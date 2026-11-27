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
from urllib.parse import parse_qs, unquote, urlparse

from . import config as cfgmod
from .cards import POINTS, TIERS, build_cards
from .collector import altitude, in_range
from .db import connect
from .logos import Logos
from .operators import OperatorResolver
from .rarity import RarityModel, SPECIALS_SCHEMA, load_seed_specials
from . import tracks
from . import fleet

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
        self.resolver = OperatorResolver(self.conn(), cfg.tar1090_html)
        load_seed_specials(self.conn())
        self._model: RarityModel | None = None
        self._model_t = 0.0

    def model(self) -> RarityModel:
        # Rebuilt every 10 minutes (or after a special-livery edit).
        if self._model is None or time.time() - self._model_t > 600:
            with self.conn() as c:
                self._model = RarityModel(c)
            self._model_t = time.time()
        return self._model

    def set_special(self, hx: str, title: str | None, note: str | None, one_off: bool) -> None:
        with self.conn() as c:
            c.executescript(SPECIALS_SCHEMA)
            if title:
                reg = c.execute("SELECT reg FROM airframes WHERE hex=?", (hx,)).fetchone()
                c.execute(
                    """INSERT INTO specials (hex, reg, title, note, one_off, source, added)
                       VALUES (?,?,?,?,?,'user',?)
                       ON CONFLICT(hex) DO UPDATE SET title=excluded.title, note=excluded.note,
                         one_off=excluded.one_off, source='user'""",
                    (hx, reg[0] if reg else None, title, note, int(one_off), time.time()))
            else:
                c.execute("DELETE FROM specials WHERE hex=?", (hx,))
        self._model = None

    def conn(self):
        c = connect(self.cfg.database)
        c.executescript(tracks.SCHEMA)
        c.executescript(fleet.SCHEMA)
        return c

    def cards(self) -> list[dict]:
        with self.conn() as c:
            rows = [dict(r) for r in c.execute(CARD_SQL + " ORDER BY a.card_no")]
        for r in rows:
            r["airline"] = self.logos.info(r["operator"])
            r["country"] = self.resolver.country(r["hex"])
        return build_cards(rows, self.model())

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

    # ---------- binder pages ----------
    @staticmethod
    def _progress(rows: list[dict]) -> dict:
        counted = [r for r in rows if not r.get("hidden") and r["status"] != "unconfirmed"]
        return {
            "collected": sum(r["collected"] for r in rows),
            "total": len(counted) + sum(1 for r in rows if r["collected"] and (r.get("hidden") or r["status"] == "unconfirmed")),
            "unconfirmed": sum(1 for r in rows if r["status"] == "unconfirmed" and not r["collected"] and not r.get("hidden")),
            "hidden": sum(1 for r in rows if r.get("hidden") and not r["collected"]),
        }

    def binder_airlines(self) -> list[dict]:
        cards = self.cards()
        ops = {}
        for c in cards:
            if c["operator"]:
                ops.setdefault(c["operator"], c)
        out = []
        with self.conn() as conn:
            for op, c in ops.items():
                rows = fleet.airline_fleet(conn, op)
                out.append({
                    "key": op, "name": (c.get("airline") or {}).get("name") or c.get("operator_name") or op,
                    "airline": c.get("airline"), **self._progress(rows),
                })
        return sorted(out, key=lambda e: (-e["collected"], e["name"]))

    def binder_airline(self, op: str) -> dict:
        op = op.upper()
        with self.conn() as conn:
            rows = fleet.airline_fleet(conn, op)
            o = conn.execute("SELECT * FROM ref_operators WHERE icao=?", (op,)).fetchone()
        info = self.logos.info(op)
        return {
            "key": op, "kind": "airline",
            "name": (info or {}).get("name") or (o["name"] if o else op),
            "subtitle": " · ".join(x for x in [o["country"] if o else None,
                                                 (info or {}).get("alliance"),
                                                 f"ICAO {op}"] if x),
            "airline": info, "rows": rows, **self._progress(rows),
        }

    def _spotted_all(self) -> list[dict]:
        with self.conn() as conn:
            rows = fleet.spotted_by(conn, "1", ())
        for r in rows:
            r["manufacturer"] = fleet.manufacturer(r["type_name"]) if r["type"] else "Unknown"
        return rows

    def binder_groups(self, by: str) -> list[dict]:
        key = "manufacturer" if by == "manufacturer" else "type"
        rows = self._spotted_all()
        have = {r[key] for r in rows if r["collected"] and r[key]}
        groups: dict[str, dict] = {}
        for r in rows:
            k = r[key]
            if k not in have:
                continue
            g = groups.setdefault(k, {"key": k, "name": k, "collected": 0, "total": 0, "types": set()})
            if by == "type":
                g["name"] = r["type_name"] or r["model"] or k
                g["manufacturer"] = r["manufacturer"]
            g["collected"] += r["collected"]
            g["total"] += 1
            if r["type"]:
                g["types"].add(r["type"])
        for g in groups.values():
            g["types"] = sorted(g["types"])
        return sorted(groups.values(), key=lambda g: (-g["collected"], g["name"]))

    def binder_group(self, by: str, k: str) -> dict:
        key = "manufacturer" if by == "manufacturer" else "type"
        rows = [r for r in self._spotted_all() if (r[key] or "").lower() == k.lower()]
        with self.conn() as conn:
            names = {o["icao"]: o["name"] for o in conn.execute("SELECT icao, name FROM ref_operators")}
        for r in rows:
            if r["operator"]:
                r["operator_name"] = (self.logos.info(r["operator"]) or {}).get("name") or names.get(r["operator"])
        name = k
        if by == "type" and rows:
            name = rows[0]["type_name"] or rows[0]["model"] or k
        return {
            "key": k, "kind": by, "name": name,
            "subtitle": f"{len(rows)} airframes heard by your receiver" if rows else "",
            "rows": rows, "collected": sum(r["collected"] for r in rows), "total": len(rows),
            "unconfirmed": 0, "hidden": 0,
        }

    def set_hidden(self, op: str, hx: str, hidden: bool) -> None:
        with self.conn() as conn:
            if hidden:
                conn.execute("INSERT OR IGNORE INTO fleet_hidden VALUES (?,?)", (op.upper(), hx.lower()))
            else:
                conn.execute("DELETE FROM fleet_hidden WHERE operator=? AND hex=?", (op.upper(), hx.lower()))

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
                if p == "/api/binder/airlines":
                    return self._json(app.binder_airlines())
                if p in ("/api/binder/manufacturers", "/api/binder/types"):
                    return self._json(app.binder_groups("manufacturer" if "manuf" in p else "type"))
                m = re.fullmatch(r"/api/binder/(airline|manufacturer|type)/([^/]+)", p)
                if m:
                    k = unquote(m.group(2))
                    if m.group(1) == "airline":
                        return self._json(app.binder_airline(k))
                    return self._json(app.binder_group(m.group(1), k))
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

        def do_POST(self):
            ms = re.fullmatch(r"/api/card/([0-9a-fA-F]{6})/special", urlparse(self.path).path)
            if ms:
                try:
                    n = int(self.headers.get("Content-Length") or 0)
                    body = json.loads(self.rfile.read(min(n, 8192)) or b"{}")
                    title = str(body.get("title") or "").strip()[:80] or None
                    note = str(body.get("note") or "").strip()[:500] or None
                    app.set_special(ms.group(1).lower(), title, note, bool(body.get("one_off", True)))
                    return self._json({"ok": True})
                except (ValueError, json.JSONDecodeError) as e:
                    return self._json({"error": str(e)}, 400)
            m = re.fullmatch(r"/api/binder/airline/([A-Za-z]{3})/hide", urlparse(self.path).path)
            if not m:
                self.send_error(404)
                return
            try:
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(min(n, 4096)) or b"{}")
                hx = str(body.get("hex", ""))
                if not re.fullmatch(r"[0-9a-fA-F]{6}", hx):
                    raise ValueError("bad hex")
                app.set_hidden(m.group(1), hx, bool(body.get("hidden", True)))
                return self._json({"ok": True})
            except (ValueError, json.JSONDecodeError) as e:
                return self._json({"error": str(e)}, 400)

    return Handler


def main() -> None:
    cfg = cfgmod.load(sys.argv[1] if len(sys.argv) > 1 else None)
    connect(cfg.database).close()
    srv = ThreadingHTTPServer((cfg.web_host, cfg.web_port), make_handler(App(cfg)))
    print(f"web: http://{cfg.web_host}:{cfg.web_port}/", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
