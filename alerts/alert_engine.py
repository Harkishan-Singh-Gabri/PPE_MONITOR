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

        # --- posture HIGH — two-pass Groq validation ---
        if risk_level == "HIGH":
            result = get_validation_result(worker_id)

            if result is None:
                # first time seeing this worker — fire Groq, skip alert this frame
                validate_async(angles or {}, worker_id, frame=frame)

            elif result == "PENDING":
                # Groq still thinking — skip alert this frame
                pass

            elif result == "NORMAL":
                # Groq confirmed false positive — suppress silently
                log.debug(f"Groq: {worker_id} posture is NORMAL — suppressed")

            elif result == "DANGEROUS":
                # Groq confirmed real risk — alert
                if self._cooldown_passed(worker_id, "posture_HIGH"):
                    msg = f"HIGH posture risk — {worker_id}"
                    alerts.append({
                        "message":        translate(msg),
                        "severity":       "HIGH",
                        "worker_id":      worker_id,
                        "violation_type": "posture_HIGH",
                    })
                    log.warning(msg)
                    # reset result so Groq re-evaluates next trigger
                    from genai.posture_validator import _validation_results
                    _validation_results.pop(worker_id, None)

        return alerts