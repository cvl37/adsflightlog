"""Fleet data for the binder pages: which airframes exist that you could still catch.

Two sources:

1. **Spotted**: every aircraft your receiver hears, at any distance, is logged
   (``spotted``), and so is every airline callsign it flies under
   (``spotted_ops``). An airframe that belongs to KLM (home.py: not just any
   aircraft flying a KLM flight number) and was heard within ``CONFIRM_DAYS``
   is a confirmed member of KLM's fleet. This data is current and local, and it
   also lists aircraft you've seen in range but not yet caught.

2. **OpenSky**: the OpenSky Network aircraft database
   (https://opensky-network.org, crowdsourced, provided "as is") has an
   operator ICAO code for about 50k airframes, but its last full export is
   old. We use it as a seed list and drop entries that have been re-registered
   since (registration differs from the current Mictronics database) or that
   were heard flying for another airline.

Writes are batched in memory and flushed every few minutes to spare the SD card.
"""

from __future__ import annotations

import csv
import io
import re
import sqlite3
import time
import urllib.request

from . import home

OPENSKY_LIST = "https://s3.opensky-network.org/data-samples?list-type=2&prefix=metadata/aircraft-database-complete-"
OPENSKY_FILE = "https://s3.opensky-network.org/data-samples/{key}"
CONFIRM_DAYS = 180
FLUSH_EVERY_S = 300
AIRLINE_CALLSIGN = re.compile(r"^([A-Z]{3})\d")

SCHEMA = """
CREATE TABLE IF NOT EXISTS spotted (
    hex         TEXT PRIMARY KEY,
    first_seen  REAL NOT NULL,
    last_seen   REAL NOT NULL,
    min_dist_km REAL
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS spotted_ops (
    hex        TEXT NOT NULL,
    operator   TEXT NOT NULL,
    first_seen REAL NOT NULL,
    last_seen  REAL NOT NULL,
    PRIMARY KEY (hex, operator)
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS spotted_ops_op ON spotted_ops(operator, last_seen);

-- One row per airframe per local day it was heard: drives "how regular is it here".
CREATE TABLE IF NOT EXISTS spotted_days (
    day      TEXT NOT NULL,       -- YYYY-MM-DD, local time
    hex      TEXT NOT NULL,
    operator TEXT,
    PRIMARY KEY (day, hex)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS ref_fleet (
    hex      TEXT PRIMARY KEY,
    operator TEXT NOT NULL,
    reg      TEXT,
    type     TEXT
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS ref_fleet_op ON ref_fleet(operator);

-- Sleeves you've marked as "not in this fleet any more".
CREATE TABLE IF NOT EXISTS fleet_hidden (
    operator TEXT NOT NULL,
    hex      TEXT NOT NULL,
    PRIMARY KEY (operator, hex)
) WITHOUT ROWID;
""" + home.SCHEMA


def manufacturer(type_name: str | None) -> str:
    """'AIRBUS A-320neo' -> 'Airbus', 'DE HAVILLAND DHC-8-400' -> 'De Havilland'."""
    if not type_name:
        return "Unknown"
    out = []
    for tok in type_name.split():
        if tok.isupper() and not re.search(r"[0-9\-/]", tok):
            out.append(tok)
        else:
            break
    name = " ".join(out) or type_name.split()[0].split("-")[0]
    # Short acronyms (ATR, PZL, MBB) stay upper-case; names get title case.
    return name if len(name) <= 3 else name.title()


