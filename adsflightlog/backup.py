"""Daily backup of your collection to any rclone remote (e.g. Google Drive).

What goes in the archive (``adsflightlog-YYYY-MM-DD.tar.gz``):
  * ``adsflightlog.db``: a consistent snapshot of the database, taken with
    SQLite's online backup API, so it is safe while the collector runs.
    Reference tables (``ref_*``) are dropped because they are re-imported
    automatically on start.
  * ``config.toml``: your local settings (location, zones).

Configure it in config.toml:

    [backup]
    remote = "myremote:"            # rclone remote (with optional path)
    root_folder_id = ""             # Google Drive only: target folder ID (optional)
    keep_days = 30

Restore: stop the services, extract the archive, put adsflightlog.db in data/
and config.toml in the repo root, then start the services again.

Run with:  python3 -m adsflightlog.backup [config.toml]
"""

from __future__ import annotations

import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import time
import tomllib
from pathlib import Path

from . import config as cfgmod

# cron has a minimal PATH; rclone is often installed per user.
RCLONE = shutil.which("rclone") or str(Path.home() / ".local/bin/rclone")


def snapshot(db_path: Path, out: Path) -> None:
    src = sqlite3.connect(db_path, timeout=60)
    dst = sqlite3.connect(out)
    with dst:
        src.backup(dst)
    src.close()
    refs = [r[0] for r in dst.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'ref\\_%' ESCAPE '\\'")]
    for t in refs:
        dst.execute(f'DROP TABLE "{t}"')
    # Force a fresh reference import after a restore.
    dst.execute("DELETE FROM meta WHERE key IN ('ref_stamp', 'opensky_key', 'opensky_checked')")
    dst.commit()
    dst.execute("VACUUM")
    dst.close()


def main() -> None:
    cfg_path = Path(sys.argv[1]) if len(sys.argv) > 1 else cfgmod.ROOT / "config.toml"
    cfg = cfgmod.load(cfg_path)
    b = tomllib.loads(cfg_path.read_text()).get("backup", {})
    remote = b.get("remote")
    if not remote:
        sys.exit("backup: set [backup] remote in config.toml")
    keep_days = int(b.get("keep_days", 30))
    flags = ["--drive-root-folder-id", b["root_folder_id"]] if b.get("root_folder_id") else []

    stamp = time.strftime("%Y-%m-%d")
    with tempfile.TemporaryDirectory(prefix="adsflightlog-backup-") as tmp:
        tmp = Path(tmp)
        db = tmp / "adsflightlog.db"
        snapshot(cfg.database, db)
        archive = tmp / f"adsflightlog-{stamp}.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(db, arcname="adsflightlog.db")
            tar.add(cfg_path, arcname="config.toml")
        size = archive.stat().st_size
        subprocess.run([RCLONE, "copyto", str(archive), f"{remote}{archive.name}", *flags], check=True)
        print(f"backup: uploaded {archive.name} ({size / 1e6:.1f} MB) to {remote}", flush=True)

    # Retention: remove our own archives older than keep_days.
    subprocess.run([RCLONE, "delete", remote, "--min-age", f"{keep_days}d",
                    "--include", "adsflightlog-*.tar.gz", *flags], check=True)
    print(f"backup: pruned archives older than {keep_days} days", flush=True)


if __name__ == "__main__":
    main()
