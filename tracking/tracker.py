import numpy as np
import supervision as sv
from utils.logger import log
from utils.config_loader import load_config

config       = load_config()
track_config = config["tracker"]

WORKER_PROXY_CLASSES = ["Person", "Hardhat", "NO-Hardhat"]


class WorkerTracker:
    def __init__(self):
        self.tracker = sv.ByteTrack(
            lost_track_buffer          = track_config["max_age"],
            minimum_matching_threshold = track_config["minimum_matching_threshold"],
            minimum_consecutive_frames = track_config["min_hits"],
        )
        log.info("ByteTrack worker tracker initialized")

    def update(self, detections):
        """
        Takes detections list.
        Returns tracked workers with persistent IDs.
        Always call every frame — even on skipped YOLO frames.
        """
        if not detections:
            # still update tracker with empty detections
            # keeps existing tracks alive during occlusion
            empty = sv.Detections.empty()
            tracked = self.tracker.update_with_detections(empty)
            results = []
            for i, tracker_id in enumerate(tracked.tracker_id):
                results.append({
                    "worker_id":  f"W-{int(tracker_id):02d}",
                    "bbox":       tuple(map(int, tracked.xyxy[i])),
                    "confidence": float(tracked.confidence[i]),
                })
            return results

        xyxy       = np.array([d["bbox"] for d in detections], dtype=float)
        confidence = np.array([d["confidence"] for d in detections], dtype=float)
        class_ids  = np.zeros(len(detections), dtype=int)

        sv_detections = sv.Detections(
            xyxy       = xyxy,
            confidence = confidence,
            class_id   = class_ids,
        )

        tracked = self.tracker.update_with_detections(sv_detections)

        results = []
        for i, tracker_id in enumerate(tracked.tracker_id):
            results.append({
                "worker_id":  f"W-{int(tracker_id):02d}",
                "bbox":       tuple(map(int, tracked.xyxy[i])),
                "confidence": float(tracked.confidence[i]),
            })

        return results


if __name__ == "__main__":
    import cv2
    import time
    from utils.video_stream import VideoStream
    from detection.ppe_detector import PPEDetector

    stream   = VideoStream()
    detector = PPEDetector()
    tracker  = WorkerTracker()

    frame_count = 0
    start_time  = time.time()

    while True:
        frame = stream.read_frame()
        if frame is None:
            break

        frame, detections, _ = detector.detect(frame)

        proxy_detections = [d for d in detections
                            if d["class"] in WORKER_PROXY_CLASSES]
        tracked_workers  = tracker.update(proxy_detections)

        for d in detections:
            if d["class"] not in WORKER_PROXY_CLASSES:
                x1,y1,x2,y2 = d["bbox"]
                color = (0,255,0) if not d["is_violation"] else (0,0,255)
                cv2.rectangle(frame, (x1,y1), (x2,y2), color, 1)
                cv2.putText(frame, d["class"], (x1, y1-5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        for w in tracked_workers:
            x1,y1,x2,y2 = w["bbox"]
            cv2.rectangle(frame, (x1,y1), (x2,y2), (255,165,0), 2)
            cv2.putText(frame, w["worker_id"], (x1, y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,165,0), 2)

        frame_count += 1
        fps = frame_count / (time.time() - start_time)
        cv2.putText(frame, f"FPS: {fps:.1f}",                   (20,40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
        cv2.putText(frame, f"Workers: {len(tracked_workers)}", (20,70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,165,0), 2)

        cv2.imshow("Worker Tracking", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    stream.release()