# ---------------------------------------------------------------- spotting
class Spotter:
    """Collects every aircraft heard (any distance) and flushes in batches."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        conn.executescript(SCHEMA)
        self.seen: dict[str, list] = {}               # hex -> [first, last, min_dist]
        self.ops: dict[tuple[str, str], list] = {}    # (hex, op) -> [first, last]
        self.days: dict[tuple[str, str], str | None] = {}  # (day, hex) -> operator
        self.last_flush = time.time()

    def observe(self, hx: str, t: float, dist_km: float | None, operator: str | None) -> None:
        """``operator`` is the already-resolved operator code (see operators.py), or None."""
        s = self.seen.get(hx)
        if s is None:
            self.seen[hx] = [t, t, dist_km]
        else:
            s[1] = t
            if dist_km is not None and (s[2] is None or dist_km < s[2]):
                s[2] = dist_km
        dk = (time.strftime("%Y-%m-%d", time.localtime(t)), hx)
        if operator or dk not in self.days:
            self.days[dk] = operator
        if operator:
            k = (hx, operator)
            o = self.ops.get(k)
            if o is None:
                self.ops[k] = [t, t]
            else:
                o[1] = t

    def maybe_flush(self, now: float) -> None:
        if now - self.last_flush >= FLUSH_EVERY_S:
            self.flush()
            self.last_flush = now

    def flush(self) -> None:
        if not self.seen and not self.ops and not self.days:
            return
        with self.conn:
            self.conn.executemany(
                """INSERT INTO spotted VALUES (?,?,?,?)
                   ON CONFLICT(hex) DO UPDATE SET
                     last_seen = MAX(last_seen, excluded.last_seen),
                     min_dist_km = MIN(COALESCE(min_dist_km, excluded.min_dist_km),
                                       COALESCE(excluded.min_dist_km, min_dist_km))""",
                [(h, f, l, d) for h, (f, l, d) in self.seen.items()],
            )
            self.conn.executemany(
                """INSERT INTO spotted_ops VALUES (?,?,?,?)
                   ON CONFLICT(hex, operator) DO UPDATE SET
                     last_seen = MAX(last_seen, excluded.last_seen)""",
                [(h, op, f, l) for (h, op), (f, l) in self.ops.items()],
            )
            self.conn.executemany(
                """INSERT INTO spotted_days VALUES (?,?,?)
                   ON CONFLICT(day, hex) DO UPDATE SET operator = COALESCE(excluded.operator, operator)""",
                [(d, h, op) for (d, h), op in self.days.items()],
            )
            cutoff = time.strftime("%Y-%m-%d", time.localtime(time.time() - 120 * 86400))
            self.conn.execute("DELETE FROM spotted_days WHERE day < ?", (cutoff,))
        self.seen.clear()
        self.ops.clear()
        self.days.clear()


def backfill_days(conn: sqlite3.Connection) -> None:
    """Seed spotted_days from data logged before it existed (one-off, idempotent)."""
    conn.executescript(SCHEMA)
    with conn:
        conn.execute(
            """INSERT OR IGNORE INTO spotted_days
               SELECT date(o.last_seen, 'unixepoch', 'localtime'), o.hex, o.operator FROM spotted_ops o""")
        conn.execute(
            """INSERT OR IGNORE INTO spotted_days
               SELECT date(s.last_seen, 'unixepoch', 'localtime'), s.hex, NULL FROM spotted s""")
        conn.execute(
            """INSERT OR IGNORE INTO spotted_days
               SELECT date(s.start, 'unixepoch', 'localtime'), s.hex, a.operator
               FROM sightings s JOIN airframes a ON a.hex = s.hex""")


# ---------------------------------------------------------------- OpenSky seed
def _latest_opensky_key() -> str | None:
    req = urllib.request.Request(OPENSKY_LIST, headers={"User-Agent": "adsflightlog"})
    with urllib.request.urlopen(req, timeout=60) as r:
        keys = re.findall(r"<Key>([^<]+\.csv)</Key>", r.read().decode())
    return max(keys) if keys else None


def update_opensky(conn: sqlite3.Connection, refresh_days: float = 30, log=print) -> None:
    """Import operator assignments from the newest complete OpenSky export (if new)."""
    conn.executescript(SCHEMA)
    row = conn.execute("SELECT value FROM meta WHERE key='opensky_checked'").fetchone()
    if row and time.time() - float(row[0]) < refresh_days * 86400:
        return
    try:
        key = _latest_opensky_key()
        if not key:
            raise ValueError("no exports listed")
        have = conn.execute("SELECT value FROM meta WHERE key='opensky_key'").fetchone()
        if have and have[0] == key:
            log(f"fleet: OpenSky export {key} already imported")
        else:
            log(f"fleet: downloading OpenSky {key} (~100 MB, streamed) ...")
            req = urllib.request.Request(OPENSKY_FILE.format(key=key), headers={"User-Agent": "adsflightlog"})
            rows = []
            with urllib.request.urlopen(req, timeout=600) as r:
                text = io.TextIOWrapper(r, encoding="utf-8", errors="replace", newline="")
                rd = csv.reader(text, quotechar="'")
                hdr = next(rd)
                ix = {h: i for i, h in enumerate(hdr)}
                need = ("icao24", "operatorIcao", "registration", "typecode")
                if not all(k in ix for k in need):
                    raise ValueError(f"unexpected columns: {hdr[:8]}")
                for rec in rd:
                    if len(rec) != len(hdr):
                        continue
                    op = rec[ix["operatorIcao"]].strip().upper()
                    if not re.fullmatch(r"[A-Z]{3}", op):
                        continue
                    rows.append((rec[ix["icao24"]].strip().lower(), op,
                                 rec[ix["registration"]].strip() or None,
                                 rec[ix["typecode"]].strip().upper() or None))
            with conn:
                conn.execute("DELETE FROM ref_fleet")
                conn.executemany("INSERT OR REPLACE INTO ref_fleet VALUES (?,?,?,?)", rows)
                conn.execute("INSERT OR REPLACE INTO meta VALUES ('opensky_key', ?)", (key,))
            log(f"fleet: imported {len(rows)} operator assignments from {key}")
    except Exception as e:  # noqa: BLE001 — fleet seed is optional
        log(f"fleet: OpenSky update failed ({e})")
    with conn:
        conn.execute("INSERT OR REPLACE INTO meta VALUES ('opensky_checked', ?)", (str(time.time()),))


# ---------------------------------------------------------------- queries
def airline_fleet(conn: sqlite3.Connection, op: str, now: float | None = None) -> list[dict]:
    """All airframes believed to be in ``op``'s fleet, with their status."""
    now = now or time.time()
    since = now - CONFIRM_DAYS * 86400
    # Each airframe belongs to one airline (home.py): flying KLM flight numbers
    # doesn't put a HOP or German Airways jet in KLM's fleet.
    q = """
    WITH home AS (SELECT hex, operator FROM airframe_home),
    confirmed AS (   -- belongs here and heard flying recently (under any callsign)
        SELECT o.hex, MAX(o.last_seen) AS last_op FROM spotted_ops o
        LEFT JOIN home h ON h.hex = o.hex
        WHERE o.last_seen >= :since
          AND (CASE WHEN h.hex IS NULL THEN o.operator ELSE h.operator END) = :op
        GROUP BY o.hex
    ),
    listed AS (
        SELECT f.hex FROM ref_fleet f
        LEFT JOIN ref_aircraft r ON r.hex = f.hex
        WHERE f.operator = :op
          AND f.hex NOT IN (SELECT hex FROM home)   -- heard: home.py decided already
          -- re-registered since the OpenSky export: probably sold
          AND (r.reg IS NULL OR f.reg IS NULL
               OR replace(upper(r.reg), '-', '') = replace(upper(f.reg), '-', ''))
    ),
    members AS (
        SELECT hex FROM confirmed
        UNION SELECT hex FROM listed
        UNION SELECT hex FROM home WHERE operator = :op
        UNION SELECT hex FROM airframes WHERE operator = :op
    )
    SELECT m.hex,
           COALESCE(a.reg, r.reg, f.reg) AS reg,
           COALESCE(a.type, r.type, f.type) AS type,
           COALESCE(a.model, r.model) AS model,
           t.name AS type_name, t.desc AS desc,
           a.card_no IS NOT NULL AS collected, a.card_no,
           c.last_op, s.last_seen AS spotted_last, s.min_dist_km AS spotted_min_km,
           f.hex IS NOT NULL AS in_opensky,
           h.hex IS NOT NULL AS hidden
    FROM members m
    LEFT JOIN airframes a ON a.hex = m.hex
    LEFT JOIN ref_aircraft r ON r.hex = m.hex
    LEFT JOIN ref_fleet f ON f.hex = m.hex AND f.operator = :op
    LEFT JOIN ref_types t ON t.type = COALESCE(a.type, r.type, f.type)
    LEFT JOIN confirmed c ON c.hex = m.hex
    LEFT JOIN spotted s ON s.hex = m.hex
    LEFT JOIN fleet_hidden h ON h.operator = :op AND h.hex = m.hex
    """
    rows = [dict(r) for r in conn.execute(q, {"op": op, "since": since})]
    confirmed_types = {r["type"] for r in rows if r["last_op"] or r["collected"]}
    for r in rows:
        r["collected"] = bool(r["collected"])
        r["hidden"] = bool(r["hidden"])
        if r["collected"] or r["last_op"]:
            r["status"] = "confirmed"
        elif r["type"] in confirmed_types:
            r["status"] = "listed"          # OpenSky only, but the airline does fly this type
        else:
            r["status"] = "unconfirmed"     # OpenSky only, type never seen for this airline
    return rows


