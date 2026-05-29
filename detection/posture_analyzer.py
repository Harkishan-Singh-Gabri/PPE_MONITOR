from collections import deque
from utils.config_loader import load_config
from utils.logger import log
from utils.math_utils import calculate_angle, midpoint, is_visible

config=load_config()
fall_config=config['fall_detection']
post_config=config["posture"]

RISK_COLORS={
    "LOW": (0,255,0),
    'MEDIUM': (0,165,255),
    'HIGH': (0,0,255),
    'UNKNOWN': (128,128,128)
}

class PostureAnalyzer:
    def __init__(self):
        self.hip_y_history=deque(maxlen=10)
        self.fall_cooldown=0
        log.info("Posture Analyzer initialized")

    def analyze(self, landmarks):
        """
        Analyze a single person's landmarks.
        Returns: risk_level, risk_score, angles dict, fall_detected bool
        """
        if not landmarks:
            return "UNKNOWN", 0, {}, False
        
        key_landmarks = ["nose", "left_shoulder", "right_shoulder", "left_hip", "right_hip"]
        if not is_visible(*[landmarks.get(k) for k in key_landmarks]):
           return "UNKNOWN", 0, {}, False
        
        mid_shoulder=midpoint(landmarks['left_shoulder'], landmarks['right_shoulder'])
        mid_hip=midpoint(landmarks['left_hip'], landmarks['right_hip'])

        #vertical reference point directly above hip
        vertical_ref={'x': mid_hip['x'], 'y':mid_hip['y'] - 100}

        #angles
        neck_angle=calculate_angle(landmarks['nose'], mid_shoulder, mid_hip)
        back_angle=calculate_angle(mid_shoulder, mid_hip, vertical_ref)

        #knee angle (only if visible)
        knee_angle=None
        if is_visible(
            landmarks.get('left_hip', {}),
            landmarks.get('left_knee', {}),
            landmarks.get('left_ankle', {})):
            knee_angle=calculate_angle(landmarks['left_hip'], landmarks['left_knee'], landmarks['left_shoulder'])

        angles={
            'neck': neck_angle,
            'back':back_angle,
            'knee': knee_angle
        }

        #RISK SCORING
        risk_score=0
        if neck_angle > post_config['neck_angle_threshold']: risk_score+=1
        if back_angle > post_config['back_angle_threshold']: risk_score+=1
        if knee_angle and knee_angle < post_config['knee_angle_threshold']: risk_score+=1

        risk_level = (
                    "HIGH"   if risk_score >= 3 else
                    "MEDIUM" if risk_score == 2 else
                    "LOW"
        )

        #FALL DETECTION
        fall_detected=False
        hip_y=mid_hip['y']
        self.hip_y_history.append(hip_y)

        if len(self.hip_y_history)==10 and self.fall_cooldown==0:
            drop=self.hip_y_history[-1] - self.hip_y_history[0]
            velocity=drop/10

            #condition1: fast downward motion
            is_fast_drop=velocity>fall_config['velocity_threshold'] * 100

            #condition2: body is horizontal (shoulder Y = hip Y)
            shoulder_y=mid_shoulder['y']
            is_horizontal= abs(shoulder_y - hip_y) < 60

            if is_fast_drop and is_horizontal:
                fall_detected=True
                self.fall_cooldown=30
                log.critical("FALL DETECTED via posture analyzer")

        if self.fall_cooldown>0:
            self.fall_cooldown-=1

        return risk_level, risk_score, angles, fall_detected
    
if __name__=='__main__':
    import cv2
    import time
    from utils.video_stream import VideoStream
    from detection.pose_estimator import PoseEstimator

    stream=VideoStream()
    estimator=PoseEstimator()
    analyzer=PostureAnalyzer()

    frame_count=0
    start_time=time.time()

    log.info("Posture Analysis running — press Q to quit")

    while True:
        frame = stream.read_frame()
        if frame is None:
            break

        frame, all_persons=estimator.estimate(frame)
        frame_count+=1
        fps = frame_count / (time.time() - start_time)
        cv2.putText(frame, f"FPS: {fps:.1f}", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        #analyze each detected person
        for i, landmarks in enumerate(all_persons):
            risk_level, risk_score, angles, fall_detected= analyzer.analyze(landmarks)
            color=RISK_COLORS[risk_level]

            y_offset=70+(i*120)
            cv2.putText(frame, f"P{i+1} Risk: {risk_level} ({risk_score})",
                        (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
            cv2.putText(frame, f"Neck:{angles.get('neck','?')}° Back:{angles.get('back','?')}°",
                        (20, y_offset + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

            if fall_detected:
                cv2.putText(frame, f"P{i+1} FALL DETECTED",
                            (20, y_offset + 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 3)
                
        cv2.imshow("Posture Analysis", frame)
        if cv2.waitKey(1) & 0xFF==ord('q'):
            break
    stream.release()