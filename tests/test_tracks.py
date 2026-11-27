"""Track logging: python3 -m unittest discover -s tests -t ."""

import unittest
from pathlib import Path

from adsflightlog import tracks
from adsflightlog.db import connect


def fly(tracker, t0, minutes, zone_from, zone_to, sid=1, step=5):
    """Straight flight, one poll every `step` s; in the zone between the given minutes."""
    t = t0
    while t <= t0 + minutes * 60:
        m = (t - t0) / 60
        in_zone = zone_from <= m <= zone_to
        tracker.observe("abc123", t, 45 + m * 0.01, 10.0, 10000 + int(m * 50), 0.0, in_zone)
        if in_zone:
            tracker.attach("abc123", sid, t)
        tracker.tick(t)
        t += step
    return t


class Tracks(unittest.TestCase):
    def setUp(self):
        self.conn = connect(Path(":memory:"))
        self.conn.execute("INSERT INTO airframes (hex, card_no, first_seen, last_seen) VALUES ('abc123', 1, 0, 0)")
        self.conn.execute("INSERT INTO sightings (id, hex, start, end) VALUES (1, 'abc123', 0, 0)")

    def test_window_30_min(self):
        tr = tracks.Tracker(self.conn, before_s=1800, after_s=1800)
        end = fly(tr, 0, 120, 60, 62)          # in zone from minute 60 to 62
        tr.tick(end + 400)                      # aircraft lost -> finalised
        pts = tracks.load(self.conn, 1)
        self.assertIsNotNone(pts)
        self.assertGreaterEqual(pts[0][0], 60 * 60 - 1800)
        self.assertLessEqual(pts[0][0], 60 * 60 - 1800 + 30)
        self.assertLessEqual(pts[-1][0], 62 * 60 + 1800)
        self.assertGreaterEqual(pts[-1][0], 62 * 60 + 1800 - 30)
        zone_pts = [p for p in pts if p[4]]
        self.assertGreaterEqual(len(zone_pts), 24)          # 2 min at 5 s, full resolution
        self.assertLess(len(pts), 24 + 2 * 1800 / 30 + 10)  # thinned outside the zone

    def test_all_visible(self):
        tr = tracks.Tracker(self.conn, before_s=None, after_s=None)
        end = fly(tr, 0, 100, 50, 51)
        tr.tick(end + 400)
        pts = tracks.load(self.conn, 1)
        self.assertLess(pts[0][0], 60)
        self.assertGreater(pts[-1][0], 99 * 60)

    def test_compact(self):
        tr = tracks.Tracker(self.conn, before_s=None, after_s=None)
        end = fly(tr, 0, 60, 30, 32)
        tr.tick(end + 400)
        size = self.conn.execute("SELECT length(data) FROM sighting_tracks").fetchone()[0]
        self.assertLess(size, 4000)

    def test_restart_merges(self):
        tr = tracks.Tracker(self.conn, before_s=None, after_s=None)
        fly(tr, 0, 20, 10, 20)
        tr.flush()
        n1 = len(tracks.load(self.conn, 1))
        tr2 = tracks.Tracker(self.conn, before_s=None, after_s=None)  # collector restarted
        end = fly(tr2, 21 * 60, 10, 0, 5)
        tr2.tick(end + 400)
        self.assertGreater(len(tracks.load(self.conn, 1)), n1)


if __name__ == "__main__":
    unittest.main()
