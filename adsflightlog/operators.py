"""Work out who operates an aircraft.

Normally the operator is the ICAO airline code at the start of the callsign
(KLM1234 -> KLM). Military and state aircraft often fly under mission
callsigns instead. OSY, for example, is used for Open Skies Treaty flights by
several air forces. So for aircraft flagged military in the aircraft database:

1. The country comes from the aircraft's ICAO 24-bit address block (tar1090
   ships the official allocation table).
2. A callsign operator is only accepted if it belongs to that same country
   and, where we know the country's main air arm, also looks military.
3. Otherwise the country's main military operator is used (DEFAULT_MIL), or
   none when we don't know one. The UI then shows "<country> military".
"""

from __future__ import annotations

import glob
import re
import sqlite3
from bisect import bisect_right
from pathlib import Path

AIRLINE_CALLSIGN = re.compile(r"^([A-Z]{3})\d")

# Callsign prefixes that describe a mission, not an operator.
MISSION_CALLSIGNS = {"OSY"}  # Open Skies Treaty observation flights

MILITARY_NAME = re.compile(
    r"air ?force|airforce|army|navy|naval|military|militar|luftwaffe|armed forces|"
    r"force a[eé]rienne|fuerza a[eé]rea|ej[eé]rcito|armada|marine nationale|marina militare|"
    r"coast ?guard|gendarmerie|air corps|air mobility command|priority air transport",
    re.I,
)

# Main military air operator per country (ICAO operator code).
DEFAULT_MIL = {
    "Germany": "GAF", "Netherlands": "NAF", "Belgium": "BAF", "France": "FAF",
    "United Kingdom": "RFR", "Italy": "IAM", "Spain": "AME", "Poland": "PLF",
    "Denmark": "DAF", "Norway": "NOW", "Sweden": "SVF", "Switzerland": "SUI",
    "Austria": "ASF", "Czech Republic": "CEF", "Canada": "CFC", "Portugal": "AFP",
    "Hungary": "HUF", "Finland": "FNF", "Turkey": "HVK", "Greece": "HAF",
    "Romania": "ROF", "Latvia": "LAF", "Ireland": "IRL",
}

# tar1090 country name -> operator database country name
COUNTRY_ALIASES = {"Czechia": "Czech Republic"}


def _load_ranges(tar1090_html: Path) -> list[tuple[int, int, str]]:
    files = glob.glob(str(tar1090_html / "flags_*.js")) + glob.glob(str(tar1090_html / "flags.js"))
    if not files:
        return []
    text = Path(files[0]).read_text(errors="replace")
    out = []
    for s, e, name in re.findall(
        r'start:\s*0x([0-9A-Fa-f]+),\s*end:\s*0x([0-9A-Fa-f]+),\s*country:\s*"([^"]+)"', text
    ):
        out.append((int(s, 16), int(e, 16), COUNTRY_ALIASES.get(name, name)))
    return sorted(out)


class OperatorResolver:
    def __init__(self, conn: sqlite3.Connection, tar1090_html: Path):
        self.ranges = _load_ranges(tar1090_html)
        self.starts = [r[0] for r in self.ranges]
        self.ops = {r[0]: (r[1] or "", r[2] or "") for r in
                    conn.execute("SELECT icao, name, country FROM ref_operators")}

    def country(self, hx: str) -> str | None:
        try:
            v = int(hx, 16)
        except ValueError:
            return None
        i = bisect_right(self.starts, v) - 1
        if i >= 0 and self.ranges[i][0] <= v <= self.ranges[i][1]:
            return self.ranges[i][2]
        return None

    def from_callsign(self, callsign: str | None) -> str | None:
        m = AIRLINE_CALLSIGN.match(callsign or "")
        if not m or m.group(1) in MISSION_CALLSIGNS or m.group(1) not in self.ops:
            return None
        return m.group(1)

    def resolve(self, hx: str, callsign: str | None, military: bool) -> str | None:
        op = self.from_callsign(callsign)
        if not military:
            return op
        country = self.country(hx)
        if op:
            name, op_country = self.ops[op]
            same_country = country is not None and op_country == country
            if same_country and (country not in DEFAULT_MIL or MILITARY_NAME.search(name)):
                return op
        return DEFAULT_MIL.get(country) if country else None


def fix_military(conn: sqlite3.Connection, resolver: OperatorResolver) -> int:
    """Re-resolve operators of military aircraft already stored (one-off, cheap)."""
    changed = 0
    with conn:
        for hx, op, cs in conn.execute(
            "SELECT hex, operator, last_callsign FROM airframes WHERE military = 1"
        ).fetchall():
            new = resolver.resolve(hx, cs, True)
            if new != op:
                conn.execute("UPDATE airframes SET operator=? WHERE hex=?", (new, hx))
                changed += 1
        rows = conn.execute(
            """SELECT o.hex, o.operator, o.first_seen, o.last_seen FROM spotted_ops o
               JOIN ref_aircraft r ON r.hex = o.hex WHERE substr(r.flags, 1, 1) = '1'"""
        ).fetchall() if conn.execute(
            "SELECT 1 FROM sqlite_master WHERE name='spotted_ops'").fetchone() else []
        for hx, op, first, last in rows:
            new = resolver.resolve(hx, op + "0", True)
            if new == op:
                continue
            conn.execute("DELETE FROM spotted_ops WHERE hex=? AND operator=?", (hx, op))
            if new:
                conn.execute(
                    """INSERT INTO spotted_ops VALUES (?,?,?,?) ON CONFLICT(hex, operator) DO UPDATE SET
                         first_seen = MIN(first_seen, excluded.first_seen),
                         last_seen = MAX(last_seen, excluded.last_seen)""",
                    (hx, new, first, last))
            changed += 1
    return changed
