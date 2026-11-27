"""How rare is this card? Explained, data-driven rarity.

The score runs from 0 (common) to 4 (legendary) and blends two signals:

* **Local regularity**: the main signal, learned from your own receiver.
  On how many of the recent days (``WINDOW_DAYS``) was this airline + type
  combination heard (or the type, for aircraft without an airline callsign)?
  An American Airlines 777-200 that comes to Schiphol daily is common here,
  however few of them exist. The signal's weight grows from 0 to 1 over the
  first ``CONFIDENT_DAYS`` days of data.
* **Worldwide population**: the starting estimate while local data is thin.
  While the local signal is still weak, having already heard 3+ (or 6+)
  different airframes of the same airline + type also marks it as routine.
  It is the number of registered airframes of the type in the Mictronics /
  tar1090 aircraft database.

Then adjustments:

* type being retired / out of production (``SUNSET``): +0.75
* the only airframe of its type in that airline's fleet: +1
* special livery (``specials`` table): at least epic, legendary if one of a kind
* aircraft flagged military: at least rare
* unidentified airframe: at least rare
* "interesting" flag in the database, or a handful-in-the-world type: legendary

Every card gets a list of human-readable reasons.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

TIERS = ["common", "uncommon", "rare", "epic", "legendary"]
WINDOW_DAYS = 60
CONFIDENT_DAYS = 7
FLEET_CONFIRM_DAYS = 180
MIN_CONFIRMED_FLEET = 20

# Types with only a handful of airframes, or famous one-offs.
LEGENDARY_TYPES = {"A124", "A225", "A3ST", "A337", "BLCF", "C5M", "CONC", "B52", "U2"}

# Out of production and/or being retired from passenger service.
SUNSET = {
    "B741": "Boeing 747 classic, almost all retired",
    "B742": "Boeing 747 classic, almost all retired",
    "B743": "Boeing 747 classic, almost all retired",
    "B744": "Boeing 747-400: passenger fleets retired, last ones flying cargo",
    "B748": "Boeing 747-8: production ended in 2023",
    "A388": "Airbus A380: production ended in 2021",
    "MD11": "MD-11: last ones flying cargo",
    "DC10": "DC-10: almost all retired",
    "A342": "Airbus A340: out of production, being retired",
    "A343": "Airbus A340: out of production, being retired",
    "A345": "Airbus A340: out of production, being retired",
    "A346": "Airbus A340: out of production, being retired",
    "A306": "Airbus A300: out of production, cargo only",
    "A30B": "Airbus A300: out of production",
    "A310": "Airbus A310: out of production, few left",
    "B752": "Boeing 757: out of production, being retired",
    "B753": "Boeing 757: out of production, being retired",
    "B762": "Boeing 767-200: out of production, being retired",
    "B733": "Boeing 737 classic: out of production, being retired",
    "B734": "Boeing 737 classic: out of production, being retired",
    "B735": "Boeing 737 classic: out of production, being retired",
    "B712": "Boeing 717: out of production, being retired",
    "MD82": "MD-80 series: almost all retired", "MD83": "MD-80 series: almost all retired",
    "MD87": "MD-80 series: almost all retired", "MD88": "MD-80 series: almost all retired",
    "F70": "Fokker 70: out of production, being retired",
    "F100": "Fokker 100: out of production, being retired",
    "F50": "Fokker 50: out of production, being retired",
    "B461": "BAe 146: out of production, being retired",
    "B462": "BAe 146: out of production, being retired",
    "B463": "BAe 146: out of production, being retired",
    "RJ85": "Avro RJ: out of production, being retired",
    "RJ1H": "Avro RJ: out of production, being retired",
    "CRJ1": "CRJ100: out of production, being retired",
    "CRJ2": "CRJ200: out of production, being retired",
    "DH8A": "Dash 8-100: out of production, being retired",
    "DH8B": "Dash 8-200: out of production, being retired",
    "DH8C": "Dash 8-300: out of production, being retired",
    "SF34": "Saab 340: out of production, being retired",
    "SB20": "Saab 2000: out of production, few left",
    "D328": "Dornier 328: out of production",
    "E135": "Embraer ERJ-135: out of production",
    "E145": "Embraer ERJ-145: out of production",
    "IL62": "Ilyushin Il-62: almost all retired",
    "IL76": "Ilyushin Il-76: few in western airspace",
    "T154": "Tupolev Tu-154: almost all retired",
}

SPECIALS_SCHEMA = """
CREATE TABLE IF NOT EXISTS specials (
    hex     TEXT PRIMARY KEY,
    reg     TEXT,
    title   TEXT NOT NULL,
    note    TEXT,
    one_off INTEGER NOT NULL DEFAULT 1,   -- the only one like it
    source  TEXT NOT NULL DEFAULT 'user', -- 'seed' (specials.json) or 'user'
    added   REAL
) WITHOUT ROWID;
"""
SEED_FILE = Path(__file__).with_name("specials.json")


def load_seed_specials(conn: sqlite3.Connection) -> int:
    """Add seed specials by registration; never overwrites a user's entry."""
    conn.executescript(SPECIALS_SCHEMA)
    if not SEED_FILE.exists():
        return 0
    n = 0
    with conn:
        for s in json.loads(SEED_FILE.read_text()):
            row = conn.execute("SELECT hex FROM ref_aircraft WHERE upper(reg)=upper(?)", (s["reg"],)).fetchone()
            if not row:
                continue
            cur = conn.execute(
                """INSERT INTO specials (hex, reg, title, note, one_off, source, added)
                   VALUES (?,?,?,?,?,'seed',?)
                   ON CONFLICT(hex) DO UPDATE SET title=excluded.title, note=excluded.note,
                     one_off=excluded.one_off WHERE specials.source='seed'""",
                (row[0], s["reg"], s["title"], s.get("note"), int(s.get("one_off", True)), time.time()),
            )
            n += cur.rowcount
    return n


