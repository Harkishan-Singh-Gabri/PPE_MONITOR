import cv2
import time
from ultralytics import YOLO
from utils.logger import log
from utils.config_loader import load_config

config=load_config()

VIOLATION_CLASSES=config["detection"]["classes"]["ppe_violations"]
CRITICAL_CLASSES=config["detection"]["classes"]["critical"]
PPE_CLASSES=config["detection"]["classes"]["ppe_present"]

#color per detection type
COLORS={
    "violations": (0,0,255), #red
    "critical": (0,0,139), # dark red
    "ppe": (0,255,0), #green
    "other": (255,255,0)
}

def get_color(class_name):
    if class_name in CRITICAL_CLASSES: return COLORS["critical"]
    if class_name in VIOLATION_CLASSES: return COLORS["violations"]
    if class_name in PPE_CLASSES: return COLORS["ppe"]
    return COLORS["other"]

class PPEDetector:
    def __init__(self):
        model_path=config["detection"]["model_path"]
        self.confidence=config["detection"]["confidence_threshold"]
        self.iou=config["detection"]["iou_threshold"]
        self.device=config["detection"]["device"]
        self.model=YOLO(model_path)
        self.class_names=self.model.names
        log.info(f"PPE model loaded: {model_path} on {self.device}")

    def detect(self, frame):
        """
        runs inference on single frame.
        returns annotated frame, detections list, latency_ms
        """
        start=time.time()
        results=self.model(
            frame,
            conf=self.confidence,
            iou=self.iou,
            device=self.device,
            verbose=False
        )[0]
        latency_ms=(time.time()-start)*1000

        detections=[]

        for box in results.boxes:
            class_id=int(box.cls[0])
            class_name=self.class_names[class_id]
            confidence=float(box.conf[0])
            x1,y1,x2,y2=map(int, box.xyxy[0])
            color=get_color(class_name)

            detections.append({
                "class": class_name,
                "confidence": confidence,
                "bbox": (x1,y1,x2,y2),
                "is_violation": class_name in VIOLATION_CLASSES,
                "is_critical": class_name in CRITICAL_CLASSES,
            })

            #bounding box
            cv2.rectangle(frame, (x1,y1), (x2,y2), color, 2)

            #label
            label=f"{class_name} {confidence:.2f}"
            cv2.putText(frame, label, (x1,y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
        return frame, detections, latency_ms
    
if __name__=="__main__":
    from utils.video_stream import VideoStream

    stream=VideoStream()
    detector=PPEDetector()
    frame_count=0
    start_time=time.time()

    log.info("PPE Detection running - press Q to quit")

    while True:
        frame=stream.read_frame()
        if frame is None:
            break

        frame, detections, latency_ms= detector.detect(frame)

        #metrics overlay
        frame_count+=1
        fps=frame_count/(time.time()- start_time)
        cv2.putText(frame, f"FPS: {fps:.1f}", (20,40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
        cv2.putText(frame, f"latency: {latency_ms:.1f}ms", (20,70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)

        #log violations
        for d in detections:
            if d["is_critical"]:
                log.critical(f"{d['class']} - {d['confidence']:.2f}")
            elif d["is_violation"]:
                log.warning(f"{d['class']} - {d['confidence']:.2f}")

        cv2.imshow("PPE Detection", frame)
        if cv2.waitKey(1) & 0xFF==ord('q'):
            break

    stream.release()