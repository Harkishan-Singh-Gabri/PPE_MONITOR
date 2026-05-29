import time
from utils.logger import log
from utils.config_loader import load_config
from alerts.translator import translate

config       = load_config()
alert_config = config["alerts"]

# severity levels
SEVERITY = {
    "CRITICAL": 3,    # fall
    "HIGH":     2,    # missing helmet near machinery
    "MEDIUM":   1,    # posture risk
    "LOW":      0,    # minor PPE missing
}

COOLDOWN_SEC=10

class AlertEngine:
    def __init__(self):
        # track last alert time per worker per violation type
        # key: (worker_id, violation_type) → timestamp
        self.last_alert = {}
        log.info("Alert engine initialized")

    def cooldown_passed(self, worker_id, violation_type):
        key=(worker_id, violation_type)
        last=self.last_alert.get(key, 0)
        passed=(time.time() - last) > COOLDOWN_SEC
        if passed:
            self.last_alert[key]=time.time()
        return passed
    
    def process(self, worker_id, detections, risk_level, fall_detected):
        """
        Takes per-worker data, returns list of alerts to display.
        Each alert: {message, severity, worker_id, violation_type}
        """
        alerts = []

        # --- fall alert (highest priority) ---
        if fall_detected and self.cooldown_passed(worker_id, "fall"):
            msg = f"CRITICAL: Fall detected — {worker_id}"
            alerts.append({
                "message":        translate(msg),
                "severity":       "CRITICAL",
                "worker_id":      worker_id,
                "violation_type": "fall",
            })
            log.critical(msg)

        # --- PPE violation alerts ---
        for d in detections:
            if d.get("is_critical") and self.cooldown_passed(worker_id, d["class"]):
                msg = f"CRITICAL: {d['class']} — {worker_id}"
                alerts.append({
                    "message":        translate(msg),
                    "severity":       "CRITICAL",
                    "worker_id":      worker_id,
                    "violation_type": d["class"],
                })
                log.critical(msg)

            elif d.get("is_violation") and self.cooldown_passed(worker_id, d["class"]):
                msg = f"WARNING: {d['class']} — {worker_id}"
                alerts.append({
                    "message":        translate(msg),
                    "severity":       "HIGH",
                    "worker_id":      worker_id,
                    "violation_type": d["class"],
                })
                log.warning(msg)

        # --- posture risk alerts ---
        if risk_level in ("MEDIUM", "HIGH") and \
           self.cooldown_passed(worker_id, f"posture_{risk_level}"):
            msg = f"Posture {risk_level} risk — {worker_id}"
            alerts.append({
                "message":        translate(msg),
                "severity":       risk_level,
                "worker_id":      worker_id,
                "violation_type": f"posture_{risk_level}",
            })
            log.warning(msg)

        return alerts
    
if __name__ == "__main__":
    engine = AlertEngine()

    # simulate detections for testing
    test_detections = [
        {"class": "NO-Hardhat",   "is_violation": True,  "is_critical": False},
        {"class": "Fall-Detected","is_violation": False, "is_critical": True},
    ]

    # fire alerts
    alerts = engine.process(
        worker_id      = "W-01",
        detections     = test_detections,
        risk_level     = "HIGH",
        fall_detected  = True
    )

    print(f"\n{len(alerts)} alerts generated:")
    for a in alerts:
        print(f"  [{a['severity']}] {a['message']}")

    # fire again immediately — should be suppressed by cooldown
    print("\nFiring again immediately (should be suppressed):")
    alerts2 = engine.process("W-01", test_detections, "HIGH", True)
    print(f"  {len(alerts2)} alerts (expected 0)")