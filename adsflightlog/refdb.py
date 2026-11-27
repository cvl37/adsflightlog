"""Import tar1090's offline aircraft database into SQLite.

tar1090-db ships gzip-compressed JSON shards named by hex prefix
(``4.js``, ``48.js``, ...). Keys inside a shard have the prefix stripped, and a
shard's ``children`` list names longer prefixes that live in their own file.
We flatten all of it into ``ref_aircraft`` once, so lookups are a single query.

Run manually with:  python3 -m adsflightlog.refdb
"""

from __future__ import annotations

import gzip
import json
import sqlite3
import sys
from pathlib import Path

from . import config as cfgmod
from .db import connect


def _load(path: Path):
    raw = path.read_bytes()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return json.loads(raw)


def _source_stamp(db_dir: Path) -> str:
    files = sorted(db_dir.glob("*.js"))
    return str(max((f.stat().st_mtime for f in files), default=0))


def needs_import(conn: sqlite3.Connection, db_dir: Path) -> bool:
    row = conn.execute("SELECT value FROM meta WHERE key='ref_stamp'").fetchone()
    return row is None or row[0] != _source_stamp(db_dir)


def import_refs(conn: sqlite3.Connection, db_dir: Path, log=print) -> None:
    if not db_dir.is_dir():
        log(f"refdb: {db_dir} not found, skipping enrichment import")
        return
    log(f"refdb: importing from {db_dir} ...")
    shard_names = _load(db_dir / "files.js")
    rows = []
    for prefix in shard_names:
        shard = _load(db_dir / f"{prefix}.js")
        for key, val in shard.items():
            if key == "children" or not isinstance(val, list):
                continue
            reg, typ, flags, model = (val + [None] * 4)[:4]
            rows.append(((prefix + key).lower(), reg or None, typ or None, flags or "", model or None))

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
        conn.execute("DELETE FROM ref_types")
        conn.executemany("INSERT OR REPLACE INTO ref_types VALUES (?,?,?,?)", types)
        conn.execute("DELETE FROM ref_operators")
        conn.executemany("INSERT OR REPLACE INTO ref_operators VALUES (?,?,?,?)", ops)
        conn.execute(
            "INSERT OR REPLACE INTO meta VALUES ('ref_stamp', ?)", (_source_stamp(db_dir),)
        )
    log(f"refdb: {len(rows)} aircraft, {len(types)} types, {len(ops)} operators")


def main() -> None:
    cfg = cfgmod.load(sys.argv[1] if len(sys.argv) > 1 else None)
    conn = connect(cfg.database)
    import_refs(conn, cfg.tar1090_db_dir)


if __name__ == "__main__":
    main()
