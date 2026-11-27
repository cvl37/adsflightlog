"""Tiny stdlib web server: JSON API + the card-collection front end.

Run with:  python3 -m adsflightlog.web [config.toml]
"""

from __future__ import annotations

import json
import mimetypes
import re
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import config as cfgmod
from .cards import POINTS, TIERS, build_cards
from .collector import altitude, in_range
from .db import connect
from .logos import Logos
from . import tracks

STATIC = cfgmod.ROOT / "web"

CARD_SQL = """
SELECT a.*, t.name AS type_name, t.desc AS desc, t.wtc AS wtc,
       o.name AS operator_name, o.country AS operator_country, o.callsign AS operator_callsign
FROM airframes a
LEFT JOIN ref_types t ON t.type = a.type
LEFT JOIN ref_operators o ON o.icao = a.operator
"""


class App:
    def __init__(self, cfg: cfgmod.Config):
        self.cfg = cfg
        self.logos = Logos(cfg.database.parent, cfg.ref_refresh_days)

    def conn(self):
        c = connect(self.cfg.database)
        c.executescript(tracks.SCHEMA)
        return c

    def cards(self) -> list[dict]:
        with self.conn() as c:
            rows = [dict(r) for r in c.execute(CARD_SQL + " ORDER BY a.card_no")]
        for r in rows:
            r["airline"] = self.logos.info(r["operator"])
        return build_cards(rows)

    def summary(self) -> dict:
        cards = self.cards()
        now = time.time()
        with self.conn() as c:
            n_sightings = c.execute("SELECT COUNT(*) FROM sightings").fetchone()[0]
            today = c.execute(
                "SELECT COUNT(*) FROM sightings WHERE start > ?", (now - 86400,)
            ).fetchone()[0]
        by_tier = {t: 0 for t in TIERS}
        for card in cards:
            by_tier[card["rarity"]] += 1
        score = sum(c["points"] for c in cards)
        # Collector level: every level needs 20% more points than the last.
        level, need, acc = 1, 250, 0
        while score >= acc + need:
            acc += need
            level += 1
            need = int(need * 1.2)
        return {
            "receiver": {"lat": self.cfg.lat, "lon": self.cfg.lon},
            "zones": [{**vars(z), "text": z.describe()} for z in self.cfg.zones],
            "cards": len(cards),
            "types": len({c["type"] for c in cards if c["type"]}),
            "operators": len({c["operator"] for c in cards if c["operator"]}),
            "sightings": n_sightings,
            "sightings_24h": today,
            "new_24h": sum(1 for c in cards if "new" in c["badges"]),
            "by_tier": by_tier,
            "score": score,
            "level": level,
            "level_progress": (score - acc) / need,
            "points": POINTS,
        }

    def card(self, hx: str) -> dict | None:
        cards = {c["hex"]: c for c in self.cards()}
        card = cards.get(hx.lower())
        if not card:
            return None
        with self.conn() as c:
            card["history"] = [
                dict(r) for r in c.execute(
                    """SELECT s.*, t.n AS track_points, t.first_t AS track_from, t.last_t AS track_to
                       FROM sightings s LEFT JOIN sighting_tracks t ON t.sighting_id = s.id
                       WHERE s.hex=? ORDER BY s.start DESC LIMIT 50""", (hx,)
                )
            ]
        return card

    def track(self, sighting_id: int) -> dict | None:
        with self.conn() as c:
            s = c.execute("SELECT * FROM sightings WHERE id=?", (sighting_id,)).fetchone()
            if not s:
                return None
            pts = tracks.load(c, sighting_id) or []
        return {
            "sighting": dict(s),
            # [epoch_s, lat, lon, alt_ft|null, in_zone 0/1]
            "points": [[round(t, 1), lat, lon, alt, int(z)] for t, lat, lon, alt, z in pts],
        }

    def track_geojson(self, sighting_id: int) -> dict | None:
        tr = self.track(sighting_id)
        if not tr:
            return None
        pts, s = tr["points"], tr["sighting"]
        return {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {
                    "hex": s["hex"], "callsign": s["callsign"], "sighting_id": s["id"],
                    "zone_entry": s["start"], "zone_exit": s["end"],
                    # per-vertex extras, aligned with the coordinates
                    "times": [p[0] for p in pts],
                    "alt_ft": [p[3] for p in pts],
                    "in_zone": [p[4] for p in pts],
                },
                "geometry": {
                    "type": "LineString",
                    # GeoJSON order is lon, lat[, elevation in metres]
                    "coordinates": [
                        [p[2], p[1]] + ([round(p[3] * 0.3048)] if p[3] is not None else [])
                        for p in pts
                    ],
                },
            }],
        }

    def types(self) -> list[dict]:
        out: dict[str, dict] = {}
        for c in self.cards():
            t = c["type"] or "?"
            e = out.setdefault(t, {
                "type": t, "name": c.get("type_name") or c.get("model"), "desc": c.get("desc"),
                "art": c["art"], "count": 0, "rarity": c["rarity"], "first_seen": c["first_seen"],
            })
            e["count"] += 1
            if TIERS.index(c["rarity"]) > TIERS.index(e["rarity"]):
                e["rarity"] = c["rarity"]
            e["first_seen"] = min(e["first_seen"], c["first_seen"])
        return sorted(out.values(), key=lambda e: (-e["count"], e["type"]))

    def operators(self) -> list[dict]:
        out: dict[str, dict] = {}
        for c in self.cards():
            if not c["operator"]:
                continue
            e = out.setdefault(c["operator"], {
                "icao": c["operator"], "name": c.get("operator_name"),
                "country": c.get("operator_country"), "callsign": c.get("operator_callsign"),
                "count": 0, "types": set(), "airline": c.get("airline"),
            })
            e["count"] += 1
            if c["type"]:
                e["types"].add(c["type"])
        for e in out.values():
            e["types"] = sorted(e["types"])
        return sorted(out.values(), key=lambda e: (-e["count"], e["icao"]))

    def live(self) -> dict:
        try:
            data = json.loads(self.cfg.aircraft_json.read_text())
        except (OSError, json.JSONDecodeError):
            return {"aircraft": [], "error": "receiver data unavailable"}
        with self.conn() as c:
            known = {r[0] for r in c.execute("SELECT hex FROM airframes")}
        out, outside = [], 0
        for ac in data.get("aircraft", []):
            hx = (ac.get("hex") or "").lower()
            dist = in_range(self.cfg, ac)
            if dist is None:
                if "lat" in ac:
                    outside += 1
                continue
            out.append({
                "hex": hx, "callsign": (ac.get("flight") or "").strip() or None,
                "dist_km": round(dist, 1), "alt_ft": altitude(ac), "gs_kt": ac.get("gs"),
                "collected": hx in known,
            })
        out.sort(key=lambda a: a["dist_km"])
        return {"aircraft": out, "outside_radius": outside}


