import cv2
import time
from ultralytics import YOLO
from utils.logger import log
from utils.config_loader import load_config

config = load_config()

VIOLATION_CLASSES = config["detection"]["classes"]["ppe_violations"]
CRITICAL_CLASSES = config["detection"]["classes"]["critical"]
PPE_CLASSES = config["detection"]["classes"]["ppe_present"]

COLORS = {
    "violation": (0, 0, 255),
    "critical": (0, 0, 139),
    "ppe": (0, 255, 0),
    "other": (255, 255, 0),
}

# Determines the box color based on detection type
def get_color(class_name):
    if class_name in CRITICAL_CLASSES: return COLORS["critical"]
    if class_name in VIOLATION_CLASSES: return COLORS["violation"]
    if class_name in PPE_CLASSES: return COLORS["ppe"]
    return COLORS["other"]


class PPEDetector:
    def __init__(self):
        model_path = config["detection"]["model_path"]
        self.confidence = config["detection"]["confidence_threshold"]
        self.iou = config["detection"]["iou_threshold"]
        self.device = config["detection"]["device"]
        self.violation_conf = config["detection"]["violation_confidence_threshold"]

        self.model = YOLO(model_path)
        self.class_names = self.model.names
        log.info(f"PPE model loaded: {model_path} on {self.device}")

    def detect(self, frame):
        start = time.time()
        results = self.model(
            frame,
            conf = self.confidence,
            iou = self.iou,
            device = self.device,
            verbose = False,
            max_det = 100,
            agnostic_nms = True
        )[0]
        latency_ms = (time.time() - start) * 1000

        detections = []
        for box in results.boxes:
            class_id = int(box.cls[0])
            class_name = self.class_names[class_id]
            confidence = float(box.conf[0])
            x1,y1,x2,y2 = map(int, box.xyxy[0])
            color = get_color(class_name)

            is_violation = (
                class_name in VIOLATION_CLASSES and
                confidence >= self.violation_conf
            )
            is_critical = (
                class_name in CRITICAL_CLASSES and
                confidence >= self.violation_conf
            )

            detections.append({
                "class": class_name,
                "confidence": confidence,
                "bbox": (x1, y1, x2, y2),
                "is_violation": is_violation,
                "is_critical": is_critical,
            })

            cv2.rectangle(frame, (x1,y1), (x2,y2), color, 2)
            label = f"{class_name} {confidence:.2f}"
            cv2.putText(frame, label, (x1, y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

        return frame, detections, latency_ms


if __name__ == "__main__":
    from utils.video_stream import VideoStream

    stream = VideoStream()
    detector = PPEDetector()

    frame_count = 0
    start_time = time.time()

    while True:
        frame = stream.read_frame()
        if frame is None:
            break

        frame, detections, latency_ms = detector.detect(frame)
        frame_count += 1
        fps = frame_count / (time.time() - start_time)

        cv2.putText(frame, f"FPS: {fps:.1f}", (20,40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
        cv2.putText(frame, f"Latency: {latency_ms:.1f}ms", (20,70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)

        for d in detections:
            if d["is_critical"]:
                log.critical(f"{d['class']} — {d['confidence']:.2f}")
            elif d["is_violation"]:
                log.warning(f"{d['class']} — {d['confidence']:.2f}")

        cv2.imshow("PPE Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    stream.release()