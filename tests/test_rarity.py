"""Weighted rarity model: python3 -m unittest discover -s tests -t ."""

import time
import unittest
from pathlib import Path

from adsflightlog import fleet, history
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
        c.executescript(history.SCHEMA)
        refs = []
        refs += [(f"a{i:05x}", None, "A320", "00", None) for i in range(2000)]   # common worldwide
        refs += [(f"b{i:05x}", None, "B772", "00", None) for i in range(400)]    # uncommon worldwide
        refs += [(f"c{i:05x}", None, "A343", "00", None) for i in range(100)]    # rare + retiring
        refs += [(f"d{i:05x}", None, "E3XX", "00", None) for i in range(50)]     # few worldwide
        c.executemany("INSERT INTO ref_aircraft VALUES (?,?,?,?,?)", refs)

    def card(self, hx, typ, op=None, **kw):
        return {"hex": hx, "type": typ, "operator": op, "desc": "L2J", **kw}

    def heard(self, hx, op, days):
        self.conn.executemany("INSERT OR REPLACE INTO spotted_days VALUES (?,?,?)",
                              [(day(d), hx, op) for d in days])

    def background(self, n_days=30):
        """Other traffic so every day in the window has data."""
        self.heard("a00100", "BGX", range(n_days))

    def model(self, **kw):
        return RarityModel(self.conn, NOW, **kw)

    def test_no_local_data_uses_worldwide(self):
        m = self.model()
        self.assertEqual(m.assess(self.card("a00001", "A320", "KLM"))[0], "common")

    def test_common_worldwide_but_never_here_is_not_common(self):
        self.background()
        self.heard("a00007", "XYZ", [2])
        self.assertEqual(self.model().assess(self.card("a00007", "A320", "XYZ"))[0], "uncommon")

    def test_rare_worldwide_but_daily_here_is_more_than_common(self):
        self.background()
        for d in range(30):
            self.heard(f"d{d % 4:05x}", "HOM", [d])
        self.assertEqual(self.model().assess(self.card("d00000", "E3XX", "HOM"))[0], "uncommon")

    def test_daily_widebody_is_common(self):
        self.background()
        for d in range(30):
            self.heard(f"b{d % 3:05x}", "AAL", [d])
        tier, reasons = self.model().assess(self.card("b00000", "B772", "AAL"))
        self.assertEqual(tier, "common")
        self.assertTrue(any(r.startswith("Local (20%)") for r in reasons))

    def test_special_livery_rarely_seen_is_legendary_daily_is_epic(self):
        self.conn.execute("INSERT INTO specials VALUES ('b00009','PH-XXX','Orange Pride','note',1,'seed',0)")
        self.background()
        self.heard("b00009", "KLM", [5])
        self.assertEqual(self.model().assess(self.card("b00009", "B772", "KLM", reg="PH-XXX"))[0], "legendary")
        self.heard("b00009", "KLM", range(30))
        self.assertEqual(self.model().assess(self.card("b00009", "B772", "KLM", reg="PH-XXX"))[0], "epic")

    def test_retiring_type_scores_higher_worldwide(self):
        tier, reasons = self.model().assess(self.card("c00001", "A343", "DLH"))
        self.assertEqual(tier, "rare")
        self.assertTrue(any("A340" in r and "3/4" in r for r in reasons))

    def test_learning_period(self):
        self.background(7)
        self.heard("a00007", "XYZ", [2])
        reasons = self.model().assess(self.card("a00007", "A320", "XYZ"))[1]
        self.assertTrue(any("still learning" in r for r in reasons))
        reasons = self.model(learn_days=6).assess(self.card("a00007", "A320", "XYZ"))[1]
        self.assertFalse(any("still learning" in r for r in reasons))

    def test_weights_are_normalised(self):
        m = self.model(weights={"special": 45, "worldwide": 35, "local": 20})
        self.assertAlmostEqual(sum(m.weights.values()), 1.0)

    def test_airport_history_counts_as_local(self):
        # Only Schiphol history (no receiver data): a daily American 777 is common.
        rows = [(day(d), "a00100", "BGX") for d in range(30)] + [(day(d), f"b{d % 3:05x}", "AAL") for d in range(30)]
        self.conn.executemany("INSERT INTO airport_days VALUES (?,?,?)", rows)
        tier, reasons = self.model().assess(self.card("b00000", "B772", "AAL"))
        self.assertEqual(tier, "common")
        self.assertFalse(any("still learning" in r for r in reasons))

    def test_military_and_unknown_floor(self):
        m = self.model()
        self.assertEqual(m.assess(self.card("a00003", "A320", "GAF", military=1))[0], "rare")
        self.assertEqual(m.assess(self.card("ffffff", None))[0], "rare")
        self.assertEqual(m.assess(self.card("a00004", "A320", interesting=1))[0], "legendary")


if __name__ == "__main__":
    unittest.main()
