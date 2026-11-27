"""Configuration loading."""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV_URL = "https://github.com/wiedehopf/tar1090-db/raw/refs/heads/csv/aircraft.csv.gz"


@dataclass
class Zone:
    """An area around the receiver where an aircraft counts as a catch.

    A circle (``max_distance_km``), optionally narrowed to a sector between two
    true bearings measured clockwise from ``bearing_from`` to ``bearing_to``
    (e.g. 270 -> 360 is the north-west quarter), and optionally limited to
    aircraft below ``max_altitude_ft``.
    """

    name: str
    max_distance_km: float
    bearing_from: float | None = None
    bearing_to: float | None = None
    max_altitude_ft: int | None = None

    def describe(self) -> str:
        s = f"{self.max_distance_km:g} km"
        if self.bearing_from is not None and self.bearing_to is not None:
            s += f" between {self.bearing_from:03.0f}° and {self.bearing_to:03.0f}°"
        if self.max_altitude_ft:
            s += f" below {self.max_altitude_ft:,} ft"
        return s


@dataclass
class Config:
    lat: float
    lon: float
    aircraft_json: Path
    zones: list[Zone]
    max_position_age_s: float
    poll_interval_s: float
    sighting_gap_s: float
    database: Path
    tar1090_db_dir: Path
    aircraft_csv_url: str
    aircraft_csv: Path
    ref_refresh_days: float
    web_host: str
    web_port: int
    track_before_s: float | None = 1800
    track_after_s: float | None = 1800
    rarity_weights: dict | None = None
    rarity_learn_days: float = 28
    editions_stable_days: float = 7
    editions_check_days: float = 7

    @property
    def tar1090_html(self) -> Path:
        """tar1090's web root (has the ICAO address -> country table)."""
        return self.tar1090_db_dir.parents[1] / "html"


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

    def _path(v: str) -> Path:
        p = Path(v)
        return p if p.is_absolute() else ROOT / p

    db = _path(sto.get("database", "data/adsflightlog.db"))

    return Config(
        lat=float(lat),
        lon=float(lon),
        aircraft_json=Path(rcv.get("aircraft_json", "/run/readsb/aircraft.json")),
        zones=_zones(col),
        max_position_age_s=float(col.get("max_position_age_s", 15)),
        poll_interval_s=float(col.get("poll_interval_s", 5)),
        sighting_gap_s=float(col.get("sighting_gap_min", 20)) * 60,
        database=db,
        tar1090_db_dir=Path(sto.get("tar1090_db_dir", "/usr/local/share/tar1090/git-db/db")),
        aircraft_csv_url=str(sto.get("aircraft_csv_url", DEFAULT_CSV_URL)),
        aircraft_csv=_path(sto.get("aircraft_csv", "data/aircraft.csv.gz")),
        ref_refresh_days=float(sto.get("refresh_days", 7)),
        track_before_s=_minutes(raw.get("tracks", {}).get("before_min", 30)),
        track_after_s=_minutes(raw.get("tracks", {}).get("after_min", 30)),
        rarity_weights={k: float(v) for k, v in raw.get("rarity", {}).get("weights", {}).items()} or None,
        rarity_learn_days=float(raw.get("rarity", {}).get("learn_days", 28)),
        editions_stable_days=float(raw.get("editions", {}).get("stable_days", 7)),
        editions_check_days=float(raw.get("editions", {}).get("check_days", 7)),
        web_host=str(web.get("host", "0.0.0.0")),
        web_port=int(web.get("port", 8642)),
    )


def _zones(col: dict) -> list[Zone]:
    zones = []
    for i, z in enumerate(col.get("zone", [])):
        bf, bt = z.get("bearing_from"), z.get("bearing_to")
        if (bf is None) != (bt is None):
            raise ValueError(f"zone {i}: set both bearing_from and bearing_to, or neither")
        zones.append(Zone(
            name=str(z.get("name", f"zone {i + 1}")),
            max_distance_km=float(z["max_distance_km"]),
            bearing_from=float(bf) % 360 if bf is not None else None,
            bearing_to=(float(bt) if float(bt) == 360 else float(bt) % 360) if bt is not None else None,
            max_altitude_ft=int(z["max_altitude_ft"]) if z.get("max_altitude_ft") else None,
        ))
    if not zones:
        # Older single-circle config.
        zones.append(Zone(
            name="radius",
            max_distance_km=float(col.get("max_distance_km", 25.0)),
            max_altitude_ft=int(col.get("max_altitude_ft", 0)) or None,
        ))
    return zones


def _minutes(v) -> float | None:
    """Minutes -> seconds; "all" means everything the receiver saw."""
    if isinstance(v, str) and v.strip().lower() == "all":
        return None
    return float(v) * 60
