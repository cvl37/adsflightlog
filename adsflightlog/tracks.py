"""Flight-path logging for sightings.

The collector already reads every aircraft's position each poll. We keep a
small, thinned-out trail per aircraft in memory. When an aircraft is caught in
a zone, the trail is attached to that sighting. The trail is saved with the
time before entering (``before``), every in-zone point, and the time after
leaving (``after``). A value of None means "everything the receiver saw".

Storage per sighting is one zlib-compressed JSON blob:
    {"v": 1, "t0": <epoch s>, "p": [[dt_s, lat, lon, alt_ft|null, in_zone], ...]}
Positions are rounded to 5 decimals (~1 m). A typical track is a few KB.
"""

from __future__ import annotations

import json
import sqlite3
import zlib
from dataclasses import dataclass, field

LOST_AFTER_S = 300          # aircraft not seen this long: close its track
MAX_BUFFER_S = 3 * 3600     # hard cap on pre-catch history kept in memory
MAX_TRACK_S = 6 * 3600      # hard cap on one sighting's track
PERSIST_EVERY_S = 60

# Downsampling outside the zone: keep a point if any of these thresholds is hit.
MIN_INTERVAL_S = 30
MIN_ALT_CHANGE_FT = 500
MIN_TURN_DEG = 10

SCHEMA = """
CREATE TABLE IF NOT EXISTS sighting_tracks (
    sighting_id INTEGER PRIMARY KEY REFERENCES sightings(id),
    n           INTEGER NOT NULL,
    first_t     REAL,
    last_t      REAL,
    data        BLOB NOT NULL
);
"""


def encode(points: list[tuple]) -> bytes:
    t0 = int(points[0][0]) if points else 0
    p = [[round(t - t0, 1), round(lat, 5), round(lon, 5), alt, int(z)]
         for t, lat, lon, alt, z in points]
    return zlib.compress(json.dumps({"v": 1, "t0": t0, "p": p}, separators=(",", ":")).encode(), 9)


def decode(blob: bytes) -> list[tuple]:
    d = json.loads(zlib.decompress(blob))
    t0 = d["t0"]
    return [(t0 + dt, lat, lon, alt, bool(z)) for dt, lat, lon, alt, z in d["p"]]


def load(conn: sqlite3.Connection, sighting_id: int) -> list[tuple] | None:
    row = conn.execute("SELECT data FROM sighting_tracks WHERE sighting_id=?", (sighting_id,)).fetchone()
    return decode(row[0]) if row else None


def _turn(a: float | None, b: float | None) -> float:
    if a is None or b is None:
        return 0.0
    return abs((a - b + 180) % 360 - 180)


@dataclass
class Trail:
    points: list = field(default_factory=list)   # (t, lat, lon, alt, in_zone)
    last_track: float | None = None
    last_seen: float = 0.0
    sighting_id: int | None = None
    sight_start: float = 0.0
    last_in_zone: float = 0.0
    last_persist: float = 0.0


class Tracker:
    def __init__(self, conn: sqlite3.Connection, before_s: float | None, after_s: float | None, log=print):
        self.conn = conn
        self.before_s = before_s
        self.after_s = after_s
        self.log = log
        self.trails: dict[str, Trail] = {}
        conn.executescript(SCHEMA)

    # ---------- per poll ----------
    def observe(self, hx: str, t: float, lat: float, lon: float, alt: int | None,
                track: float | None, in_zone: bool) -> None:
        tr = self.trails.setdefault(hx, Trail())
        tr.last_seen = t
        last = tr.points[-1] if tr.points else None
        keep = (
            last is None
            or in_zone or last[4]                      # full resolution in and at the zone edge
            or t - last[0] >= MIN_INTERVAL_S
            or (alt is not None and last[3] is not None and abs(alt - last[3]) >= MIN_ALT_CHANGE_FT)
            or _turn(track, tr.last_track) >= MIN_TURN_DEG
        )
        if keep and (last is None or (lat, lon) != (last[1], last[2]) or in_zone != last[4]):
            tr.points.append((t, lat, lon, alt, in_zone))
            tr.last_track = track

    def attach(self, hx: str, sighting_id: int, t: float) -> None:
        """Called on every in-zone hit with the sighting it belongs to."""
        tr = self.trails.setdefault(hx, Trail())
        if tr.sighting_id != sighting_id:
            if tr.sighting_id is not None:
                self._persist(tr)
            tr.sighting_id = sighting_id
            tr.sight_start = t
            tr.last_persist = 0.0
        tr.last_in_zone = t

    def tick(self, now: float) -> None:
        for hx, tr in list(self.trails.items()):
            if tr.sighting_id is not None:
                lost = now - tr.last_seen > LOST_AFTER_S
                done = self.after_s is not None and now - tr.last_in_zone > self.after_s
                too_long = now - tr.sight_start > MAX_TRACK_S
                if lost or done or too_long:
                    self._persist(tr)
                    tr.sighting_id = None
                elif now - tr.last_persist >= PERSIST_EVERY_S:
                    self._persist(tr)
                    tr.last_persist = now
            if tr.sighting_id is None:
                if now - tr.last_seen > LOST_AFTER_S:
                    del self.trails[hx]
                    continue
                keep_s = min(self.before_s if self.before_s is not None else MAX_BUFFER_S, MAX_BUFFER_S)
                cutoff = now - keep_s
                if tr.points and tr.points[0][0] < cutoff:
                    tr.points = [p for p in tr.points if p[0] >= cutoff]

    def flush(self) -> None:
        for tr in self.trails.values():
            if tr.sighting_id is not None:
                self._persist(tr)

    # ---------- storage ----------
    def _persist(self, tr: Trail) -> None:
        lo = tr.sight_start - self.before_s if self.before_s is not None else float("-inf")
        hi = tr.last_in_zone + self.after_s if self.after_s is not None else float("inf")
        pts = [p for p in tr.points if lo <= p[0] <= hi]
        # Merge with what is already stored (e.g. from before a collector restart).
        existing = load(self.conn, tr.sighting_id) or []
        merged = {round(p[0], 1): p for p in existing}
        for p in pts:
            merged[round(p[0], 1)] = p
        pts = [merged[k] for k in sorted(merged)]
        if not pts:
            return
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO sighting_tracks VALUES (?,?,?,?,?)",
                (tr.sighting_id, len(pts), pts[0][0], pts[-1][0], encode(pts)),
            )