def spotted_by(conn: sqlite3.Connection, where: str, params: tuple) -> list[dict]:
    """Spotted (or collected) airframes matching a ref_aircraft/ref_types filter."""
    q = f"""
    SELECT s.hex, COALESCE(a.reg, r.reg) AS reg, COALESCE(a.type, r.type) AS type,
           COALESCE(a.model, r.model) AS model, t.name AS type_name, t.desc AS desc,
           a.card_no IS NOT NULL AS collected, a.card_no,
           s.last_seen AS spotted_last, s.min_dist_km AS spotted_min_km,
           CASE WHEN EXISTS (SELECT 1 FROM airframe_home h WHERE h.hex = s.hex)
                THEN (SELECT operator FROM airframe_home h WHERE h.hex = s.hex)
                ELSE COALESCE((SELECT operator FROM spotted_ops o WHERE o.hex = s.hex
                               ORDER BY last_seen DESC LIMIT 1), a.operator) END AS operator
    FROM (SELECT hex, last_seen, min_dist_km FROM spotted
          UNION SELECT hex, last_seen, closest_km FROM airframes WHERE hex NOT IN (SELECT hex FROM spotted)) s
    LEFT JOIN airframes a ON a.hex = s.hex
    LEFT JOIN ref_aircraft r ON r.hex = s.hex
    LEFT JOIN ref_types t ON t.type = COALESCE(a.type, r.type)
    WHERE {where}
    """
    rows = [dict(r) for r in conn.execute(q, params)]
    for r in rows:
        r["collected"] = bool(r["collected"])
        r["status"] = "confirmed" if r["collected"] else "spotted"
    return rows
