"""Catch-zone geometry: python3 -m unittest discover -s tests"""

import math
import unittest

from adsflightlog.collector import bearing_deg, in_range, in_sector
from adsflightlog.config import Config, Zone

LAT, LON = 45.0, 10.0  # arbitrary test location


def at(bearing: float, km: float) -> tuple[float, float]:
    """Point at a bearing/distance from the receiver (flat-earth is fine at 10 km)."""
    d_lat = km * math.cos(math.radians(bearing)) / 111.32
    d_lon = km * math.sin(math.radians(bearing)) / (111.32 * math.cos(math.radians(LAT)))
    return LAT + d_lat, LON + d_lon


def cfg(*zones: Zone) -> Config:
    return Config(
        lat=LAT, lon=LON, aircraft_json=None, zones=list(zones), max_position_age_s=15,
        poll_interval_s=5, sighting_gap_s=1200, database=None, tar1090_db_dir=None,
        aircraft_csv_url="", aircraft_csv=None, ref_refresh_days=7, web_host="", web_port=0,
    )


# Generic test layout: a 5 km circle (any altitude) plus a 10 km slice from
# west (270) clockwise to north (360) below 20,000 ft.
ZONES = cfg(
    Zone("circle", 5.0),
    Zone("slice", 10.0, bearing_from=270, bearing_to=360, max_altitude_ft=20000),
)


def ac(bearing, km, alt=10000):
    lat, lon = at(bearing, km)
    a = {"hex": "abc123", "lat": lat, "lon": lon, "seen_pos": 1}
    if alt is not None:
        a["alt_baro"] = alt
    return a


class Geometry(unittest.TestCase):
    def test_bearing(self):
        for b in (0, 45, 90, 180, 270, 315):
            self.assertAlmostEqual(bearing_deg(LAT, LON, *at(b, 10)), b, delta=0.5)

    def test_sector_wraps_north(self):
        self.assertTrue(in_sector(300, 270, 0))
        self.assertTrue(in_sector(0, 270, 360))
        self.assertTrue(in_sector(10, 330, 30))
        self.assertFalse(in_sector(90, 270, 360))
        self.assertFalse(in_sector(180, 330, 30))


class Zones(unittest.TestCase):
    def counts(self, *a, **kw):
        return in_range(ZONES, ac(*a, **kw)) is not None

    def test_inner_circle_any_direction_any_altitude(self):
        self.assertTrue(self.counts(135, 4.5, alt=38000))
        self.assertTrue(self.counts(315, 4.5, alt=38000))
        self.assertTrue(self.counts(90, 4.5, alt=None))

    def test_slice_low_counts(self):
        self.assertTrue(self.counts(315, 8, alt=19975))
        self.assertTrue(self.counts(275, 9.5, alt=3000))
        self.assertTrue(self.counts(355, 9.5, alt=0))

    def test_slice_high_or_unknown_altitude_does_not_count(self):
        self.assertFalse(self.counts(315, 8, alt=20000))
        self.assertFalse(self.counts(315, 8, alt=35000))
        self.assertFalse(self.counts(315, 8, alt=None))

    def test_outside_slice_direction_or_range(self):
        self.assertFalse(self.counts(45, 8, alt=3000))    # north-east
        self.assertFalse(self.counts(225, 8, alt=3000))   # south-west
        self.assertFalse(self.counts(315, 10.5, alt=3000))

    def test_ground(self):
        a = ac(315, 8, alt=None)
        a["alt_baro"] = "ground"
        self.assertIsNotNone(in_range(ZONES, a))

    def test_stale_position(self):
        a = ac(0, 1)
        a["seen_pos"] = 60
        self.assertIsNone(in_range(ZONES, a))


if __name__ == "__main__":
    unittest.main()
