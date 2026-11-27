"""Rarity model: python3 -m unittest discover -s tests -t ."""

import time
import unittest
from pathlib import Path

from adsflightlog import fleet
from adsflightlog.db import connect
from adsflightlog.rarity import RarityModel, SPECIALS_SCHEMA

NOW = time.mktime((2026, 6, 30, 23, 0, 0, 0, 0, -1))


def day(n):
    return time.strftime("%Y-%m-%d", time.localtime(NOW - n * 86400))


class Rarity(unittest.TestCase):
    def setUp(self):
        c = self.conn = connect(Path(":memory:"))
        c.executescript(fleet.SCHEMA)
        c.executescript(SPECIALS_SCHEMA)
        refs = []
        # population: 2000 A320s, 400 B772s, 100 A343s
        refs += [(f"a{i:05x}", None, "A320", "00", None) for i in range(2000)]
        refs += [(f"b{i:05x}", None, "B772", "00", None) for i in range(400)]
        refs += [(f"c{i:05x}", None, "A343", "00", None) for i in range(100)]
        c.executemany("INSERT INTO ref_aircraft VALUES (?,?,?,?,?)", refs)

    def card(self, hx, typ, op=None, **kw):
        return {"hex": hx, "type": typ, "operator": op, "desc": "L2J", **kw}

    def heard(self, hx, op, days):
        self.conn.executemany("INSERT OR REPLACE INTO spotted_days VALUES (?,?,?)",
                              [(day(d), hx, op) for d in days])

    def test_prior_without_local_data(self):
        m = RarityModel(self.conn, NOW)
        self.assertEqual(m.assess(self.card("a00001", "A320", "KLM"))[0], "common")
        self.assertEqual(m.assess(self.card("b00001", "B772", "AAL"))[0], "uncommon")

    def test_daily_visitor_is_common(self):
        # an American 777-200 heard every day for two weeks
        for d in range(14):
            self.heard(f"b{d % 3:05x}", "AAL", [d])
        for d in range(14):                    # other traffic so every day has data
            self.heard("a00002", "KLM", [d])
        m = RarityModel(self.conn, NOW)
        tier, reasons = m.assess(self.card("b00000", "B772", "AAL"))
        self.assertEqual(tier, "common")
        self.assertTrue(any("heard on" in r for r in reasons))

    def test_occasional_visitor_is_rare(self):
        for d in range(30):
            self.heard("a00002", "KLM", [d])
        self.heard("b00005", "XYZ", [3])
        m = RarityModel(self.conn, NOW)
        self.assertIn(m.assess(self.card("b00005", "B772", "XYZ"))[0], ("rare", "epic"))

    def test_sunset_type_gets_bonus(self):
        m = RarityModel(self.conn, NOW)
        tier, reasons = m.assess(self.card("c00001", "A343", "DLH"))
        self.assertEqual(tier, "epic")          # rare by population + retiring
        self.assertTrue(any("A340" in r for r in reasons))

    def test_special_livery(self):
        self.conn.execute("INSERT INTO specials VALUES ('a00001','PH-XXX','Orange Pride','note',1,'seed',0)")
        m = RarityModel(self.conn, NOW)
        tier, reasons = m.assess(self.card("a00001", "A320", "KLM"))
        self.assertEqual(tier, "legendary")
        self.assertTrue(any("Orange Pride" in r for r in reasons))
        self.conn.execute("UPDATE specials SET one_off=0")
        self.assertEqual(RarityModel(self.conn, NOW).assess(self.card("a00001", "A320", "KLM"))[0], "epic")

    def test_military_and_unknown_floor(self):
        m = RarityModel(self.conn, NOW)
        self.assertEqual(m.assess(self.card("a00003", "A320", "GAF", military=1))[0], "rare")
        self.assertEqual(m.assess(self.card("ffffff", None))[0], "rare")


if __name__ == "__main__":
    unittest.main()
