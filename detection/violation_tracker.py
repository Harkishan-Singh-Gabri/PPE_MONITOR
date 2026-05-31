from collections import defaultdict
from utils.config_loader import load_config
from utils.logger import log

config      = load_config()
PERSIST_N   = config["detection"]["violation_persistence_frames"]


class ViolationTracker:
    """
    Only confirms a violation after it appears in N consecutive frames.
    Eliminates single-frame false positives.
    """
    def __init__(self):
        # {(worker_id, violation_type): consecutive_count}
        self.counters = defaultdict(int)
        log.info(f"Violation tracker initialized — persistence: {PERSIST_N} frames")

    def update(self, worker_id, detections):
        """
        Takes raw detections for a worker.
        Returns only confirmed violations (seen N consecutive frames).
        """
        # track which violations are active this frame
        active_keys = set()

        confirmed = []
        for d in detections:
            if not d.get("is_violation") and not d.get("is_critical"):
                continue

            key = (worker_id, d["class"])
            active_keys.add(key)
            self.counters[key] += 1

            if self.counters[key] >= PERSIST_N:
                confirmed.append(d)       # confirmed — seen N frames in a row

        # reset counters for violations not seen this frame
        for key in list(self.counters):
            if key not in active_keys:
                self.counters[key] = 0

        return confirmed