"""Registered operator per airframe from hexdb.io (https://hexdb.io).

hexdb.io is a free, keyless lookup of the BaseStation-style aircraft database
maintained by the spotting community. For each ICAO address it gives the
registration, the registered owner and the operator's ICAO code (F-HBLJ ->
HOP, YR-ABA -> KRP). That is the first thing home.py trusts.

Lookups are one aircraft at a time, so a background thread works through the
airframes slowly (one request every ``INTERVAL_S``): caught cards first, then
airframes heard under several callsigns, then everything else the receiver or
the airport history has seen. Answers, including "not found", are cached in
``ref_owner`` and re-checked after ``REFRESH_DAYS``.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

URL = "https://hexdb.io/api/v1/aircraft/{hex}"
INTERVAL_S = 2.0
REFRESH_DAYS = 90
BACKOFF_S = 600

SCHEMA = """
CREATE TABLE IF NOT EXISTS ref_owner (
    hex      TEXT PRIMARY KEY,
    reg      TEXT,
    operator TEXT,            -- ICAO operator code (OperatorFlagCode), NULL if none
    owner    TEXT,            -- registered owner / operator name
    fetched  REAL NOT NULL,
    found    INTEGER NOT NULL
) WITHOUT ROWID;
"""


def fetch(hx: str, timeout: float = 15) -> dict | None:
    """hexdb.io record for one ICAO address, or None if it doesn't know it."""
    req = urllib.request.Request(URL.format(hex=hx.lower()), headers={"User-Agent": "adsflightlog"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    if not isinstance(data, dict) or data.get("status") == "404":
        return None
    return data


def store(conn: sqlite3.Connection, hx: str, rec: dict | None, now: float | None = None) -> None:
    now = now or time.time()
    op = ((rec or {}).get("OperatorFlagCode") or "").strip().upper() or None
    if op and not (len(op) == 3 and op.isalpha()):
        op = None
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO ref_owner VALUES (?,?,?,?,?,?)",
            (hx.lower(), ((rec or {}).get("Registration") or "").strip() or None, op,
             ((rec or {}).get("RegisteredOwners") or "").strip() or None, now, int(rec is not None)))


def next_hex(conn: sqlite3.Connection, now: float | None = None) -> tuple[str, bool] | None:
    """Next airframe to look up: (hex, is a caught card), or None when all are fresh."""
    stale = (now or time.time()) - REFRESH_DAYS * 86400
    has = lambda t: conn.execute("SELECT 1 FROM sqlite_master WHERE name=?", (t,)).fetchone()
    civil = "hex NOT IN (SELECT hex FROM ref_aircraft WHERE substr(flags, 1, 1) = '1')"
    fresh = "hex NOT IN (SELECT hex FROM ref_owner WHERE fetched >= :stale)"
    r = conn.execute(f"SELECT hex FROM airframes WHERE military = 0 AND {fresh} ORDER BY card_no DESC LIMIT 1",
                     {"stale": stale}).fetchone()
    if r:
        return r[0], True
    if has("spotted_ops"):   # flies under several callsigns: the ones that need a source
        r = conn.execute(f"""SELECT hex FROM spotted_ops WHERE {civil} AND {fresh}
                             GROUP BY hex HAVING COUNT(*) > 1 LIMIT 1""", {"stale": stale}).fetchone()
        if r:
            return r[0], False
    src = [f"SELECT hex FROM {t}" for t in ("spotted_days", "airport_days") if has(t)]
    if not src:
        return None
    r = conn.execute(f"SELECT hex FROM ({' UNION '.join(src)}) WHERE {civil} AND {fresh} LIMIT 1",
                     {"stale": stale}).fetchone()
    return (r[0], False) if r else None


class OwnerFetcher(threading.Thread):
    """Background lookups. ``dirty`` is set when a caught card's owner changed,
    or after every ``batch`` lookups, so the collector recomputes home airlines."""

    def __init__(self, db_path: Path, log=print, batch: int = 200):
        super().__init__(daemon=True, name="owners")
        self.db_path, self.log, self.batch = db_path, log, batch
        self.dirty = threading.Event()
        self.stop = threading.Event()

    def run(self) -> None:
        from .db import connect
        conn = connect(self.db_path)
        conn.executescript(SCHEMA)
        done = 0
        while not self.stop.is_set():
            nxt = next_hex(conn)
            if nxt is None:
                if done:
                    self.log(f"owners: all airframes looked up ({done} this run)")
                    self.dirty.set()
                    done = 0
                self.stop.wait(3600)
                continue
            hx, caught = nxt
            try:
                rec = fetch(hx)
            except (OSError, ValueError) as e:
                self.log(f"owners: hexdb.io lookup failed ({e}); retrying in {BACKOFF_S // 60} min")
                self.stop.wait(BACKOFF_S)
                continue
            old = conn.execute("SELECT operator FROM ref_owner WHERE hex=?", (hx,)).fetchone()
            store(conn, hx, rec)
            done += 1
            new_op = conn.execute("SELECT operator FROM ref_owner WHERE hex=?", (hx,)).fetchone()[0]
            if (caught and (old is None or old[0] != new_op)) or done % self.batch == 0:
                self.dirty.set()
            self.stop.wait(INTERVAL_S)
