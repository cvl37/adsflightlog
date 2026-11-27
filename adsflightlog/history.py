"""Schiphol traffic history from the OpenSky Network.

Imports, per local day, every aircraft that arrived at or departed from an
airport (default EHAM), with its callsign. The data feeds the rarity model's
"local regularity" alongside what your own receiver hears, so patterns don't
need weeks of listening first. It goes into its own table (``airport_days``);
the receiver's ``spotted_days`` is left alone.

Needs a free OpenSky account with an API client. Put its credentials in
config.toml:

    [opensky]
    client_id = "..."
    client_secret = "..."
    airport = "EHAM"
    history_days = 60

Each one-day query costs 30 API credits (4,000 per day), so 60 days of
arrivals and departures fit in one run. The import resumes where it left off.
Run it daily (cron) to keep the last days current:

    python3 -m adsflightlog.history [config.toml]
"""

from __future__ import annotations

import json
import sqlite3
import sys
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from . import config as cfgmod
from .db import connect
from .operators import OperatorResolver

TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
API = "https://opensky-network.org/api/flights/{kind}?airport={airport}&begin={begin}&end={end}"
MIN_CREDITS = 100

SCHEMA = """
CREATE TABLE IF NOT EXISTS airport_days (
    day      TEXT NOT NULL,     -- YYYY-MM-DD, local time
    hex      TEXT NOT NULL,
    operator TEXT,
    PRIMARY KEY (day, hex)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS airport_days_done (
    day         TEXT PRIMARY KEY,
    airport     TEXT NOT NULL,
    arrivals    INTEGER,
    departures  INTEGER,
    imported_at REAL
) WITHOUT ROWID;
"""


class OpenSky:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id, self.client_secret = client_id, client_secret
        self.token, self.token_exp = None, 0.0
        self.remaining: int | None = None

    def _auth(self) -> dict:
        if not self.token or time.time() > self.token_exp - 60:
            data = urllib.parse.urlencode({
                "grant_type": "client_credentials",
                "client_id": self.client_id, "client_secret": self.client_secret,
            }).encode()
            req = urllib.request.Request(TOKEN_URL, data=data,
                                         headers={"Content-Type": "application/x-www-form-urlencoded"})
            tok = json.load(urllib.request.urlopen(req, timeout=30))
            self.token, self.token_exp = tok["access_token"], time.time() + tok.get("expires_in", 1800)
        return {"Authorization": f"Bearer {self.token}", "User-Agent": "adsflightlog"}

    def flights(self, kind: str, airport: str, begin: int, end: int) -> list[dict]:
        url = API.format(kind=kind, airport=airport, begin=begin, end=end)
        for attempt in range(3):
            try:
                r = urllib.request.urlopen(urllib.request.Request(url, headers=self._auth()), timeout=120)
                rem = r.headers.get("X-Rate-Limit-Remaining")
                self.remaining = int(rem) if rem and rem.isdigit() else self.remaining
                return json.load(r)
            except urllib.error.HTTPError as e:
                rem = e.headers.get("X-Rate-Limit-Remaining")
                self.remaining = int(rem) if rem and rem.isdigit() else self.remaining
                if e.code == 404:          # no flights in that interval
                    return []
                if e.code == 429 or attempt == 2:
                    raise
                time.sleep(5 * (attempt + 1))
        return []


def _local_midnight(day: str) -> int:
    return int(time.mktime(time.strptime(day, "%Y-%m-%d")))


def import_history(conn: sqlite3.Connection, cfg: cfgmod.Config, osky: dict, log=print) -> int:
    conn.executescript(SCHEMA)
    airport = osky.get("airport", "EHAM").upper()
    n_days = int(osky.get("history_days", 60))
    api = OpenSky(osky["client_id"], osky["client_secret"])
    resolver = OperatorResolver(conn, cfg.tar1090_html)
    military = {h for (h,) in conn.execute("SELECT hex FROM ref_aircraft WHERE substr(flags,1,1)='1'")}

    done = {d for (d,) in conn.execute("SELECT day FROM airport_days_done WHERE airport=?", (airport,))}
    today = time.strftime("%Y-%m-%d")
    # Newest first, so the most relevant days land even if credits run out.
    days = [time.strftime("%Y-%m-%d", time.localtime(time.time() - i * 86400)) for i in range(1, n_days + 1)]
    todo = [d for d in days if d not in done and d != today]
    imported = 0
    for day in todo:
        if api.remaining is not None and api.remaining < MIN_CREDITS:
            log(f"history: stopping, only {api.remaining} API credits left today; will resume next run")
            break
        begin = _local_midnight(day)
        end = begin + 86400
        try:
            arr = api.flights("arrival", airport, begin, end)
            dep = api.flights("departure", airport, begin, end)
        except urllib.error.HTTPError as e:
            log(f"history: {day} failed (HTTP {e.code}); will retry next run")
            break
        rows = {}
        for f in arr + dep:
            hx = (f.get("icao24") or "").lower()
            if not hx:
                continue
            cs = (f.get("callsign") or "").strip() or None
            op = resolver.resolve(hx, cs, hx in military) if cs else None
            if op or hx not in rows:
                rows[hx] = op
        with conn:
            conn.executemany(
                """INSERT INTO airport_days VALUES (?,?,?)
                   ON CONFLICT(day, hex) DO UPDATE SET operator = COALESCE(excluded.operator, operator)""",
                [(day, hx, op) for hx, op in rows.items()])
            conn.execute("INSERT OR REPLACE INTO airport_days_done VALUES (?,?,?,?,?)",
                         (day, airport, len(arr), len(dep), time.time()))
            # Also confirms fleet membership (airframe flies for this airline).
            conn.executemany(
                """INSERT INTO spotted_ops VALUES (?,?,?,?)
                   ON CONFLICT(hex, operator) DO UPDATE SET
                     first_seen = MIN(first_seen, excluded.first_seen),
                     last_seen = MAX(last_seen, excluded.last_seen)""",
                [(hx, op, begin, begin + 43200) for hx, op in rows.items() if op])
        imported += 1
        log(f"history: {day}: {len(arr)} arrivals, {len(dep)} departures, {len(rows)} aircraft"
            f" (credits left: {api.remaining})")
        time.sleep(1)
    # Keep the window tidy.
    cutoff = time.strftime("%Y-%m-%d", time.localtime(time.time() - 120 * 86400))
    with conn:
        conn.execute("DELETE FROM airport_days WHERE day < ?", (cutoff,))
    return imported


def main() -> None:
    cfg_path = Path(sys.argv[1]) if len(sys.argv) > 1 else cfgmod.ROOT / "config.toml"
    cfg = cfgmod.load(cfg_path)
    osky = tomllib.loads(cfg_path.read_text()).get("opensky", {})
    if not osky.get("client_id") or not osky.get("client_secret"):
        sys.exit("history: set [opensky] client_id and client_secret in config.toml")
    conn = connect(cfg.database)
    from . import fleet
    conn.executescript(fleet.SCHEMA)
    n = import_history(conn, cfg, osky, log=lambda m: print(m, flush=True))
    print(f"history: imported {n} day(s)", flush=True)


if __name__ == "__main__":
    main()
