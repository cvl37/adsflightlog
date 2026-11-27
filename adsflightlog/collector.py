"""Poll readsb's aircraft.json and log every aircraft caught inside the radius.

Run with:  python3 -m adsflightlog.collector [config.toml]
"""

from __future__ import annotations

import json
import math
import re
import signal
import sqlite3
import sys
import time

from . import config as cfgmod
from .db import connect
from . import refdb

AIRLINE_CALLSIGN = re.compile(r"^([A-Z]{3})\d")


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def altitude(ac: dict) -> int | None:
    alt = ac.get("alt_baro", ac.get("alt_geom"))
    if alt == "ground":
        return 0
    return int(alt) if isinstance(alt, (int, float)) else None


def in_range(cfg: cfgmod.Config, ac: dict) -> float | None:
    """Return distance in km if this aircraft counts as a catch, else None."""
    if "lat" not in ac or "lon" not in ac:
        return None
    if ac.get("seen_pos", 0) > cfg.max_position_age_s:
        return None
    dist = haversine_km(cfg.lat, cfg.lon, ac["lat"], ac["lon"])
    if dist > cfg.max_distance_km:
        return None
    if cfg.max_altitude_ft:
        alt = altitude(ac)
        if alt is not None and alt > cfg.max_altitude_ft:
            return None
    return dist


def _max(a, b):
    if a is None:
        return b
    if b is None:
        return a
    return max(a, b)


def _min(a, b):
    if a is None:
        return b
    if b is None:
        return a
    return min(a, b)