def make_handler(app: App):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # keep journald quiet
            pass

        def _json(self, obj, status=200):
            body = json.dumps(obj, default=list).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            url = urlparse(self.path)
            p = url.path
            try:
                if p == "/api/summary":
                    return self._json(app.summary())
                if p == "/api/cards":
                    return self._json(app.cards())
                if p.startswith("/api/card/"):
                    card = app.card(p.rsplit("/", 1)[-1])
                    return self._json(card) if card else self._json({"error": "not found"}, 404)
                m = re.fullmatch(r"/api/sighting/(\d+)/track(\.geojson)?", p)
                if m:
                    sid = int(m.group(1))
                    if m.group(2):
                        gj = app.track_geojson(sid)
                        if not gj:
                            return self._json({"error": "not found"}, 404)
                        body = json.dumps(gj).encode()
                        self.send_response(200)
                        self.send_header("Content-Type", "application/geo+json")
                        self.send_header("Content-Disposition",
                                         f'attachment; filename="sighting-{sid}.geojson"')
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                        self.wfile.write(body)
                        return
                    tr = app.track(sid)
                    return self._json(tr) if tr else self._json({"error": "not found"}, 404)
                if p == "/api/types":
                    return self._json(app.types())
                if p == "/api/operators":
                    return self._json(app.operators())
                if p == "/api/live":
                    return self._json(app.live())
                if p.startswith("/logo/"):
                    # /logo/<ICAO>/<variant>.svg — cached Soaring Symbols mark
                    parts = p.split("/")
                    if len(parts) == 4 and parts[3].endswith(".svg"):
                        body = app.logos.svg(parts[2], parts[3][:-4])
                        if body:
                            self.send_response(200)
                            self.send_header("Content-Type", "image/svg+xml")
                            # Third-party SVG: never let it run script on our origin.
                            self.send_header("Content-Security-Policy",
                                             "default-src 'none'; style-src 'unsafe-inline'")
                            self.send_header("X-Content-Type-Options", "nosniff")
                            self.send_header("Cache-Control", "public, max-age=604800")
                            self.send_header("Content-Length", str(len(body)))
                            self.end_headers()
                            self.wfile.write(body)
                            return
                    self.send_error(404)
                    return
            except Exception as e:  # noqa: BLE001 — surface errors to the UI
                return self._json({"error": str(e)}, 500)

            rel = "index.html" if p in ("", "/") else p.lstrip("/")
            f = (STATIC / rel).resolve()
            if STATIC.resolve() not in f.parents or not f.is_file():
                self.send_error(404)
                return
            body = f.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(f.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def main() -> None:
    cfg = cfgmod.load(sys.argv[1] if len(sys.argv) > 1 else None)
    connect(cfg.database).close()
    srv = ThreadingHTTPServer((cfg.web_host, cfg.web_port), make_handler(App(cfg)))
    print(f"web: http://{cfg.web_host}:{cfg.web_port}/", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
