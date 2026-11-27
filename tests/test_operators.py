"""Operator resolution: python3 -m unittest discover -s tests -t ."""

import unittest
from pathlib import Path

from adsflightlog.db import connect
from adsflightlog.operators import OperatorResolver


class Resolver(unittest.TestCase):
    def setUp(self):
        conn = connect(Path(":memory:"))
        conn.executemany("INSERT INTO ref_operators VALUES (?,?,?,?)", [
            ("KLM", "KLM Royal Dutch Airlines", "Netherlands", "KLM"),
            ("OSY", "Open Skies Consultative Commission", "United States", "OPEN SKIES"),
            ("GAF", "German Air Force", "Germany", "GERMAN AIR FORCE"),
            ("GAM", "German Army", "Germany", "GERMAN ARMY"),
            ("NAF", "Royal Netherlands Air Force", "Netherlands", "NETHERLANDS AIR FORCE"),
            ("RCH", "Air Mobility Command", "United States", "REACH"),
            ("DLH", "Lufthansa", "Germany", "LUFTHANSA"),
        ])
        self.r = OperatorResolver(conn, Path("/nonexistent"))
        # Minimal address table instead of tar1090's file.
        self.r.ranges = [(0x3C0000, 0x3FFFFF, "Germany"), (0x480000, 0x487FFF, "Netherlands"),
                         (0xA00000, 0xAFFFFF, "United States")]
        self.r.starts = [x[0] for x in self.r.ranges]

    def test_civil_uses_callsign(self):
        self.assertEqual(self.r.resolve("484000", "KLM123", False), "KLM")
        self.assertIsNone(self.r.resolve("484000", "PHABC", False))

    def test_mission_callsign_never_an_operator(self):
        self.assertIsNone(self.r.resolve("484000", "OSY16T", False))

    def test_military_open_skies_becomes_air_force(self):
        self.assertEqual(self.r.resolve("3f9a92", "OSY16T", True), "GAF")

    def test_military_keeps_own_branch(self):
        self.assertEqual(self.r.resolve("3f9a92", "GAM123", True), "GAM")

    def test_military_rejects_foreign_or_civil_callsign_operator(self):
        self.assertEqual(self.r.resolve("3f9a92", "NAF12", True), "GAF")   # other country
        self.assertEqual(self.r.resolve("3f9a92", "DLH4A", True), "GAF")   # civil airline
        self.assertEqual(self.r.resolve("480001", None, True), "NAF")

    def test_country_without_default(self):
        self.assertEqual(self.r.resolve("ae1234", "RCH123", True), "RCH")
        self.assertIsNone(self.r.resolve("ae1234", "DUKE01", True))


if __name__ == "__main__":
    unittest.main()
