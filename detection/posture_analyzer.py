from collections import deque
from utils.config_loader import load_config
from utils.logger import log
from utils.math_utils import calculate_angle, midpoint, is_visible

config = load_config()
fall_config = config["fall_detection"]
post_config = config["posture"]

RISK_COLORS = {
    "LOW": (0, 255, 0),
    "MEDIUM": (0, 165, 255),
    "HIGH": (0, 0, 255),
    "UNKNOWN": (128, 128, 128),
}

_logged = False 


class PostureAnalyzer:
    def __init__(self):
        global _logged
        if not _logged:
            log.info("Posture analyzer initialized")
            _logged = True

        self.hip_y_history = deque(maxlen=10)
        self.fall_cooldown = 0

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

        mid_shoulder = midpoint(landmarks["left_shoulder"], landmarks["right_shoulder"])
        mid_hip      = midpoint(landmarks["left_hip"],      landmarks["right_hip"])
        vertical_ref = {"x": mid_hip["x"], "y": mid_hip["y"] - 100}

        neck_angle = calculate_angle(landmarks["nose"], mid_shoulder, mid_hip)
        back_angle = calculate_angle(mid_shoulder, mid_hip, vertical_ref)

        knee_angle = None
        if is_visible(
            landmarks.get("left_hip", {}),
            landmarks.get("left_knee", {}),
            landmarks.get("left_ankle", {})
        ):
            knee_angle = calculate_angle(
                landmarks["left_hip"],
                landmarks["left_knee"],
                landmarks["left_ankle"]
            )

        angles = {
            "neck": neck_angle,
            "back": back_angle,
            "knee": knee_angle,
        }

        risk_score = 0
        if neck_angle > post_config["neck_angle_threshold"]: risk_score += 1
        if back_angle > post_config["back_angle_threshold"]: risk_score += 1
        if knee_angle and knee_angle < post_config["knee_angle_threshold"]: risk_score += 1

        risk_level = (
            "HIGH" if risk_score >= 3 else
            "MEDIUM" if risk_score == 2 else
            "LOW"
        )

        # fall detection
        fall_detected = False
        hip_y = mid_hip["y"]
        self.hip_y_history.append(hip_y)

        if len(self.hip_y_history) == 10 and self.fall_cooldown == 0:
            drop = self.hip_y_history[-1] - self.hip_y_history[0]
            velocity = drop / 10
            is_fast_drop = velocity > fall_config["velocity_threshold"] * 100
            shoulder_y = mid_shoulder["y"]
            is_horizontal = abs(shoulder_y - hip_y) < fall_config["horizontal_threshold"]

            if is_fast_drop and is_horizontal:
                fall_detected = True
                self.fall_cooldown = 30
                log.critical("FALL DETECTED via posture analyzer")

        if self.fall_cooldown > 0:
            self.fall_cooldown -= 1

        return risk_level, risk_score, angles, fall_detected