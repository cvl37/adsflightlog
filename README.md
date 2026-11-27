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

All of these settings live in `config.toml`. You define one or more **catch zones**. An aircraft counts as a catch if it is inside *any* zone. If it is inside several zones at once, it still counts once, and all zones count equally.

```toml
# Everything within 25 km, any altitude
[[collect.zone]]
name = "overhead"
max_distance_km = 25.0

# A "pizza slice": 40 km, from south-east (135°) clockwise to south-west (225°), below 10,000 ft
[[collect.zone]]
name = "southern approach"
max_distance_km = 40.0
bearing_from = 135
bearing_to = 225
max_altitude_ft = 10000
```

| Setting | Meaning |
|---|---|
| `receiver.lat` / `receiver.lon` | Where distances and bearings are measured from. If left out, it is read from readsb's `receiver.json`. |
| `zone.max_distance_km` | Radius of the zone. |
| `zone.bearing_from` / `bearing_to` | Optional sector, in true degrees, measured clockwise from `bearing_from` to `bearing_to`. For example, `330` → `30` is a slice across north. |
| `zone.max_altitude_ft` | Optional ceiling. An aircraft counts only if it is strictly below this altitude. If its altitude is unknown, it doesn't count in this zone. |
| `collect.max_position_age_s` | Stale positions are ignored. |
| `collect.sighting_gap_min` | A gap this long starts a new "sighting" of a known airframe. |

Changes to the zones apply from then on. Cards you already collected stay in your binder.

Run the zone geometry tests with `python3 -m unittest discover -s tests -t .`.

## Operators

A card's operator normally comes from the callsign's ICAO airline prefix (`KLM1234` → KLM). Military and state aircraft often fly under mission callsigns instead (for example `OSY` for Open Skies Treaty flights), so for aircraft flagged military:

1. The country is looked up from the aircraft's 24-bit address block, using tar1090's ICAO allocation table.
2. A callsign operator is only accepted if it is that same country's military, so a German Army callsign on a German airframe stays "German Army".
3. Otherwise the country's main air arm is used (`DEFAULT_MIL` in `adsflightlog/operators.py`). If none is known, the card shows "\<country\> military".

Mission callsigns (`MISSION_CALLSIGNS`) are never used as an operator, for any aircraft.

## Binder pages: fleets, manufacturers and types

Besides the **All cards** view, the binder has pages per **airline/operator**, **manufacturer** and **aircraft type**. You only get pages you hold at least one card for. Each page shows your cards plus an **empty sleeve** for every airframe you could still catch, with a progress bar.

Where the empty sleeves come from:

- **Spotting log (your receiver).** Every aircraft the receiver hears is logged, at any distance and not just in your zones, along with every airline callsign it flies under (`spotted`, `spotted_ops`). Writes are batched every 5 minutes.
  - An airframe heard flying as e.g. KLM in the last 180 days is a **confirmed** member of KLM's fleet.
  - Manufacturer and type pages show airframes your receiver has heard but you haven't caught yet.
- **OpenSky seed list.** The OpenSky Network aircraft database (crowdsourced, "as is") lists an operator for about 50k airframes, but its last full export is older (currently August 2025). It is imported once and re-checked monthly (`ref_fleet`). Two kinds of entries are dropped:
  - airframes re-registered since the export;
  - airframes recently heard flying for another airline.
  Of the rest, entries of a type the airline is known to fly show as "not yet heard". Others are **unconfirmed**: hidden by default, because they're often retired aircraft.
- **Hiding.** If a sleeve is wrong (e.g. an aircraft that has left the fleet), hide it with its × button.

Airfleets.net and Planespotters.net were considered, but they don't permit automated access, so they aren't used.

## Flight paths

Each sighting stores the aircraft's flight path as raw positions, not images. The path covers the time before it entered your catch zones, every position while inside them, and the time after it left. You set how much in `config.toml`:

```toml
[tracks]
before_min = 30     # or "all" for everything the receiver saw
after_min = 30
```

- **How it works:** the collector already reads every aircraft's position each poll. It keeps a short, thinned-out trail per aircraft in memory and saves it only when the aircraft is caught.
- **Resolution:**
  - Inside a zone, every poll is kept (5 s).
  - Outside a zone, a point is kept every 30 s, on a turn of 10° or more, or on an altitude change of 500 ft or more.
