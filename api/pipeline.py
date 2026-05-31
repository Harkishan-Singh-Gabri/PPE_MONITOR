import cv2
import time
import threading
import numpy as np
from datetime import datetime
from utils.logger import log
from utils.config_loader import load_config
from utils.video_stream import VideoStream
from detection.ppe_detector import PPEDetector
from detection.pose_estimator import PoseEstimator
from detection.posture_analyzer import PostureAnalyzer
from detection.violation_tracker import ViolationTracker
from tracking.tracker import WorkerTracker
from alerts.alert_engine import AlertEngine
from db.crud import log_violation, log_alert, update_worker

config         = load_config()
pipeline_cfg   = config["pipeline"]
YOLO_SKIP      = pipeline_cfg["yolo_frame_skip"]
POSE_SKIP      = pipeline_cfg["pose_frame_skip"]

WORKER_PROXY_CLASSES = ["Person", "Hardhat", "NO-Hardhat"]

RISK_COLORS = {
    "LOW":     (0, 255, 0),
    "MEDIUM":  (0, 165, 255),
    "HIGH":    (0, 0, 255),
    "UNKNOWN": (128, 128, 128),
}


class PPEPipeline:
    def __init__(self):
        log.info("Initializing PPE Pipeline...")
        self.stream    = VideoStream()
        self.detector  = PPEDetector()
        self.pose      = PoseEstimator()
        self.tracker   = WorkerTracker()
        self.alert     = AlertEngine()
        self.vtracker  = ViolationTracker()

        self.frame_count      = 0
        self.start_time       = time.time()
        self.violation_count  = 0
        self.fall_count       = 0
        self.worker_analyzers = {}

        # cache last results for skipped frames
        self.last_detections     = []
        self.last_tracked        = []
        self.last_persons        = []
        self.last_worker_posture = {}

        log.info("Pipeline ready")

    def _get_worker_analyzer(self, worker_id):
        if worker_id not in self.worker_analyzers:
            self.worker_analyzers[worker_id] = PostureAnalyzer()
        return self.worker_analyzers[worker_id]

    def _nearest_worker(self, bbox, tracked_workers):
        x1, y1, x2, y2 = bbox
        det_cx = (x1 + x2) / 2
        det_cy = (y1 + y2) / 2

        nearest_id   = "UNKNOWN"
        nearest_dist = float("inf")

        for w in tracked_workers:
            wx1, wy1, wx2, wy2 = w["bbox"]
            wcx  = (wx1 + wx2) / 2
            wcy  = (wy1 + wy2) / 2
            dist = np.sqrt((det_cx - wcx)**2 + (det_cy - wcy)**2)
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_id   = w["worker_id"]

        return nearest_id

    def _save_snapshot(self, frame, worker_id, violation_type):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path      = f"reports/{worker_id}_{violation_type}_{timestamp}.jpg"
        cv2.imwrite(path, frame)
        return path

    def _async_db_write(self, fn, *args, **kwargs):
        """Fire DB write in background thread — never blocks main loop."""
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
        thread.start()

    def process_frame(self, frame):
        run_yolo = (self.frame_count % YOLO_SKIP == 0)
        run_pose = (self.frame_count % POSE_SKIP == 0)

        # --- YOLO PPE Detection (every N frames) ---
        if run_yolo:
            frame, detections, latency_ms = self.detector.detect(frame)
            proxy                = [d for d in detections if d["class"] in WORKER_PROXY_CLASSES]
            self.last_detections = detections
            self.last_tracked    = self.tracker.update(proxy)

            for w in self.last_tracked:
                self._async_db_write(update_worker, w["worker_id"])
        else:
            # reuse last frame detections
            detections     = self.last_detections
            latency_ms     = 0

        tracked_workers = self.last_tracked

        # --- Pose Estimation (every M frames) ---
        if run_pose:
            frame, all_persons    = self.pose.estimate(frame)
            self.last_persons     = all_persons

            worker_posture = {}
            for i, landmarks in enumerate(all_persons):
                if i < len(tracked_workers):
                    wid      = tracked_workers[i]["worker_id"]
                    analyzer = self._get_worker_analyzer(wid)
                    risk_level, risk_score, angles, fall_detected = analyzer.analyze(landmarks)
                    worker_posture[wid] = {
                        "risk_level":    risk_level,
                        "risk_score":    risk_score,
                        "angles":        angles,
                        "fall_detected": fall_detected,
                    }
            self.last_worker_posture = worker_posture
        else:
            worker_posture = self.last_worker_posture

        # --- Alert Engine with Violation Persistence ---
        all_alerts = []
        for w in tracked_workers:
            wid = w["worker_id"]

            raw_detections = [
                d for d in detections
                if self._nearest_worker(d["bbox"], [w]) == wid
                and d["class"] not in WORKER_PROXY_CLASSES
            ]

            # only confirmed violations (seen N consecutive frames)
            confirmed_detections = self.vtracker.update(wid, raw_detections)

            posture_data  = worker_posture.get(wid, {})
            risk_level    = posture_data.get("risk_level", "UNKNOWN")
            fall_detected = posture_data.get("fall_detected", False)

            alerts = self.alert.process(
                worker_id = wid,
                detections = confirmed_detections,
                risk_level = risk_level,
                fall_detected = fall_detected,
                angles = posture_data.get("angles", {}),
                frame = frame,   
            )

            for a in alerts:
                if a["severity"] in ("CRITICAL", "HIGH"):
                    snapshot = self._save_snapshot(frame, wid, a["violation_type"])
                    self._async_db_write(
                        log_alert, wid, a["message"], a["severity"], a["violation_type"]
                    )
                    self._async_db_write(
                        log_violation,
                        worker_id      = wid,
                        violation_type = a["violation_type"],
                        severity       = a["severity"],
                        zone           = "general",
                        snapshot_path  = snapshot,
                    )
                    if a["violation_type"] == "fall":
                        self.fall_count += 1
                    self.violation_count += 1

            all_alerts.extend(alerts)

        # --- Draw Worker IDs + Risk ---
        for w in tracked_workers:
            wid          = w["worker_id"]
            x1,y1,x2,y2 = w["bbox"]
            posture      = worker_posture.get(wid, {})
            risk         = posture.get("risk_level", "UNKNOWN")
            color        = RISK_COLORS[risk]

            cv2.rectangle(frame, (x1,y1), (x2,y2), (255,165,0), 2)
            cv2.putText(frame, wid, (x1, y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,165,0), 2)
            cv2.putText(frame, f"Risk:{risk}", (x1, y2+20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # --- Metrics Overlay ---
        self.frame_count += 1
        fps = self.frame_count / (time.time() - self.start_time)

        metrics = {
            "fps":              round(fps, 1),
            "latency_ms":       round(latency_ms, 1),
            "active_workers":   len(tracked_workers),
            "violations_today": self.violation_count,
            "falls_detected":   self.fall_count,
        }

        cv2.putText(frame, f"FPS: {fps:.1f}",                          (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
        cv2.putText(frame, f"Workers: {len(tracked_workers)}",          (20, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
        cv2.putText(frame, f"Critical Violations: {self.violation_count}", (20, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)

        return frame, all_alerts, metrics

    def run(self):
        log.info("Pipeline running — press Q to quit")

        while True:
            frame = self.stream.read_frame()
            if frame is None:
                break

            frame, alerts, metrics = self.process_frame(frame)

            for a in alerts:
                log.warning(f"[{a['severity']}] {a['message']}")

            cv2.imshow("PPE Monitor", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        self.stream.release()


if __name__ == "__main__":
    pipeline = PPEPipeline()
    pipeline.run()