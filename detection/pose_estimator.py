import cv2
import time
from ultralytics import YOLO
from utils.logger import log
from utils.config_loader import load_config

config = load_config()

# YOLOv8-Pose detects 17 keypoints 
KEYPOINTS = {
    "nose":           0,
    "left_shoulder":  5,
    "right_shoulder": 6,
    "left_elbow":     7,
    "right_elbow":    8,
    "left_wrist":     9,
    "right_wrist":    10,
    "left_hip":       11,
    "right_hip":      12,
    "left_knee":      13,
    "right_knee":     14,
    "left_ankle":     15,
    "right_ankle":    16,
}

class PoseEstimator:
    def __init__(self):
        self.model  = YOLO("yolov8n-pose.pt")
        self.device = config["detection"]["device"]
        log.info(f"YOLOv8-Pose loaded on {self.device}")

    def estimate(self, frame):
        """
        Run pose estimation on frame.
        Returns: annotated frame, list of landmarks per person
        each person = dict of keypoint_name → {x, y, confidence}
        """
        results = self.model(
            frame,
            device=self.device,
            verbose=False
        )[0]

        all_persons = []

        if results.keypoints is None:
            return frame, all_persons

        h, w, _ = frame.shape

        for person_kps in results.keypoints:
            landmarks = {}
            kp_data   = person_kps.data[0]   # shape: (17, 3) → x, y, conf

            for name, idx in KEYPOINTS.items():
                x, y, conf = kp_data[idx]
                landmarks[name] = {
                    "x":          float(x),
                    "y":          float(y),
                    "visibility": float(conf)
                }

            all_persons.append(landmarks)

            # draw keypoints manually
            for name, lm in landmarks.items():
                if lm["visibility"] > 0.5:
                    cv2.circle(frame,
                        (int(lm["x"]), int(lm["y"])),
                        4, (0, 255, 255), -1)

        return frame, all_persons


if __name__ == "__main__":
    from utils.video_stream import VideoStream

    stream    = VideoStream()
    estimator = PoseEstimator()

    frame_count = 0
    start_time  = time.time()

    log.info("YOLOv8-Pose running — press Q to quit")

    while True:
        frame = stream.read_frame()
        if frame is None:
            break

        frame, all_persons = estimator.estimate(frame)

        frame_count += 1
        fps = frame_count / (time.time() - start_time)

        cv2.putText(frame, f"FPS: {fps:.1f}", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(frame, f"Persons: {len(all_persons)}", (20, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        cv2.imshow("Pose Estimation", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    stream.release()