"""Reference data: registrations, types and operators.

Aircraft (hex -> registration/type) come from the tar1090-db / Mictronics
database. We prefer the upstream ``aircraft.csv.gz``, which we download and
refresh ourselves (``refresh_days``), because the copy bundled with a tar1090
install is only updated when tar1090 itself is reinstalled and goes stale.
If the download is unavailable we fall back to tar1090's local JSON shards.

Type and operator names always come from tar1090's local files (they rarely
change).

After every import, cards that were caught while their airframe was unknown
are filled in retroactively.

Run manually with:  python3 -m adsflightlog.refdb [config.toml] [--force]
"""

from __future__ import annotations

import gzip
import json
import os
import sqlite3
import sys
import time
import urllib.request
from pathlib import Path

from . import config as cfgmod
from .db import connect


def _load(path: Path):
    raw = path.read_bytes()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return json.loads(raw)


def download_csv(cfg: cfgmod.Config, force: bool = False, log=print) -> bool:
    """Fetch aircraft.csv.gz if missing or older than refresh_days. Returns True if updated."""
    dest = cfg.aircraft_csv
    if not cfg.aircraft_csv_url:
        return False
    if not force and dest.exists() and time.time() - dest.stat().st_mtime < cfg.ref_refresh_days * 86400:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    try:
        req = urllib.request.Request(cfg.aircraft_csv_url, headers={"User-Agent": "adsflightlog"})
        with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
            while chunk := r.read(1 << 16):
                f.write(chunk)
        # Sanity check: must be gzip with a plausible number of rows.
        with gzip.open(tmp, "rt", errors="replace") as f:
            n = sum(1 for _ in f)
        if n < 100_000:
            raise ValueError(f"only {n} rows")
        os.replace(tmp, dest)
        log(f"refdb: downloaded {cfg.aircraft_csv_url} ({n} aircraft)")
        return True
    except Exception as e:  # noqa: BLE001 — network trouble must not stop collecting
        tmp.unlink(missing_ok=True)
        if dest.exists():
            os.utime(dest)  # don't retry every poll; try again next period
        log(f"refdb: download failed ({e}); keeping existing data")
        return False


def _csv_rows(path: Path):
    # hex;reg;type;flags;description;...
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            p = line.rstrip("\n").split(";")
            if len(p) < 5 or not p[0]:
                continue
            yield (p[0].lower(), p[1] or None, p[2] or None, p[3] or "", p[4] or None)


def _shard_rows(db_dir: Path):
    for prefix in _load(db_dir / "files.js"):
        shard = _load(db_dir / f"{prefix}.js")
        for key, val in shard.items():
            if key == "children" or not isinstance(val, list):
                continue
            reg, typ, flags, model = (val + [None] * 4)[:4]
            yield ((prefix + key).lower(), reg or None, typ or None, flags or "", model or None)


def _sources(cfg: cfgmod.Config) -> list[Path]:
    out = []
    if cfg.aircraft_csv.exists():
        out.append(cfg.aircraft_csv)
    elif cfg.tar1090_db_dir.is_dir():
        out += sorted(cfg.tar1090_db_dir.glob("*.js"))
    return out


def _stamp(cfg: cfgmod.Config) -> str:
    src = _sources(cfg)
    return f"{src[0].parent if src else ''}:{max((f.stat().st_mtime for f in src), default=0)}"


def needs_import(conn: sqlite3.Connection, cfg: cfgmod.Config) -> bool:
    row = conn.execute("SELECT value FROM meta WHERE key='ref_stamp'").fetchone()
    return row is None or row[0] != _stamp(cfg)


def backfill(conn: sqlite3.Connection, log=print) -> int:
    """Fill in reg/type/model/flags on cards caught before their airframe was known."""
    with conn:
        cur = conn.execute(
            """UPDATE airframes SET
                   reg   = COALESCE(airframes.reg,   r.reg),
                   type  = COALESCE(airframes.type,  r.type),
                   model = COALESCE(airframes.model, r.model),
                   military    = MAX(military,    substr(r.flags,1,1)='1'),
                   interesting = MAX(interesting, substr(r.flags,2,1)='1')
               FROM ref_aircraft r
               WHERE r.hex = airframes.hex
                 AND ((airframes.reg IS NULL AND r.reg IS NOT NULL)
                   OR (airframes.type IS NULL AND r.type IS NOT NULL)
                   OR (airframes.model IS NULL AND r.model IS NOT NULL))"""
        )
    if cur.rowcount:
        log(f"refdb: filled in {cur.rowcount} previously unidentified card(s)")
    return cur.rowcount


def import_refs(conn: sqlite3.Connection, cfg: cfgmod.Config, log=print) -> None:
    db_dir = cfg.tar1090_db_dir
    if cfg.aircraft_csv.exists():
        log(f"refdb: importing aircraft from {cfg.aircraft_csv} ...")
        rows = list(_csv_rows(cfg.aircraft_csv))
    elif db_dir.is_dir():
        log(f"refdb: importing aircraft from {db_dir} ...")
        rows = list(_shard_rows(db_dir))
    else:
        log("refdb: no aircraft database found, skipping enrichment import")
        return

    types = []
    tpath = db_dir / "icao_aircraft_types2.js"
    if tpath.exists():
        for code, (name, desc, wtc) in _load(tpath).items():
            types.append((code, name, desc, wtc))

    ops = []
    opath = db_dir / "operators.js"
    if opath.exists():
        for code, o in _load(opath).items():
            ops.append((code, o.get("n"), o.get("c"), o.get("r")))

    with conn:
        conn.execute("DELETE FROM ref_aircraft")
        conn.executemany("INSERT OR REPLACE INTO ref_aircraft VALUES (?,?,?,?,?)", rows)
        if types:
            conn.execute("DELETE FROM ref_types")
            conn.executemany("INSERT OR REPLACE INTO ref_types VALUES (?,?,?,?)", types)
        if ops:
            conn.execute("DELETE FROM ref_operators")
            conn.executemany("INSERT OR REPLACE INTO ref_operators VALUES (?,?,?,?)", ops)
        conn.execute("INSERT OR REPLACE INTO meta VALUES ('ref_stamp', ?)", (_stamp(cfg),))
    log(f"refdb: {len(rows)} aircraft, {len(types)} types, {len(ops)} operators")
    backfill(conn, log)


def update(conn: sqlite3.Connection, cfg: cfgmod.Config, force: bool = False, log=print) -> None:
    """Download if due, then (re)import if the source changed."""
    download_csv(cfg, force=force, log=log)
    if force or needs_import(conn, cfg):
        import_refs(conn, cfg, log)


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    cfg = cfgmod.load(args[0] if args else None)
    conn = connect(cfg.database)
    update(conn, cfg, force="--force" in sys.argv)


if __name__ == "__main__":
    main()
