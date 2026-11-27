"""How rare is this card? A weighted, explained score.

Three factors each score 0 (ordinary) to 4 (exceptional) and are combined
with configurable weights (``[rarity]`` in config.toml):

* **Special livery** (default 45%): 4 for a one-of-a-kind livery, 3 for a
  special livery shared by a few aircraft, otherwise 0 (``specials`` table,
  seeded from specials.json, editable on the card back).
* **Worldwide numbers** (default 35%): from the number of registered airframes
  of the type (Mictronics / tar1090 database): thousands = 0, a handful = 4.
  Types being retired or out of production (``SUNSET``) score one point higher.
* **Local regularity** (default 20%): learned from your own receiver. On how
  many of the recent days was this airline + type (or the type, for aircraft
  without an airline callsign) heard? Daily = 0, (almost) never = 4. Until
  ``learn_days`` of data exist, it is blended with an estimate: having heard
  several different airframes of it already marks it as routine; otherwise
  the worldwide score is used.

The weighted score (0-4) maps to a tier with ``THRESHOLDS``. Then minimum
tiers: military and unidentified aircraft are at least rare; aircraft flagged
"interesting" and types with only a handful built are legendary.

Every card gets a list of human-readable reasons.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

TIERS = ["common", "uncommon", "rare", "epic", "legendary"]
WINDOW_DAYS = 60
DEFAULT_WEIGHTS = {"special": 0.45, "worldwide": 0.35, "local": 0.20}
DEFAULT_LEARN_DAYS = 28
# Upper bounds of the weighted score for common, uncommon, rare, epic.
THRESHOLDS = (0.6, 1.25, 1.9, 2.6)

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


def _local(p: float, k: int) -> float:
    """Local regularity score from the share of days it was heard (p) and days seen (k)."""
    if p >= 0.6:
        return 0.0
    if p >= 0.25:
        return 1.0
    if p >= 0.07:
        return 2.0
    return 3.0 if k > 1 else 4.0


def _tier(score: float) -> int:
    for i, upper in enumerate(THRESHOLDS):
        if score < upper:
            return i
    return 4


class RarityModel:
    def __init__(self, conn: sqlite3.Connection, now: float | None = None,
                 weights: dict | None = None, learn_days: float = DEFAULT_LEARN_DAYS):
        now = now or time.time()
        w = {**DEFAULT_WEIGHTS, **(weights or {})}
        total = sum(w.values()) or 1.0
        self.weights = {k: v / total for k, v in w.items()}   # normalised to sum to 1
        self.learn_days = max(1.0, float(learn_days))
        conn.executescript(SPECIALS_SCHEMA)
        since_day = time.strftime("%Y-%m-%d", time.localtime(now - WINDOW_DAYS * 86400))
        has_days = conn.execute("SELECT 1 FROM sqlite_master WHERE name='spotted_days'").fetchone()

        self.days = 0.0
        self.n_days = 0
        self.type_days: dict[str, set] = {}
        self.combo_days: dict[tuple, set] = {}
        self.type_air: dict[str, set] = {}
        self.combo_air: dict[tuple, set] = {}
        if has_days:
            all_days = set()
            for day, hx, typ, op in conn.execute(
                """SELECT d.day, d.hex, r.type, d.operator FROM spotted_days d
                   JOIN ref_aircraft r ON r.hex = d.hex WHERE d.day >= ?""", (since_day,)
            ):
                all_days.add(day)
                if typ:
                    self.type_days.setdefault(typ, set()).add(day)
                    self.type_air.setdefault(typ, set()).add(hx)
                    if op:
                        self.combo_days.setdefault((op, typ), set()).add(day)
                        self.combo_air.setdefault((op, typ), set()).add(hx)
            # Today only counts as the part of it that has passed.
            lt = time.localtime(now)
            today = time.strftime("%Y-%m-%d", lt)
            frac_today = (lt.tm_hour * 3600 + lt.tm_min * 60) / 86400
            self.days = len(all_days - {today}) + (frac_today if today in all_days else 0)
            self.n_days = len(all_days)

        self.population = dict(conn.execute(
            "SELECT type, COUNT(*) FROM ref_aircraft WHERE type IS NOT NULL GROUP BY type"))
        self.specials = {r[0]: {"title": r[1], "note": r[2], "one_off": bool(r[3]), "source": r[4]}
                         for r in conn.execute("SELECT hex, title, note, one_off, source FROM specials")}
        # For special liveries regularity is about that one aircraft, not its type.
        self.hex_days: dict[str, int] = {}
        if has_days and self.specials:
            q = ",".join("?" * len(self.specials))
            self.hex_days = dict(conn.execute(
                f"SELECT hex, COUNT(*) FROM spotted_days WHERE day >= ? AND hex IN ({q}) GROUP BY hex",
                (since_day, *self.specials)))

    # ------------------------------------------------------------------
    def assess(self, c: dict) -> tuple[str, list[str]]:
        typ, op, desc = c.get("type"), c.get("operator"), c.get("desc")
        reasons: list[str] = []
        W = self.weights
        pct = lambda k: f"{round(W[k] * 100)}%"
        type_label = c.get("type_name") or typ or "this type"
        op_label = (c.get("airline") or {}).get("name") or c.get("operator_name") or op

        # 1. Special livery
        sp = self.specials.get(c["hex"])
        s_special = (4.0 if sp["one_off"] else 3.0) if sp else 0.0
        if sp:
            reasons.append(f"Special livery ({pct('special')}): {sp['title']}"
                           + (f": {sp['note']}" if sp.get("note") else "")
                           + f" → {s_special:g}/4")

        # 2. Worldwide numbers (+1 for types on their way out)
        n = self.population.get(typ, 0) if typ else 0
        s_world = _prior(n, desc) if typ else 2.0
        world_txt = f"{n:,} registered" if typ else "unknown type"
        if typ in SUNSET:
            s_world = min(4.0, s_world + 1.0)
            world_txt += f"; {SUNSET[typ]}"
        reasons.append(f"Worldwide ({pct('worldwide')}): {world_txt} → {s_world:g}/4")

        # 3. Local regularity, blended with an estimate while still learning
        conf = min(1.0, self.days / self.learn_days)
        estimate = s_world
        local_txt = "nothing heard yet"
        s_local_raw = None
        if self.n_days and sp:
            k = self.hex_days.get(c["hex"], 0)
            p = min(1.0, k / max(self.days, 1.0))
            s_local_raw = _local(p, k)
            estimate = 2.0   # one aircraft: no way to guess its schedule yet
            local_txt = (f"{c.get('reg') or 'this aircraft'} itself heard on {k} of the last "
                         f"{self.n_days} day{'s' if self.n_days != 1 else ''}")
        elif self.n_days and typ:
            key_days = self.combo_days.get((op, typ)) if op else self.type_days.get(typ)
            n_air = len((self.combo_air.get((op, typ)) if op else self.type_air.get(typ)) or ())
            k = len(key_days or ())
            p = min(1.0, k / max(self.days, 1.0))
            s_local_raw = _local(p, k)
            ab = _abundance(n_air)
            ab_type = _abundance(len(self.type_air.get(typ) or ()))
            if ab is not None:
                estimate = min(estimate, ab)
            if ab_type is not None:
                estimate = min(estimate, ab_type + 0.5)   # weaker: same type, any airline
            what = f"{op_label} {typ}" if op else type_label
            local_txt = (f"{what} heard on {k} of the last {self.n_days} day{'s' if self.n_days != 1 else ''}"
                         f" ({n_air} airframe{'s' if n_air != 1 else ''})")
        s_local = conf * s_local_raw + (1 - conf) * estimate if s_local_raw is not None else estimate
        learning = f"; still learning ({self.days:.1f} of {self.learn_days:g} days)" if conf < 1 else ""
        reasons.append(f"Local ({pct('local')}): {local_txt}{learning} → {s_local:.1f}/4")

        score = W["special"] * s_special + W["worldwide"] * s_world + W["local"] * s_local
        tier = _tier(score)
        reasons.append(f"Score {score:.2f} of 4 → {TIERS[tier]}")

        # Minimum tiers
        floors = []
        if c.get("military"):
            floors.append((2, "Military aircraft: at least rare"))
        if not typ:
            floors.append((2, "Unidentified airframe: at least rare"))
        if c.get("interesting"):
            floors.append((4, "Flagged as interesting in the aircraft database: legendary"))
        if typ in LEGENDARY_TYPES:
            floors.append((4, "Only a handful exist: legendary"))
        for f, why in floors:
            if f > tier:
                reasons.append(why)
                tier = f

        return TIERS[tier], reasons
