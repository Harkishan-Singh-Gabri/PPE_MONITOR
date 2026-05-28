import cv2
import time
from utils.logger import log
from utils.config_loader import load_config

config=load_config()

class VideoStream:
    def __init__(self):
        source=config["camera"]["source"]
        self.fps_limit=config["camera"]["fps_limit"]
        self.resolution=config["camera"]["resolution"]

        self.cap= cv2.VideoCapture(source)

        if not self.cap.isOpened():
            log.error(f"Cannot open camera source: {source}")
            raise RuntimeError("Video source failed to open")
        
        log.info(f"Video source opened: {source}")

    def read_frame(self):
        ret, frame= self.cap.read()

        if not ret:
            log.warning("Failed to read frame")
            return None
        
        frame= cv2.resize(frame, self.resolution)
        return frame
    
    def release(self):
        self.cap.release()
        cv2.destroyAllWindows()
        log.info("Video stream released")

if __name__=="__main__":

    stream=VideoStream()
    
    fps=0
    frame_count=0
    start_time=time.time()

    log.info("Starting Video Stream - Press Q to exit")

    while True:
        frame=stream.read_frame()
        if frame is None:
            break

        #FPS Calculation
        frame_count+=1
        elapsed=time.time()- start_time
        if elapsed>0:
            fps=frame_count/elapsed

        #overlay fps
        cv2.putText(
            frame,
            f"FPS: {fps:.1f}",
            (20,40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0,255,0),
            2
        )

        cv2.imshow("PPE Monitor", frame)

        #if want to quit
        if cv2.waitKey(1) & 0xFF == ord('Q'):
            log.info("Stream stopped by user")
            break

    stream.release()
