"""Card editions: python3 -m unittest discover -s tests -t ."""

import unittest
from pathlib import Path

from adsflightlog import editions
from adsflightlog.cards import POINTS
from adsflightlog.db import connect

DAY = 86400
T0 = 1_800_000_000.0


def card(hx, no, rarity="common", reg=None, special=None, op="KLM"):
    return {"hex": hx, "card_no": no, "rarity": rarity, "rarity_score": 0.5,
            "rarity_reasons": [f"why {rarity}"], "special": special, "reg": reg or hx.upper(),
            "type": "B77W", "model": "BOEING 777-300ER", "operator": op, "badges": [], "emergency": None}


class Editions(unittest.TestCase):
    def setUp(self):
        self.c = connect(Path(":memory:"))
        editions.ensure_schema(self.c)
        self.c.executemany("INSERT INTO airframes (hex, card_no, first_seen, last_seen) VALUES (?,?,?,?)",
                           [("aaaaaa", 1, T0, T0), ("bbbbbb", 2, T0, T0)])
        self.cards = [card("aaaaaa", 1, "legendary", "PH-BVA", {"title": "Orange Pride", "one_off": True}),
                      card("bbbbbb", 2, "uncommon")]

    def eds(self, hx):
        return editions.by_hex(self.c).get(hx, [])

    def test_nothing_happens_before_lock(self):
        self.assertEqual(editions.sync(self.c, self.cards, T0), [])
        self.assertEqual(self.eds("aaaaaa"), [])

    def test_lock_creates_first_editions(self):
        self.assertEqual(editions.lock(self.c, self.cards, T0), 2)
        e = self.eds("aaaaaa")[0]
        self.assertEqual((e["edition"], e["card_no"], e["rarity"]), (1, 1, "legendary"))
        self.assertIsNotNone(editions.locked_at(self.c))

    def test_respray_retires_and_issues_new_edition(self):
        editions.lock(self.c, self.cards, T0)
        now_plain = [card("aaaaaa", 1, "uncommon", "PH-BVA", None), self.cards[1]]
        events = editions.sync(self.c, now_plain, T0 + DAY)
        self.assertEqual(len(events), 1)
        old, new = self.eds("aaaaaa")
        self.assertEqual(old["rarity"], "legendary")
        self.assertIsNotNone(old["retired"])
        self.assertIn("Orange Pride", old["retire_reason"])
        self.assertEqual((new["edition"], new["card_no"], new["rarity"], new["special"]), (2, 3, "uncommon", None))

    def test_tier_change_must_be_stable(self):
        editions.lock(self.c, self.cards, T0)
        higher = [self.cards[0], card("bbbbbb", 2, "rare")]
        self.assertEqual(editions.sync(self.c, higher, T0 + DAY), [])        # pending starts
        self.assertEqual(editions.sync(self.c, higher, T0 + 4 * DAY), [])    # not stable yet
        self.assertEqual(len(editions.sync(self.c, higher, T0 + 8.5 * DAY)), 1)
        self.assertEqual([e["rarity"] for e in self.eds("bbbbbb")], ["uncommon", "rare"])

    def test_flapping_tier_does_not_issue(self):
        editions.lock(self.c, self.cards, T0)
        editions.sync(self.c, [self.cards[0], card("bbbbbb", 2, "rare")], T0 + DAY)
        editions.sync(self.c, self.cards, T0 + 2 * DAY)                      # back to uncommon
        self.assertEqual(editions.sync(self.c, [self.cards[0], card("bbbbbb", 2, "rare")], T0 + 9 * DAY), [])
        self.assertEqual(len(self.eds("bbbbbb")), 1)

    def test_reregistration(self):
        editions.lock(self.c, self.cards, T0)
        events = editions.sync(self.c, [self.cards[0], card("bbbbbb", 2, "uncommon", reg="OO-NEW")], T0 + DAY)
        self.assertIn("Re-registered", events[0])

    def test_new_catch_after_lock(self):
        editions.lock(self.c, self.cards, T0)
        self.c.execute("INSERT INTO airframes (hex, card_no, first_seen, last_seen) VALUES ('cccccc', ?, ?, ?)",
                       (editions.next_card_no(self.c), T0, T0))
        self.assertEqual(editions.next_card_no(self.c), 4)
        editions.ensure_first_editions(self.c, self.cards + [card("cccccc", 3, "rare")], T0 + DAY)
        self.assertEqual(self.eds("cccccc")[0]["edition"], 1)

    def test_apply_keeps_frozen_rarity_on_retired_card(self):
        editions.lock(self.c, self.cards, T0)
        now_plain = [card("aaaaaa", 1, "uncommon", "PH-BVA", None), self.cards[1]]
        editions.sync(self.c, now_plain, T0 + DAY)
        out = editions.apply(now_plain, editions.by_hex(self.c), POINTS)
        bva = [d for d in out if d["hex"] == "aaaaaa"]
        self.assertEqual([(d["edition"], d["rarity"], bool(d["retired"])) for d in bva],
                         [(1, "legendary", True), (2, "uncommon", False)])
        self.assertIn("special livery", bva[0]["badges"])
        self.assertNotIn("special livery", bva[1]["badges"])
        self.assertEqual(bva[0]["points"], POINTS["legendary"])


if __name__ == "__main__":
    unittest.main()
