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
from .tracks import Tracker
from . import fleet
from . import editions
from .operators import OperatorResolver, fix_military
from . import home

AIRLINE_CALLSIGN = re.compile(r"^([A-Z]{3})\d")


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial true bearing from point 1 to point 2, 0..360."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return math.degrees(math.atan2(x, y)) % 360


def in_sector(brg: float, start: float, end: float) -> bool:
    """True if bearing lies on the clockwise arc from start to end (inclusive)."""
    span = (end - start) % 360 or 360
    return (brg - start) % 360 <= span


def altitude(ac: dict) -> int | None:
    alt = ac.get("alt_baro", ac.get("alt_geom"))
    if alt == "ground":
        return 0
    return int(alt) if isinstance(alt, (int, float)) else None


def zone_hit(zone: cfgmod.Zone, dist: float, brg: float, alt: int | None) -> bool:
    if dist > zone.max_distance_km:
        return False
    if zone.bearing_from is not None and not in_sector(brg, zone.bearing_from, zone.bearing_to):
        return False
    if zone.max_altitude_ft is not None:
        # Unknown altitude can't be shown to be below the ceiling: don't count it.
        if alt is None or alt >= zone.max_altitude_ft:
            return False
    return True


def in_range(cfg: cfgmod.Config, ac: dict) -> float | None:
    """Return distance in km if this aircraft is inside any zone, else None.

    Zones overlap freely; an aircraft inside several still counts once.
    """
    if "lat" not in ac or "lon" not in ac:
        return None
    if ac.get("seen_pos", 0) > cfg.max_position_age_s:
        return None
    dist = haversine_km(cfg.lat, cfg.lon, ac["lat"], ac["lon"])
    if dist > max(z.max_distance_km for z in cfg.zones):
        return None
    brg = bearing_deg(cfg.lat, cfg.lon, ac["lat"], ac["lon"])
    alt = altitude(ac)
    if any(zone_hit(z, dist, brg, alt) for z in cfg.zones):
        return dist
    return None


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
        self.tracker = Tracker(conn, cfg.track_before_s, cfg.track_after_s, log=log)
        self.spotter = fleet.Spotter(conn)
        self.resolver = OperatorResolver(conn, cfg.tar1090_html)
        self._military: dict[str, bool] = {}

    def is_military(self, hx: str, ac: dict) -> bool:
        if hx not in self._military:
            ref = self.conn.execute("SELECT flags FROM ref_aircraft WHERE hex=?", (hx,)).fetchone()
            flags = (ref[0] if ref else "") or ""
            self._military[hx] = flags[:1] == "1" or bool(int(ac.get("dbFlags", 0) or 0) & 1)
        return self._military[hx]

    def poll_once(self, now: float | None = None) -> int:
        data = json.loads(self.cfg.aircraft_json.read_text())
        now = now or data.get("now") or time.time()
        hits = 0
        with self.conn:
            for ac in data.get("aircraft", []):
                hx = (ac.get("hex") or "").lower()
                if not hx or hx.startswith("~"):  # '~' = non-ICAO (TIS-B) address
                    continue
                fresh = "lat" in ac and ac.get("seen_pos", 0) <= self.cfg.max_position_age_s
                if ac.get("seen", 0) <= 60:
                    # Fleet/spotting log: every aircraft heard, at any distance.
                    cs = (ac.get("flight") or "").strip() or None
                    self.spotter.observe(
                        hx, now,
                        haversine_km(self.cfg.lat, self.cfg.lon, ac["lat"], ac["lon"]) if fresh else None,
                        self.resolver.resolve(hx, cs, self.is_military(hx, ac)) if cs else None,
                    )
                if not fresh:
                    continue
                dist = in_range(self.cfg, ac)
                pos_t = now - ac.get("seen_pos", 0)
                self.tracker.observe(hx, pos_t, ac["lat"], ac["lon"], altitude(ac),
                                     ac.get("track", ac.get("true_heading")), dist is not None)
                if dist is None:
                    continue
                sid = self.record(hx, ac, dist, now)
                self.tracker.attach(hx, sid, now)
                hits += 1
        self.tracker.tick(now)
        self.spotter.maybe_flush(now)
        return hits

    def record(self, hx: str, ac: dict, dist: float, now: float) -> int:
        """Log an in-zone hit; returns the sighting id it belongs to."""
        c = self.conn
        callsign = (ac.get("flight") or "").strip() or None
        alt = altitude(ac)
        gs = ac.get("gs")
        emergency = ac.get("emergency")
        emergency = emergency if emergency and emergency != "none" else None
        military = self.is_military(hx, ac)
        operator = self.resolver.resolve(hx, callsign, military)
        if not military:
            known, home_op = home.lookup(c, hx)   # the airline it belongs to, not its flight number
            if known:
                operator = home_op

        row = c.execute("SELECT * FROM airframes WHERE hex=?", (hx,)).fetchone()
        if row is None:
            ref = c.execute("SELECT * FROM ref_aircraft WHERE hex=?", (hx,)).fetchone()
            flags = (ref["flags"] if ref else "") or ""
            # readsb's own dbFlags (bit 0 military, bit 1 interesting) as fallback.
            dbf = int(ac.get("dbFlags", 0) or 0)
            card_no = editions.next_card_no(c)   # unique across airframes and editions
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
            sid = c.execute(
                """INSERT INTO sightings (hex, callsign, start, end, min_dist_km, min_alt_ft,
                       max_alt_ft, max_gs_kt, closest_lat, closest_lon)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (hx, callsign, now, now, dist, alt, alt, gs, ac["lat"], ac["lon"]),
            ).lastrowid
            self.log(f"NEW CARD #{card_no}: {hx} {callsign or ''} "
                     f"{(ref['reg'] if ref else '') or ''} {(ref['type'] if ref else '') or ''} "
                     f"at {dist:.1f} km")
            return sid

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
            return c.execute(
                """INSERT INTO sightings (hex, callsign, start, end, min_dist_km, min_alt_ft,
                       max_alt_ft, max_gs_kt, closest_lat, closest_lon)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (hx, callsign, now, now, dist, alt, alt, gs, ac["lat"], ac["lon"]),
            ).lastrowid
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
            return sight["id"]


