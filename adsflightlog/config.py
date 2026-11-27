"""Configuration loading."""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Config:
    lat: float
    lon: float
    aircraft_json: Path
    max_distance_km: float
    max_altitude_ft: int
    max_position_age_s: float
    poll_interval_s: float
    sighting_gap_s: float
    database: Path
    tar1090_db_dir: Path
    web_host: str
    web_port: int


def load(path: str | Path | None = None) -> Config:
    path = Path(path) if path else ROOT / "config.toml"
    if not path.exists():
        path = ROOT / "config.example.toml"
    raw = tomllib.loads(path.read_text())

    rcv = raw.get("receiver", {})
    col = raw.get("collect", {})
    sto = raw.get("storage", {})
    web = raw.get("web", {})

    lat, lon = rcv.get("lat"), rcv.get("lon")
    if lat is None or lon is None:
        rj = json.loads(Path(rcv.get("receiver_json", "/run/readsb/receiver.json")).read_text())
        lat, lon = rj["lat"], rj["lon"]

    db = Path(sto.get("database", "data/adsflightlog.db"))
    if not db.is_absolute():
        db = ROOT / db

    return Config(
        lat=float(lat),
        lon=float(lon),
        aircraft_json=Path(rcv.get("aircraft_json", "/run/readsb/aircraft.json")),
        max_distance_km=float(col.get("max_distance_km", 25.0)),
        max_altitude_ft=int(col.get("max_altitude_ft", 0)),
        max_position_age_s=float(col.get("max_position_age_s", 15)),
        poll_interval_s=float(col.get("poll_interval_s", 5)),
        sighting_gap_s=float(col.get("sighting_gap_min", 20)) * 60,
        database=db,
        tar1090_db_dir=Path(sto.get("tar1090_db_dir", "/usr/local/share/tar1090/git-db/db")),
        web_host=str(web.get("host", "0.0.0.0")),
        web_port=int(web.get("port", 8642)),
    )
