"""Helicopter operators from helispot.nl (https://www.helispot.nl/helicopters).

hexdb.io and OpenSky know airline fleets well but helicopters poorly: the ANWB
air ambulance PH-HLP is missing from both. Helispot keeps a hand-maintained
database of (mostly Benelux) helicopters with the operator that actually
flies each one ("ANWB Medical Air Assistance BV, Lelystad", "Luchtvaartpolitie
NL", "Bristow Helicopters").

There is no API, and the search page only works in a browser, but every model
page (/helicopters/<id>, ~140 of them) lists its airframes with registration,
operator and status. A full crawl is ~140 requests; we space them out and
re-crawl monthly (cron: ``python3 -m adsflightlog.helispot``). There is no
Mode-S address on helispot, so home.py matches on registration.
"""

from __future__ import annotations

import argparse
import html
import re
import sqlite3
import sys
import time
import urllib.request

BASE = "https://www.helispot.nl"
# Plain urllib requests get a 403 from some CDNs; send an ordinary browser UA.
UA = "Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
DELAY_S = 2.0

SCHEMA = """
CREATE TABLE IF NOT EXISTS ref_heli (
    reg_norm  TEXT PRIMARY KEY,   -- registration, upper case, no dash (PHHLP)
    reg       TEXT NOT NULL,
    operator  TEXT,               -- operator name, cleaned (see clean_operator)
    raw       TEXT,               -- operator text as helispot shows it
    cancelled INTEGER NOT NULL,   -- struck off the register ("doorgehaald")
    crashed   INTEGER NOT NULL,
    page      TEXT,               -- /helicopter/<id>
    fetched   REAL NOT NULL
) WITHOUT ROWID;
"""

CARD = re.compile(r'<article class="post heli-card([^"]*)">(.*?)</article>', re.S)


def norm_reg(reg: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", reg.upper())


def clean_operator(raw: str | None) -> str | None:
    """Operator name from helispot's free text.

    'ANWB Medical Air Assistance BV, Lelystad (voor RAV)' -> 'ANWB Medical Air Assistance BV'
    'Heli & Co, Liege (B) - owner TECAIR Arcangues (FR)'   -> 'Heli & Co'
    'Heliair, eigenaar Top Motion Works, Odijk (NL)'      -> 'Heliair'
    'Heli Luxembourg (owner: Tradlux SA)'                 -> 'Heli Luxembourg'
    'Helihansa (AU) - Startrade (D)'                      -> 'Helihansa'
    """
    s = html.unescape(raw or "").strip()
    s = re.split(r"\s*[-,(]?\s*\b(?:owner|eigenaar|eigendom)\b", s, maxsplit=1, flags=re.I)[0]
    s = s.split(" - ")[0]                 # 'operator - other party': the first named flies it
    s = re.sub(r"\([^)]*\)?", "", s)      # (voor RAV), (D), unclosed '(owner'
    s = s.split(",")[0]                   # ', Lelystad'
    s = re.sub(r"\s+", " ", s).strip(" -,.")
    return s or None


def parse_model_page(page: str) -> list[dict]:
    out = []
    for cls, body in CARD.findall(page):
        a = re.search(r'<a href="(/helicopter/[A-Za-z0-9]+)">([^<]*)</a>', body)
        if not a:
            continue
        op = re.search(r'<p class="heli-operator">(.*?)</p>', body, re.S)
        raw = html.unescape(re.sub(r"<[^>]+>", "", op.group(1))).strip() if op else None
        out.append({
            "reg": html.unescape(a.group(2)).strip(), "page": a.group(1),
            "raw": raw or None, "operator": clean_operator(raw),
            "cancelled": "is-unsubscribed" in cls or "cancelled" in body,
            "crashed": "crash" in cls or "crash" in body.lower(),
        })
    return out


def _get(path: str, timeout: float = 30) -> str:
    req = urllib.request.Request(BASE + path, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def crawl(delay: float = DELAY_S, log=print) -> list[dict]:
    models = sorted(set(re.findall(r'href="(/helicopters/[A-Za-z0-9]{6})"', _get("/helicopters"))))
    rows = []
    for i, m in enumerate(models):
        time.sleep(delay)
        try:
            rows += parse_model_page(_get(m))
        except OSError as e:
            log(f"{m}: {e}")
        if (i + 1) % 25 == 0:
            log(f"{i + 1}/{len(models)} model pages, {len(rows)} helicopters")
    if not models or not rows:
        raise RuntimeError("helispot layout changed? no helicopters found")
    return rows


def store(conn: sqlite3.Connection, rows: list[dict], now: float | None = None) -> int:
    """Replace the table. A registration on several pages: the current (not struck off) one wins."""
    now = now or time.time()
    best: dict[str, dict] = {}
    for r in rows:
        k = norm_reg(r["reg"])
        if not k:
            continue
        if k not in best or (best[k]["cancelled"] and not r["cancelled"]):
            best[k] = r
    with conn:
        conn.executescript(SCHEMA)
        conn.execute("DELETE FROM ref_heli")
        conn.executemany(
            "INSERT INTO ref_heli VALUES (?,?,?,?,?,?,?,?)",
            [(k, r["reg"], r["operator"], r["raw"], int(r["cancelled"]), int(r["crashed"]), r["page"], now)
             for k, r in best.items()])
    return len(best)


def operators(conn: sqlite3.Connection) -> dict[str, str]:
    """{hex: operator name} for airframes whose current registration helispot lists as active."""
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='ref_heli'").fetchone():
        return {}
    norm = "replace(replace(upper({}), '-', ''), ' ', '')"
    q = f"""SELECT x.hex, h.operator FROM
              (SELECT hex, reg FROM ref_aircraft WHERE reg IS NOT NULL
               UNION SELECT hex, reg FROM airframes WHERE reg IS NOT NULL) x
            JOIN ref_heli h ON h.reg_norm = {norm.format('x.reg')}
            WHERE h.cancelled = 0 AND h.operator IS NOT NULL"""
    return dict(conn.execute(q).fetchall())


def main(argv: list[str] | None = None) -> None:
    from . import config as cfgmod
    from . import home
    from .db import connect
    from .operators import OperatorResolver

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--delay", type=float, default=DELAY_S)
    args = ap.parse_args(argv)
    cfg = cfgmod.load(cfgmod.ROOT / "config.toml")
    rows = crawl(args.delay, log=lambda m: print(m, file=sys.stderr))
    conn = connect(cfg.database)
    n = store(conn, rows)
    changed = home.compute(conn, OperatorResolver(conn, cfg.tar1090_html))
    print(f"{n} helicopters stored, {len(operators(conn))} matched to known airframes, "
          f"{changed} card operators changed")


if __name__ == "__main__":
    main()