class Collector:
    def __init__(self, cfg: cfgmod.Config, conn: sqlite3.Connection, log=print):
        self.cfg = cfg
        self.conn = conn
        self.log = log

    def poll_once(self, now: float | None = None) -> int:
        data = json.loads(self.cfg.aircraft_json.read_text())
        now = now or data.get("now") or time.time()
        hits = 0
        with self.conn:
            for ac in data.get("aircraft", []):
                hx = (ac.get("hex") or "").lower()
                if not hx or hx.startswith("~"):  # '~' = non-ICAO (TIS-B) address
                    continue
                dist = in_range(self.cfg, ac)
                if dist is None:
                    continue
                self.record(hx, ac, dist, now)
                hits += 1
        return hits

    def record(self, hx: str, ac: dict, dist: float, now: float) -> None:
        c = self.conn
        callsign = (ac.get("flight") or "").strip() or None
        alt = altitude(ac)
        gs = ac.get("gs")
        emergency = ac.get("emergency")
        emergency = emergency if emergency and emergency != "none" else None
        m = AIRLINE_CALLSIGN.match(callsign or "")
        operator = m.group(1) if m else None
        if operator and not c.execute(
            "SELECT 1 FROM ref_operators WHERE icao=?", (operator,)
        ).fetchone():
            operator = None

        row = c.execute("SELECT * FROM airframes WHERE hex=?", (hx,)).fetchone()
        if row is None:
            ref = c.execute("SELECT * FROM ref_aircraft WHERE hex=?", (hx,)).fetchone()
            flags = (ref["flags"] if ref else "") or ""
            # readsb's own dbFlags (bit 0 military, bit 1 interesting) as fallback.
            dbf = int(ac.get("dbFlags", 0) or 0)
            card_no = (c.execute("SELECT COALESCE(MAX(card_no),0)+1 FROM airframes").fetchone()[0])
            c.execute(
                """INSERT INTO airframes (hex, card_no, reg, type, model, military, interesting,
                       category, operator, last_callsign, first_seen, last_seen, sightings,
                       closest_km, closest_alt_ft, max_alt_ft, max_gs_kt, emergency)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1,?,?,?,?,?)""",
                (
                    hx, card_no,
                    (ref["reg"] if ref else None) or ac.get("r"),
                    (ref["type"] if ref else None) or ac.get("t"),
                    (ref["model"] if ref else None) or ac.get("desc"),
                    int(flags[:1] == "1" or bool(dbf & 1)),
                    int(flags[1:2] == "1" or bool(dbf & 2)),
                    ac.get("category"), operator, callsign, now, now,
                    dist, alt, alt, gs, emergency,
                ),
            )
            c.execute(
                """INSERT INTO sightings (hex, callsign, start, end, min_dist_km, min_alt_ft,
                       max_alt_ft, max_gs_kt, closest_lat, closest_lon)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (hx, callsign, now, now, dist, alt, alt, gs, ac["lat"], ac["lon"]),
            )
            self.log(f"NEW CARD #{card_no}: {hx} {callsign or ''} "
                     f"{(ref['reg'] if ref else '') or ''} {(ref['type'] if ref else '') or ''} "
                     f"at {dist:.1f} km")
            return

        closer = row["closest_km"] is None or dist < row["closest_km"]
        sight = c.execute(
            "SELECT * FROM sightings WHERE hex=? ORDER BY end DESC LIMIT 1", (hx,)
        ).fetchone()
        new_sighting = sight is None or now - sight["end"] > self.cfg.sighting_gap_s

        c.execute(
            """UPDATE airframes SET last_seen=?, sightings=sightings+?,
                   operator=COALESCE(?, operator), last_callsign=COALESCE(?, last_callsign),
                   category=COALESCE(category, ?),
                   closest_km=?, closest_alt_ft=?, max_alt_ft=?, max_gs_kt=?,
                   emergency=COALESCE(emergency, ?)
               WHERE hex=?""",
            (
                now, int(new_sighting), operator, callsign, ac.get("category"),
                dist if closer else row["closest_km"],
                alt if closer else row["closest_alt_ft"],
                _max(row["max_alt_ft"], alt), _max(row["max_gs_kt"], gs),
                emergency, hx,
            ),
        )
        if new_sighting:
            c.execute(
                """INSERT INTO sightings (hex, callsign, start, end, min_dist_km, min_alt_ft,
                       max_alt_ft, max_gs_kt, closest_lat, closest_lon)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (hx, callsign, now, now, dist, alt, alt, gs, ac["lat"], ac["lon"]),
            )
        else:
            s_closer = sight["min_dist_km"] is None or dist < sight["min_dist_km"]
            c.execute(
                """UPDATE sightings SET end=?, callsign=COALESCE(callsign, ?),
                       min_dist_km=?, closest_lat=?, closest_lon=?,
                       min_alt_ft=?, max_alt_ft=?, max_gs_kt=?
                   WHERE id=?""",
                (
                    now, callsign,
                    dist if s_closer else sight["min_dist_km"],
                    ac["lat"] if s_closer else sight["closest_lat"],
                    ac["lon"] if s_closer else sight["closest_lon"],
                    _min(sight["min_alt_ft"], alt), _max(sight["max_alt_ft"], alt),
                    _max(sight["max_gs_kt"], gs), sight["id"],
                ),
            )


def main() -> None:
    cfg = cfgmod.load(sys.argv[1] if len(sys.argv) > 1 else None)
    conn = connect(cfg.database)
    refdb.update(conn, cfg, log=lambda m: print(m, flush=True))

    print(f"collector: receiver {cfg.lat:.4f},{cfg.lon:.4f}, radius {cfg.max_distance_km} km"
          + (f", ceiling {cfg.max_altitude_ft} ft" if cfg.max_altitude_ft else ""), flush=True)

    running = True

    def stop(*_):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    col = Collector(cfg, conn, log=lambda m: print(m, flush=True))
    last_ref_check = time.time()
    while running:
        try:
            col.poll_once()
        except (OSError, json.JSONDecodeError) as e:
            print(f"collector: read error: {e}", flush=True)
        if time.time() - last_ref_check > 6 * 3600:
            last_ref_check = time.time()
            refdb.update(conn, cfg, log=lambda m: print(m, flush=True))
        time.sleep(cfg.poll_interval_s)


if __name__ == "__main__":
    main()
