import cv2
import time
from utils.logger import log
from utils.config_loader import load_config

config = load_config()

class VideoStream:
    def __init__(self):
        source = config["camera"]["source"]
        self.fps_limit = config["camera"]["fps_limit"]
        self.resolution = tuple(config["camera"]["resolution"])

        # source can be 0 (webcam) or a file path like "test.mp4"
        self.cap = cv2.VideoCapture(source)

        if not self.cap.isOpened():
            log.error(f"Cannot open camera source: {source}")
            raise RuntimeError("Video source failed to open")

        log.info(f"Video source opened: {source}")

    def read_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            log.warning("Failed to read frame")
            return None
        frame = cv2.resize(frame, self.resolution)
        return frame

    def release(self):
        self.cap.release()
        cv2.destroyAllWindows()
        log.info("Video stream released")


if __name__ == "__main__":
    stream = VideoStream()

    fps = 0
    frame_count = 0
    start_time = time.time()

    log.info("Starting video stream — press Q to quit")

    while True:
        frame = stream.read_frame()
        if frame is None:
            break

        # FPS calculation
        frame_count += 1
        elapsed = time.time() - start_time
        if elapsed > 0:
            fps = frame_count / elapsed

        # overlay FPS on frame
        cv2.putText(
            frame,
            f"FPS: {fps:.1f}",
            (20, 40),                    # position
            cv2.FONT_HERSHEY_SIMPLEX,
            1,                           # font scale
            (0, 255, 0),                 # green
            2                            # thickness
        )

        cv2.imshow("PPE Monitor", frame)

        # Q to quit
        if cv2.waitKey(1) & 0xFF == ord("q"):
            log.info("Stream stopped by user")
            break

    stream.release()