def main() -> None:
    cfg = cfgmod.load(sys.argv[1] if len(sys.argv) > 1 else None)
    conn = connect(cfg.database)
    refdb.update(conn, cfg, log=lambda m: print(m, flush=True))
    fleet.update_opensky(conn, log=lambda m: print(m, flush=True))

    editions.ensure_schema(conn)
    fleet.backfill_days(conn)
    from .rarity import load_seed_specials
    load_seed_specials(conn)
    fixed = fix_military(conn, OperatorResolver(conn, cfg.tar1090_html))
    if fixed:
        print(f"collector: corrected operator on {fixed} military record(s)", flush=True)
    resolver = OperatorResolver(conn, cfg.tar1090_html)
    moved = home.compute(conn, resolver)
    print(f"collector: home airlines updated ({moved} card(s) moved)", flush=True)

    print(f"collector: receiver {cfg.lat:.4f},{cfg.lon:.4f}; zones: "
          + "; ".join(f"{z.name} ({z.describe()})" for z in cfg.zones), flush=True)

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
            fleet.update_opensky(conn, log=lambda m: print(m, flush=True))
            col.spotter.flush()
            moved = home.compute(conn, resolver)
            if moved:
                print(f"collector: {moved} card(s) moved to their home airline", flush=True)
        time.sleep(cfg.poll_interval_s)
    col.tracker.flush()
    col.spotter.flush()
    print("collector: stopped, tracks saved", flush=True)


if __name__ == "__main__":
    main()
