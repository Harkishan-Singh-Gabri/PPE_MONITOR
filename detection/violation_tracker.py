from collections import defaultdict
import time
from utils.config_loader import load_config
from utils.logger import log

config    = load_config()
PERSIST_N = config["detection"]["violation_persistence_frames"]


class ViolationTracker:
    def __init__(self):
        self.counters       = defaultdict(int)
        self.first_seen     = {}    # {(worker_id, class): first_detection_timestamp}
        self.response_times = []    # measured response times in ms
        log.info(f"Violation tracker — persistence: {PERSIST_N} frames")

    def update(self, worker_id, detections):
        active_keys = set()
        confirmed   = []

        for d in detections:
            if not d.get("is_violation") and not d.get("is_critical"):
                continue

            key = (worker_id, d["class"])
            active_keys.add(key)

            if self.counters[key] == 0:
                # first detection — record timestamp
                self.first_seen[key] = time.time()
                log.debug(f"Violation first seen: {worker_id} — {d['class']}")

            self.counters[key] += 1

            if self.counters[key] >= PERSIST_N:
                # record response time exactly once — when counter hits PERSIST_N
                if self.counters[key] == PERSIST_N and key in self.first_seen:
                    response_ms = (time.time() - self.first_seen[key]) * 1000
                    self.response_times.append(response_ms)
                    log.info(
                        f"Alert response: {response_ms:.0f}ms | "
                        f"{worker_id} — {d['class']}"
                    )
                    del self.first_seen[key]
                confirmed.append(d)

        # reset counters for violations not seen this frame
        for key in list(self.counters):
            if key not in active_keys:
                self.counters[key] = 0
                self.first_seen.pop(key, None)

        return confirmed

    def avg_response_ms(self):
        log.debug(f"response_times list: {self.response_times}")
        if not self.response_times:
            return 0
        return round(sum(self.response_times) / len(self.response_times))

    def min_response_ms(self):
        return round(min(self.response_times)) if self.response_times else 0

    def total_confirmed(self):
        return len(self.response_times)