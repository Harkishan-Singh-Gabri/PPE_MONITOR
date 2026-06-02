import numpy as np
from scipy.optimize import linear_sum_assignment
from utils.logger import log
from utils.config_loader import load_config

config = load_config()
track_config = config["tracker"]


class Track:
    def __init__(self, track_id, bbox):
        self.track_id = track_id
        self.bbox = bbox
        self.centroid = self._centroid(bbox)
        self.lost = 0   

    def update(self, bbox):
        self.bbox = bbox
        self.centroid = self._centroid(bbox)
        self.lost = 0

    def mark_lost(self):
        self.lost += 1

    @staticmethod
    def _centroid(bbox):
        x1, y1, x2, y2 = bbox
        return np.array([(x1+x2)/2, (y1+y2)/2])


class WorkerTracker:
    """
    Centroid-based tracker — much more stable than IoU for small helmet boxes.
    Matches detections to existing tracks using Euclidean distance between centers.
    """
    def __init__(self):
        self.tracks     = {}    
        self.next_id    = 1
        self.max_lost   = track_config["max_age"]
        self.max_dist   = 120    # max pixel distance to match same person
        log.info("Centroid tracker initialized")

    def update(self, detections):
        if not detections:
            # mark all existing tracks as lost
            for t in self.tracks.values():
                t.mark_lost()
            self._remove_stale()
            return self._get_results()

        det_centroids = np.array([
            [(d["bbox"][0]+d["bbox"][2])/2,
             (d["bbox"][1]+d["bbox"][3])/2]
            for d in detections
        ])

        if not self.tracks:
            # no existing tracks — create new for all detections
            for i, d in enumerate(detections):
                self.tracks[self.next_id] = Track(self.next_id, d["bbox"])
                self.next_id += 1
            return self._get_results()

        # build cost matrix — Euclidean distance between each track and detection
        track_ids = list(self.tracks.keys())
        track_cents = np.array([self.tracks[t].centroid for t in track_ids])

        cost_matrix = np.linalg.norm(
            track_cents[:, np.newaxis] - det_centroids[np.newaxis, :],
            axis=2
        )  # shape: (num_tracks, num_detections)

        # Hungarian algorithm — optimal assignment
        row_ind, col_ind = linear_sum_assignment(cost_matrix)

        matched_tracks = set()
        matched_dets = set()

        for r, c in zip(row_ind, col_ind):
            if cost_matrix[r, c] < self.max_dist:
                # distance within threshold — same person
                self.tracks[track_ids[r]].update(detections[c]["bbox"])
                matched_tracks.add(track_ids[r])
                matched_dets.add(c)

        # unmatched tracks — mark lost
        for tid in track_ids:
            if tid not in matched_tracks:
                self.tracks[tid].mark_lost()

        # unmatched detections — new person, create new track
        for i, d in enumerate(detections):
            if i not in matched_dets:
                self.tracks[self.next_id] = Track(self.next_id, d["bbox"])
                self.next_id += 1

        self._remove_stale()
        return self._get_results()

    def _remove_stale(self):
        """Remove tracks that have been lost too long."""
        stale = [tid for tid, t in self.tracks.items() if t.lost > self.max_lost]
        for tid in stale:
            del self.tracks[tid]

    def _get_results(self):
        return [
            {
                "worker_id": f"W-{t.track_id:02d}",
                "bbox": t.bbox,
                "confidence": 1.0,
            }
            for t in self.tracks.values()
            if t.lost == 0   # only return currently visible tracks
        ]