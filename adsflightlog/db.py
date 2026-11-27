"""SQLite schema and connection helper."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

-- Reference data, imported from tar1090's offline database (see refdb.py).
CREATE TABLE IF NOT EXISTS ref_aircraft (
    hex   TEXT PRIMARY KEY,      -- lower-case ICAO 24-bit address
    reg   TEXT,
    type  TEXT,                  -- ICAO type designator, e.g. A20N
    flags TEXT,                  -- tar1090 flags: [military, interesting, PIA, LADD]
    model TEXT                   -- long description, e.g. "AIRBUS A-320neo"
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS ref_types (
    type TEXT PRIMARY KEY,
    name TEXT,
    desc TEXT,                   -- ICAO class, e.g. L2J = landplane, 2 engines, jet
    wtc  TEXT                    -- wake turbulence category L/M/H/J
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS ref_operators (
    icao     TEXT PRIMARY KEY,   -- 3-letter ICAO airline designator
    name     TEXT,
    country  TEXT,
    callsign TEXT                -- radiotelephony callsign
) WITHOUT ROWID;

-- The collection: one row ("card") per airframe ever caught within range.
CREATE TABLE IF NOT EXISTS airframes (
    hex            TEXT PRIMARY KEY,
    card_no        INTEGER UNIQUE NOT NULL,
    reg            TEXT,
    type           TEXT,
    model          TEXT,
    military       INTEGER NOT NULL DEFAULT 0,
    interesting    INTEGER NOT NULL DEFAULT 0,
    category       TEXT,          -- ADS-B emitter category (A1..C7)
    operator       TEXT,          -- ICAO airline code from the callsign (last seen)
    last_callsign  TEXT,
    first_seen     REAL NOT NULL,
    last_seen      REAL NOT NULL,
    sightings      INTEGER NOT NULL DEFAULT 1,
    closest_km     REAL,
    closest_alt_ft INTEGER,
    max_alt_ft     INTEGER,
    max_gs_kt      REAL,
    emergency      TEXT           -- non-'none' emergency status ever seen
);

-- Each separate visit of an airframe inside the radius.
CREATE TABLE IF NOT EXISTS sightings (
    id          INTEGER PRIMARY KEY,
    hex         TEXT NOT NULL REFERENCES airframes(hex),
    callsign    TEXT,
    start       REAL NOT NULL,
    end         REAL NOT NULL,
    min_dist_km REAL,
    min_alt_ft  INTEGER,
    max_alt_ft  INTEGER,
    max_gs_kt   REAL,
    closest_lat REAL,
    closest_lon REAL
);
CREATE INDEX IF NOT EXISTS sightings_hex ON sightings(hex, end);
CREATE INDEX IF NOT EXISTS sightings_start ON sightings(start);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.executescript(SCHEMA)
    return conn
