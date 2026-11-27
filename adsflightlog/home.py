"""Which airline an airframe belongs to (its "home" operator).

An airframe is often heard under more than one airline's callsign: a regional
jet flies the main brand's flight numbers (KLM Cityhopper as KLM), and
wet-leased or chartered aircraft fly for another airline for weeks (a HOP E190
flying KLM flights). The card and the binder should count it once, for the
airline it belongs to, not for every airline whose flight number it carried.

For each civil airframe, in this order:

1. The registered operator from hexdb.io (owners.py), if its registration
   still matches: YR-ABA -> Carpatair, F-HBLJ -> HOP. When hexdb.io names
   the owner but gives no airline code (PH-PXX -> "KLPD Police Aviation
   Service"), the owner name is matched to an airline from the same country;
   if none matches, the owner is not an airline and the airframe gets no home
   airline (reason ``registered to <owner>``), even if it flies another
   operator's callsign now and then (police helicopters on Kustwacht flights);
   such flights are incidental, so no ``flying_for`` is recorded either.
   Lessors and "Private" don't count as owners here.
2. The OpenSky operator, likewise (older data, fewer airframes), if that
   airline was heard flying at all in the window (OpenSky still lists defunct ones).

Only when neither source knows the airframe, we guess from the airlines it was
heard flying for (receiver and airport history, last ``WINDOW_DAYS``):

a. Same country first. The ICAO 24-bit address gives the state of registry,
   and aircraft are almost always registered where their operator is based
   (F-HBLJ is French, so it's HOP's, not KLM's).
b. Among same-country airlines, the one with the smaller fleet wins. When two
   airlines share an aircraft, the smaller one is usually operating it for the
   bigger brand (KLM Cityhopper for KLM, Transavia for KLM), not the reverse.
c. No same-country airline: the one airline it was heard for (foreign-registered fleets are common: Malta Air for Ryanair).
d. Heard for several airlines, none from its country: a
   wet-lease (D-AMWO flying for KLM and KLM Cityhopper). It gets no home
   airline and counts for nobody's fleet; ``flying_for`` records who it flies for.

Airlines heard on fewer than ``MIN_SHARE`` of the airframe's days are ignored
in step c/d (a one-off positioning or rescue flight), unless nothing else is left.

Military aircraft keep the operator from operators.py (it already uses the
country of registry). ``home_overrides`` holds manual corrections, which win.
"""

from __future__ import annotations

import re
import sqlite3
import time

from .operators import OperatorResolver

WINDOW_DAYS = 180
MIN_SHARE = 0.10
REGISTERED_TO = "registered to "
# Registered owners that say nothing about who flies the aircraft.
NOT_AN_OPERATOR = re.compile(r"^private$|leas|lessor|capital|financ|bank|trust|investment|holding", re.I)


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


def match_owner(name: str, country: str | None, op_names: dict[str, tuple[str, str]]) -> str | None:
    """Airline code whose name matches a registered owner name, same country only."""
    n = _norm(name)
    if not n or not country:
        return None
    hits = [o for o, (on, oc) in op_names.items()
            if oc == country and on and (_norm(on) == n or f" {_norm(on)} " in f" {n} ")]
    return min(hits) if len(hits) == 1 else None

SCHEMA = """
CREATE TABLE IF NOT EXISTS airframe_home (
    hex      TEXT PRIMARY KEY,
    operator   TEXT,              -- NULL: wet-lease, no home airline known
    flying_for TEXT,              -- airline it was heard flying for most
    reason     TEXT,
    updated    REAL NOT NULL
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS airframe_home_op ON airframe_home(operator);

CREATE TABLE IF NOT EXISTS home_overrides (
    hex      TEXT PRIMARY KEY,
    operator TEXT NOT NULL
) WITHOUT ROWID;
"""


