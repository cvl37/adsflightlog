"""Fleet membership rules: python3 -m unittest discover -s tests -t ."""

import time
import unittest
from pathlib import Path

from adsflightlog import fleet
from adsflightlog.db import connect

NOW = time.time()


class Fleet(unittest.TestCase):
    def setUp(self):
        c = self.conn = connect(Path(":memory:"))
        c.executescript(fleet.SCHEMA)
        c.executemany("INSERT INTO ref_aircraft VALUES (?,?,?,?,?)", [
            ("000001", "XX-AAA", "B738", "00", None),
            ("000002", "XX-AAB", "B738", "00", None),
            ("000003", "XX-AAC", "B744", "00", None),   # old type, never heard
            ("000004", "YY-NEW", "B738", "00", None),   # re-registered since export
            ("000005", "XX-AAE", "B738", "00", None),   # now flies for someone else
            ("000006", "XX-AAF", "A20N", "00", None),   # not in OpenSky, but heard
        ])
        c.executemany("INSERT INTO ref_fleet VALUES (?,?,?,?)", [
            ("000001", "TST", "XX-AAA", "B738"),
            ("000002", "TST", "XX-AAB", "B738"),
            ("000003", "TST", "XX-AAC", "B744"),
            ("000004", "TST", "XX-AAD", "B738"),
            ("000005", "TST", "XX-AAE", "B738"),
        ])
        c.execute("INSERT INTO airframes (hex, card_no, reg, type, operator, first_seen, last_seen) "
                  "VALUES ('000001', 1, 'XX-AAA', 'B738', 'TST', ?, ?)", (NOW, NOW))
        sp = fleet.Spotter(c)
        sp.observe("000006", NOW - 3600, 80.0, "TST123")
        sp.observe("000005", NOW - 3600, 120.0, "OTH456")
        sp.flush()

    def test_membership(self):
        rows = {r["hex"]: r for r in fleet.airline_fleet(self.conn, "TST", NOW)}
        self.assertTrue(rows["000001"]["collected"])
        self.assertEqual(rows["000001"]["status"], "confirmed")
        self.assertEqual(rows["000002"]["status"], "listed")       # type B738 is confirmed for TST
        self.assertEqual(rows["000003"]["status"], "unconfirmed")  # B744 never seen for TST
        self.assertNotIn("000004", rows)                          # re-registered
        self.assertNotIn("000005", rows)                          # heard flying for OTH
        self.assertEqual(rows["000006"]["status"], "confirmed")    # heard as TST123
        self.assertEqual(rows["000006"]["spotted_min_km"], 80.0)

    def test_hidden(self):
        self.conn.execute("INSERT INTO fleet_hidden VALUES ('TST', '000002')")
        rows = {r["hex"]: r for r in fleet.airline_fleet(self.conn, "TST", NOW)}
        self.assertTrue(rows["000002"]["hidden"])

    def test_manufacturer(self):
        self.assertEqual(fleet.manufacturer("AIRBUS A-320neo"), "Airbus")
        self.assertEqual(fleet.manufacturer("DE HAVILLAND DHC-8-400 Dash 8"), "De Havilland")
        self.assertEqual(fleet.manufacturer("ATR-72-600"), "ATR")
        self.assertEqual(fleet.manufacturer(None), "Unknown")


if __name__ == "__main__":
    unittest.main()
