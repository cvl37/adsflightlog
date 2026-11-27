# ADS Flight Log

Collect the aircraft that fly over your ADS-B receiver as trading cards.

A collector polls `readsb`'s `aircraft.json`. Every aircraft that comes within
**your configured radius** becomes a card in your binder. A small web UI then
shows the collection with rarity tiers, foil cards, badges, a type dex, an
airline list and a live "in range now" view.

Only the Python standard library is used. It needs Python 3.11 or newer, plus
readsb (or dump1090-fa) for live data and tar1090 for the offline aircraft
database.

## Setup

```bash
cp config.example.toml config.toml   # then edit location + radius
./install.sh                         # installs and starts both systemd services
```

`install.sh` creates `config.toml` for you if it doesn't exist. It fills in the
receiver location from `/run/readsb/receiver.json`. `config.toml` is git-ignored,
so your location stays out of the repo.

To run without systemd:

```bash
python3 -m adsflightlog.collector config.toml
python3 -m adsflightlog.web config.toml      # http://<pi>:8642/
```

## What counts as a catch

All of these settings live in `config.toml`:

| Setting | Meaning |
|---|---|
| `receiver.lat` / `receiver.lon` | Where distances are measured from. If left out, it is read from readsb's `receiver.json`. |
| `collect.max_distance_km` | **Only aircraft inside this radius count.** Anything further away is ignored. |
| `collect.max_altitude_ft` | Optional ceiling (0 = off), e.g. to only collect low overflights. |
| `collect.max_position_age_s` | Stale positions are ignored. |
| `collect.sighting_gap_min` | A gap this long starts a new "sighting" of a known airframe. |

Changing the radius applies from then on. Cards you already collected stay in
your binder.

## Cards

- **One card per airframe** (ICAO hex), numbered in the order you caught them. Each card carries the series year of its first catch.
- **Rarity tiers**, from Common to Legendary:
  - Common: everyday narrow-bodies and regional aircraft.
  - Uncommon: wide-bodies, business jets and GA.
  - Rare: helicopters, older types, unidentified airframes.
  - Epic: military aircraft and four-engine jets.
  - Legendary: airframes flagged "interesting" in the database, and true oddballs (An-124, Beluga, ...).
  - Once you have 100+ cards, a type you've only caught once is bumped up one tier.
- **Badges**:
  - `1st edition`: your first airframe of that type.
  - `new`: caught in the last 24 h.
  - `low pass`: under 2 km away and below 3,000 ft.
  - `squawk …`: an emergency was seen.
  - `military`.
  - `regular`: 10+ sightings.
- **Points and collector level**: each card is worth points by rarity, and levels need progressively more points.
- **Card back** (click a card): full details and sighting history.

Card rules live in `adsflightlog/cards.py`.

## Data

The SQLite database is at `data/adsflightlog.db` (git-ignored). It has three kinds of tables:

- `airframes`: the cards.
- `sightings`: each visit inside the radius.
- `ref_*`: reference data imported from tar1090's Mictronics database. It is
  refreshed automatically when tar1090's database updates. To refresh it by
  hand, run `python3 -m adsflightlog.refdb`.