- **Storage:** one zlib-compressed blob per sighting (`sighting_tracks` table). An hour of flight is typically 2 to 4 KB.
- **On the card:** the back of each card shows the path on a map, with the in-zone part highlighted.
- **Raw data:**
  - `/api/sighting/<id>/track` returns JSON points `[epoch_s, lat, lon, alt_ft, in_zone]`.
  - `/api/sighting/<id>/track.geojson` returns a GeoJSON LineString, with per-vertex times, altitudes and in-zone flags in its properties.
- **Limits:** "all" means what *your* receiver heard: it begins when the aircraft first came into reception range, or when the collector last restarted. In-memory history is capped at 3 h before a catch and 6 h per track.

## Cards

- **One card per airframe** (ICAO hex), numbered in the order you caught them. Each card carries the series year of its first catch.
- **Rarity tiers**, from Common to Legendary, are worked out from data. Each card lists its reasons on the back. The rules are in `adsflightlog/rarity.py`.
  - **Local regularity** is the main signal. It's learned from your receiver: on how many recent days (out of 60) this airline + type was heard, or the type alone for aircraft without an airline callsign. A wide-body that comes to Schiphol daily is common here.
  - **Worldwide population** is the starting estimate, from the number of registered airframes of the type. For the first days, hearing 3+ different airframes of the same airline + type already marks it as routine. The local signal fully takes over after 7 days of data.
  - **Bonuses:**
    - the type is being retired or is out of production (`SUNSET`);
    - it's the only one of its type in an airline's fleet (claimed only after at least 20 of that airline's aircraft have been confirmed).
  - **Minimum tiers:**
    - military aircraft are at least rare;
    - unidentified aircraft are at least rare;
    - a special livery is at least epic, and legendary if it's one of a kind;
    - airframes flagged "interesting", and types with only a handful built, are legendary.
- **Special liveries:**
  - seeded from `adsflightlog/specials.json` (e.g. PH-BVA *Orange Pride*);
  - add your own on the back of a card under "Mark as special livery". They're stored locally, in the `specials` table.
- **Badges**:
  - `1st edition`: your first airframe of that type.
  - `new`: caught in the last 24 h.
  - `low pass`: under 2 km away and below 3,000 ft.
  - `squawk …`: an emergency was seen.
  - `military`.
  - `regular`: 10+ sightings.
  - `special livery`, `retiring`, `fleet one-off`.
- **Points and collector level**: each card is worth points by rarity, and levels need progressively more points.
- **Card back** (click a card): full details and sighting history.

Card rules live in `adsflightlog/cards.py`.

## Backups

`python3 -m adsflightlog.backup` uploads a daily archive (`adsflightlog-YYYY-MM-DD.tar.gz`) to any [rclone](https://rclone.org) remote and keeps the last `keep_days`. The archive holds a consistent database snapshot, safe to take while the collector runs, plus your `config.toml`. Reference tables are left out because they re-import automatically. Configure it under `[backup]` in `config.toml`, and schedule it, e.g. with cron:

```
30 3 * * * cd ~/adsflightlog && python3 -m adsflightlog.backup > data/backup-last-run.log 2>&1
```

**To restore:**
1. Stop both services.
2. Extract the archive.
3. Put `adsflightlog.db` in `data/` and `config.toml` in the repo root.
4. Start the services again. Reference data downloads and imports itself.

## Data

The SQLite database is at `data/adsflightlog.db` (git-ignored). It has three kinds of tables:

- `airframes`: the cards.
- `sightings`: each visit inside the radius.
- `ref_*`: reference data. Registrations and types come from the latest
  [tar1090-db](https://github.com/wiedehopf/tar1090-db) (Mictronics) release.
  It is downloaded to `data/aircraft.csv.gz` and refreshed weekly, because
  tar1090's bundled copy goes stale. Type and airline names come from tar1090's
  local files. Whenever the data updates, cards caught as "unidentified" are
  filled in. To force a refresh, run `python3 -m adsflightlog.refdb --force`.
