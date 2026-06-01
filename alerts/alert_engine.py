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

    def _handle_fall_result(self, result, worker_id, key_suffix, alerts):
        """Shared fall result handler for both posture and YOLO falls."""
        full_key = f"{worker_id}_{key_suffix}"

        if result == "FALL_CONFIRMED":
            if self._cooldown_passed(worker_id, f"fall_{key_suffix}"):
                msg = f"CRITICAL: Fall confirmed — {worker_id}"
                alerts.append({
                    "message":        translate(msg),
                    "severity":       "CRITICAL",
                    "worker_id":      worker_id,
                    "violation_type": "Fall-Detected",
                })
                log.critical(msg)
                from genai.posture_validator import _validation_results
                _validation_results.pop(full_key, None)

        elif result == "UNCERTAIN":
            if self._cooldown_passed(worker_id, f"fall_uncertain_{key_suffix}"):
                msg = f"UNCERTAIN: Possible fall — {worker_id}, manual check required"
                alerts.append({
                    "message":        translate(msg),
                    "severity":       "HIGH",
                    "worker_id":      worker_id,
                    "violation_type": "Fall-Uncertain",
                })
                log.warning(msg)
                from genai.posture_validator import _validation_results
                _validation_results.pop(full_key, None)

        elif result == "FALSE_ALARM":
            log.debug(f"Groq: fall for {worker_id} [{key_suffix}] is FALSE_ALARM — suppressed")
            from genai.posture_validator import _validation_results
            _validation_results.pop(full_key, None)

        # PENDING — do nothing, wait

    def process(self, worker_id, detections, risk_level,
                fall_detected, angles=None, frame=None):
        alerts = []

        # --- fall from posture analyzer (velocity + horizontal) ---
        if fall_detected:
            result = get_validation_result(f"{worker_id}_posture")

            if result is None:
                # first time — fire Groq, skip this frame
                validate_async(angles or {}, f"{worker_id}_posture", frame=frame)
            else:
                self._handle_fall_result(result, worker_id, "posture", alerts)

        # --- PPE + YOLO Fall-Detected ---
        for d in detections:
            if d.get("is_critical") and d["class"] == "Fall-Detected":
                result = get_validation_result(f"{worker_id}_yolo_fall")

                if result is None:
                    validate_async(angles or {}, f"{worker_id}_yolo_fall", frame=frame)
                else:
                    self._handle_fall_result(result, worker_id, "yolo_fall", alerts)

            elif d.get("is_critical") and self._cooldown_passed(worker_id, d["class"]):
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

        # posture risk = metric only, never alerted or logged

        return alerts