def _prior(n: int, desc: str | None) -> float:
    """Tier estimate from worldwide population."""
    if n >= 1500:
        s = 0
    elif n >= 300:
        s = 1
    elif n >= 80:
        s = 2
    elif n >= 15:
        s = 3
    else:
        s = 4
    # Small home-built / light piston types: rare at most on population alone.
    if desc and desc[1:2] == "1" and desc[2:3] == "P":
        s = min(s, 2)
    return float(s)


def _abundance(n_airframes: int) -> float | None:
    """Cold-start hint: many different airframes of it heard already = routine traffic."""
    if n_airframes >= 6:
        return 0.0
    if n_airframes >= 3:
        return 1.0
    return None


def _local(p: float) -> float:
    """Tier estimate from the share of days it was heard."""
    if p >= 0.6:
        return 0.0
    if p >= 0.25:
        return 1.0
    if p >= 0.07:
        return 2.0
    return 3.0


class RarityModel:
    def __init__(self, conn: sqlite3.Connection, now: float | None = None):
        now = now or time.time()
        conn.executescript(SPECIALS_SCHEMA)
        since_day = time.strftime("%Y-%m-%d", time.localtime(now - WINDOW_DAYS * 86400))
        has_days = conn.execute("SELECT 1 FROM sqlite_master WHERE name='spotted_days'").fetchone()

        self.days = 0
        self.type_days: dict[str, set] = {}
        self.combo_days: dict[tuple, set] = {}
        self.type_air: dict[str, set] = {}
        self.combo_air: dict[tuple, set] = {}
        if has_days:
            rows = conn.execute(
                """SELECT d.day, d.hex, r.type, d.operator FROM spotted_days d
                   JOIN ref_aircraft r ON r.hex = d.hex WHERE d.day >= ?""", (since_day,)
            ).fetchall()
            all_days = set()
            for day, hx, typ, op in rows:
                all_days.add(day)
                if typ:
                    self.type_days.setdefault(typ, set()).add(day)
                    self.type_air.setdefault(typ, set()).add(hx)
                    if op:
                        self.combo_days.setdefault((op, typ), set()).add(day)
                        self.combo_air.setdefault((op, typ), set()).add(hx)
            # Today only counts as a fraction until it is over.
            today = time.strftime("%Y-%m-%d", time.localtime(now))
            lt = time.localtime(now)
            frac_today = (lt.tm_hour * 3600 + lt.tm_min * 60) / 86400
            self.days = len(all_days - {today}) + (frac_today if today in all_days else 0)
            self.n_days = len(all_days)
        else:
            self.n_days = 0

        self.population = dict(conn.execute(
            "SELECT type, COUNT(*) FROM ref_aircraft WHERE type IS NOT NULL GROUP BY type"))

        fleet_since = now - FLEET_CONFIRM_DAYS * 86400
        self.fleet: dict[tuple, int] = {}
        self.fleet_size: dict[str, int] = {}
        # Airframes confirmed flying for each operator (heard with its callsign).
        self.confirmed: dict[str, int] = {}
        if conn.execute("SELECT 1 FROM sqlite_master WHERE name='spotted_ops'").fetchone():
            self.confirmed = dict(conn.execute(
                "SELECT operator, COUNT(DISTINCT hex) FROM spotted_ops WHERE last_seen >= ? GROUP BY operator",
                (now - FLEET_CONFIRM_DAYS * 86400,)))
        if conn.execute("SELECT 1 FROM sqlite_master WHERE name='ref_fleet'").fetchone():
            for op, typ, n in conn.execute(
                """SELECT operator, type, COUNT(DISTINCT hex) FROM (
                       SELECT f.operator, f.hex, COALESCE(r.type, f.type) AS type
                       FROM ref_fleet f LEFT JOIN ref_aircraft r ON r.hex = f.hex
                       UNION
                       SELECT o.operator, o.hex, r.type FROM spotted_ops o
                       JOIN ref_aircraft r ON r.hex = o.hex WHERE o.last_seen >= ?
                       UNION
                       SELECT a.operator, a.hex, a.type FROM airframes a WHERE a.operator IS NOT NULL
                   ) WHERE type IS NOT NULL GROUP BY operator, type""", (fleet_since,)
            ):
                self.fleet[(op, typ)] = n
                self.fleet_size[op] = self.fleet_size.get(op, 0) + n

        self.specials = {r[0]: {"title": r[1], "note": r[2], "one_off": bool(r[3]), "source": r[4]}
                         for r in conn.execute("SELECT hex, title, note, one_off, source FROM specials")}

    # ------------------------------------------------------------------
    def assess(self, c: dict) -> tuple[str, list[str]]:
        typ, op, desc = c.get("type"), c.get("operator"), c.get("desc")
        reasons: list[str] = []
        type_label = c.get("type_name") or typ or "this type"
        op_label = (c.get("airline") or {}).get("name") or c.get("operator_name") or op

        # Worldwide population prior
        n = self.population.get(typ, 0) if typ else 0
        prior = _prior(n, desc) if typ else 2.0
        if typ:
            reasons.append(f"{n:,} registered worldwide")

        # Local regularity
        w = min(1.0, self.days / CONFIDENT_DAYS)
        score = prior
        if self.n_days and typ:
            key_days = self.combo_days.get((op, typ)) if op else self.type_days.get(typ)
            n_air = len((self.combo_air.get((op, typ)) if op else self.type_air.get(typ)) or ())
            k = len(key_days or ())
            p = min(1.0, k / max(self.days, 1.0))
            ab = _abundance(n_air)
            ab_type = _abundance(len(self.type_air.get(typ) or ()))
            cold = prior
            if ab is not None:
                cold = min(cold, ab)
            if ab_type is not None:
                cold = min(cold, ab_type + 0.5)   # weaker: same type, any airline
            score = w * _local(p) + (1 - w) * cold
            what = f"{op_label} {typ}" if op else type_label
            reasons.append(f"{what}: heard on {k} of the last {self.n_days} day{'s' if self.n_days != 1 else ''}"
                           f" ({n_air} different airframe{'s' if n_air != 1 else ''})")
            if w < 1:
                reasons.append(f"Still learning local traffic ({self.days:.1f} of {CONFIDENT_DAYS} days)")

        # Adjustments
        if typ in SUNSET:
            score += 0.75
            reasons.append(SUNSET[typ])
        # Only claim "the only one" once we've confirmed a good part of the fleet ourselves.
        if op and typ and self.fleet.get((op, typ)) == 1 and self.confirmed.get(op, 0) >= MIN_CONFIRMED_FLEET:
            score += 1.0
            reasons.append(f"The only {type_label} in {op_label}'s fleet")

        tier = int(min(4, max(0, score + 0.5)))

        floors = []
        if c.get("military"):
            floors.append((2, "Military aircraft"))
        if not typ:
            floors.append((2, "Unidentified airframe"))
        sp = self.specials.get(c["hex"])
        if sp:
            floors.append((4 if sp["one_off"] else 3,
                           f"Special livery: {sp['title']}" + (f": {sp['note']}" if sp.get("note") else "")))
        if c.get("interesting"):
            floors.append((4, "Flagged as interesting in the aircraft database"))
        if typ in LEGENDARY_TYPES:
            floors.append((4, "Only a handful exist"))
        for f, why in floors:
            reasons.append(why)
            tier = max(tier, f)

        return TIERS[tier], reasons
