from utils.video_stream import VideoStream

if __name__=="__main__":
    import time
    import cv2

    stream=VideoStream()
    frame_count=0
    start_time=time.time()

    while True:
        frame=stream.read_frame()
        if frame is None:
            break

        frame_count+=1
        fps=frame_count/(time.time()-start_time)
        cv2.putText(frame, f"FPS: {fps:.1f}", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow("PPE Monitor", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    stream.release()