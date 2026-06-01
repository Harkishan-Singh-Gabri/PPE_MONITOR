import time
from utils.logger import log
from utils.config_loader import load_config
from alerts.translator import translate
from genai.posture_validator import validate_async, get_validation_result

config       = load_config()
COOLDOWN_SEC = config["alerts"]["cooldown_sec"]


class AlertEngine:
    def __init__(self):
        self.last_alert = {}
        log.info("Alert engine initialized")

    def _cooldown_passed(self, worker_id, violation_type):
        key    = (worker_id, violation_type)
        last   = self.last_alert.get(key, 0)
        passed = (time.time() - last) > COOLDOWN_SEC
        if passed:
            self.last_alert[key] = time.time()
        return passed

    def process(self, worker_id, detections, risk_level,
                fall_detected, angles=None, frame=None):
        alerts = []

        # --- fall ---
        if fall_detected and self._cooldown_passed(worker_id, "fall"):
            msg = f"CRITICAL: Fall detected — {worker_id}"
            alerts.append({
                "message":        translate(msg),
                "severity":       "CRITICAL",
                "worker_id":      worker_id,
                "violation_type": "fall",
            })
            log.critical(msg)

        # --- PPE violations ---
        for d in detections:
            if d.get("is_critical") and self._cooldown_passed(worker_id, d["class"]):
                msg = f"CRITICAL: {d['class']} — {worker_id}"
                alerts.append({
                    "message":        translate(msg),
                    "severity":       "CRITICAL",
                    "worker_id":      worker_id,
                    "violation_type": d["class"],
                })
                log.critical(msg)

            elif d.get("is_violation") and self._cooldown_passed(worker_id, d["class"]):
                msg = f"WARNING: {d['class']} — {worker_id}"
                alerts.append({
                    "message":        translate(msg),
                    "severity":       "HIGH",
                    "worker_id":      worker_id,
                    "violation_type": d["class"],
                })
                log.warning(msg)

        # --- posture HIGH — Groq validates async ---
        if risk_level == "HIGH" and self._cooldown_passed(worker_id, "posture_HIGH"):
            validate_async(angles or {}, worker_id, frame=frame)
            is_real_risk = get_validation_result(worker_id)

            if is_real_risk:
                msg = f"HIGH posture risk — {worker_id}"
                alerts.append({
                    "message":        translate(msg),
                    "severity":       "HIGH",
                    "worker_id":      worker_id,
                    "violation_type": "posture_HIGH",
                })
                log.warning(msg)
            else:
                log.debug(f"Groq rejected posture alert for {worker_id} — normal work position")

        return alerts