def _table(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE name=?", (name,)).fetchone() is not None


def pick(hx: str, heard: dict[str, int], ref_op: str | None, fleet_size: dict[str, int],
         op_country: dict[str, str], reg_country: str | None,
         owner: tuple[str, str | None] | None = None) -> tuple[str | None, str]:
    """Choose the home operator. ``heard`` is {operator: days heard flying for it};
    ``owner`` is (operator code, owner name) from hexdb.io; ``ref_op`` from OpenSky."""
    if owner and owner[0] in op_country:
        return owner[0], f"hexdb.io: {owner[1] or owner[0]}"
    if owner and not owner[0] and owner[1] and not NOT_AN_OPERATOR.search(owner[1]):
        return None, REGISTERED_TO + owner[1]
    # OpenSky's export is old: only trust airlines still flying (not Air Berlin).
    if ref_op and ref_op in op_country and fleet_size.get(ref_op, 0) > 0:
        return ref_op, "OpenSky operator"
    total = sum(heard.values())
    main = {o: n for o, n in heard.items() if total and n / total >= MIN_SHARE} or dict(heard)
    smaller = lambda ops: min(ops, key=lambda o: (fleet_size.get(o, 0), -heard.get(o, 0), o))

    if reg_country:
        cands = set(heard)
        same = [o for o in cands if op_country.get(o) == reg_country]
        if len(same) == 1:
            return same[0], f"only airline from {reg_country}"
        if same:
            return smaller(same), f"smaller of {', '.join(sorted(same))} ({reg_country})"
    if not main:
        return None, ""
    if len(main) == 1:
        return next(iter(main)), "only airline heard"
    return None, f"wet-lease, flies for {', '.join(sorted(main))}"


def compute(conn: sqlite3.Connection, resolver: OperatorResolver, now: float | None = None) -> int:
    """Recompute airframe_home and the airframes.operator of caught civil aircraft.

    Returns the number of airframes whose card operator changed.
    """
    now = now or time.time()
    conn.executescript(SCHEMA)
    since_day = time.strftime("%Y-%m-%d", time.localtime(now - WINDOW_DAYS * 86400))
    src = ["SELECT day, hex, operator FROM spotted_days"] if _table(conn, "spotted_days") else []
    if _table(conn, "airport_days"):
        src.append("SELECT day, hex, operator FROM airport_days")
    heard: dict[str, dict[str, int]] = {}
    if src:
        q = (f"SELECT hex, operator, COUNT(DISTINCT day) FROM ({' UNION ALL '.join(src)}) "
             "WHERE operator IS NOT NULL AND day >= ? GROUP BY hex, operator")
        for hx, op, n in conn.execute(q, (since_day,)):
            heard.setdefault(hx, {})[op] = n
    # Caught airframes heard before day logging existed.
    for hx, op in conn.execute("SELECT hex, operator FROM airframes WHERE operator IS NOT NULL"):
        heard.setdefault(hx, {}).setdefault(op, 1)

    fleet_size: dict[str, int] = {}
    for ops in heard.values():
        for o in ops:
            fleet_size[o] = fleet_size.get(o, 0) + 1

    ref = {}
    if _table(conn, "ref_fleet"):
        # Skip OpenSky entries for airframes re-registered since the export (sold).
        ref = dict(conn.execute(
            """SELECT f.hex, f.operator FROM ref_fleet f LEFT JOIN ref_aircraft r ON r.hex = f.hex
               WHERE r.reg IS NULL OR f.reg IS NULL
                  OR replace(upper(r.reg), '-', '') = replace(upper(f.reg), '-', '')"""))
    norm = "replace(upper({}), '-', '')"
    owners = {}
    if _table(conn, "ref_owner"):
        # Skip answers for a previous registration (sold since the lookup).
        owners = {h: (o, n) for h, o, n in conn.execute(
            f"""SELECT w.hex, w.operator, w.owner FROM ref_owner w LEFT JOIN ref_aircraft r ON r.hex = w.hex
                WHERE (w.operator IS NOT NULL OR w.owner IS NOT NULL)
                  AND (r.reg IS NULL OR w.reg IS NULL OR {norm.format('r.reg')} = {norm.format('w.reg')})""")}
    military = {h for (h,) in conn.execute(
        "SELECT hex FROM ref_aircraft WHERE substr(flags, 1, 1) = '1' "
        "UNION SELECT hex FROM airframes WHERE military = 1")}
    caught = {h for (h,) in conn.execute("SELECT hex FROM airframes")}
    overrides = dict(conn.execute("SELECT hex, operator FROM home_overrides"))
    op_country = {o: c for o, (_, c) in resolver.ops.items()}
    for hx, (code, name) in list(owners.items()):
        if not code and name:   # owner named, no airline code: is it an airline we know?
            m = match_owner(name, resolver.country(hx), resolver.ops)
            if m:
                owners[hx] = (m, name)

    rows = []
    for hx in set(heard) | set(overrides) | (set(owners) & caught):
        h = heard.get(hx, {})
        top = max(h, key=lambda o: (h[o], o)) if h else None
        if hx in overrides:
            rows.append((hx, overrides[hx], top, "set by you", now))
            continue
        if hx in military:
            continue
        op, why = pick(hx, h, ref.get(hx), fleet_size, op_country, resolver.country(hx), owners.get(hx))
        if why.startswith(REGISTERED_TO):
            top = None   # not an airline's aircraft: an odd flight under one's callsign is incidental
        if op or why:
            rows.append((hx, op, top, why, now))

    changed = 0
    with conn:
        conn.execute("DELETE FROM airframe_home")
        conn.executemany("INSERT INTO airframe_home VALUES (?,?,?,?,?)", rows)
        changed = conn.execute(
            """UPDATE airframes SET operator = (SELECT operator FROM airframe_home h WHERE h.hex = airframes.hex)
               WHERE hex IN (SELECT hex FROM airframe_home)
                 AND operator IS NOT (SELECT operator FROM airframe_home h WHERE h.hex = airframes.hex)"""
        ).rowcount
    return changed


def lookup(conn: sqlite3.Connection, hx: str) -> tuple[bool, str | None]:
    """(known, home operator). Unknown airframes keep their callsign operator."""
    if not _table(conn, "airframe_home"):
        return False, None
    r = conn.execute("SELECT operator FROM airframe_home WHERE hex=?", (hx,)).fetchone()
    return (True, r[0]) if r else (False, None)
