"""Home airline of an airframe: python3 -m unittest discover -s tests -t ."""

import time
import unittest
from pathlib import Path

from adsflightlog import fleet, helispot, home, owners
from adsflightlog.db import connect
from adsflightlog.operators import OperatorResolver

NOW = time.time()
DAY = time.strftime("%Y-%m-%d", time.localtime(NOW))


def day(n):
    return time.strftime("%Y-%m-%d", time.localtime(NOW - n * 86400))


class Home(unittest.TestCase):
    def setUp(self):
        c = self.conn = connect(Path(":memory:"))
        c.executescript(fleet.SCHEMA)
        c.executemany("INSERT INTO ref_operators VALUES (?,?,?,?)", [
            ("BIG", "Big Airways", "Xland", "BIG"),
            ("REG", "Big Regional", "Xland", "REGIONAL"),
            ("FRN", "Foreign Air", "Yland", "FOREIGN"),
            ("LSE", "Lease Air", "Zland", "LEASE"),
        ])
        self.r = OperatorResolver(c, Path("/nonexistent"))
        self.r.ranges = [(0x100000, 0x1FFFFF, "Xland"), (0x200000, 0x2FFFFF, "Yland"),
                         (0x300000, 0x3FFFFF, "Zland")]
        self.r.starts = [x[0] for x in self.r.ranges]
        days = []
        # BIG's own fleet: big, so BIG is the larger airline.
        for i in range(10):
            days += [(day(d), f"10000{i}", "BIG") for d in range(5)]
        # Regional jet: mostly BIG flight numbers, some of its own.
        days += [(day(d), "110001", "BIG") for d in range(8)] + [(day(d), "110001", "REG") for d in range(8, 11)]
        # Foreign wet-lease flying for BIG, once under its own callsign (like F-HBLJ for KLM).
        days += [(day(d), "200001", "BIG") for d in range(3)] + [(day(5), "200001", "FRN")]
        # Foreign airframe heard only for BIG, OpenSky says FRN.
        days += [(day(1), "200002", "BIG")]
        # Foreign airframe flying for BIG and REG, nothing from its own country: wet-lease.
        days += [(day(d), "300001", "BIG") for d in range(4)] + [(day(d), "300001", "REG") for d in range(4, 7)]
        c.executemany("INSERT INTO spotted_days VALUES (?,?,?)", days)
        c.executemany("INSERT OR REPLACE INTO spotted_ops VALUES (?,?,?,?)",
                      [(h, o, NOW - 86400, NOW - 3600) for _, h, o in days])
        c.executemany("INSERT INTO ref_aircraft VALUES (?,?,?,?,?)",
                      [(h, None, "E190", "00", None) for h in {d[1] for d in days}])
        c.execute("INSERT INTO ref_fleet VALUES ('200002', 'FRN', NULL, 'E190')")
        c.execute("INSERT INTO airframes (hex, card_no, reg, type, operator, first_seen, last_seen) "
                  "VALUES ('200001', 1, 'Y-AAA', 'E190', 'BIG', ?, ?)", (NOW, NOW))
        home.compute(c, self.r, NOW)
        self.home = {h: o for h, o in c.execute("SELECT hex, operator FROM airframe_home")}

    def test_registry_country_wins(self):
        self.assertEqual(self.home["200001"], "FRN")

    def test_regional_beats_mainline(self):
        self.assertEqual(self.home["110001"], "REG")
        self.assertEqual(self.home["100001"], "BIG")

    def test_opensky_for_foreign_airframe(self):
        self.assertEqual(self.home["200002"], "FRN")

    def test_wet_lease_has_no_home(self):
        self.assertIsNone(self.home["300001"])
        ff = self.conn.execute("SELECT flying_for FROM airframe_home WHERE hex='300001'").fetchone()[0]
        self.assertEqual(ff, "BIG")

    def test_card_moves_to_home_airline(self):
        op = self.conn.execute("SELECT operator FROM airframes WHERE hex='200001'").fetchone()[0]
        self.assertEqual(op, "FRN")

    def test_fleet_counts_home_only(self):
        big = {r["hex"] for r in fleet.airline_fleet(self.conn, "BIG", NOW)}
        self.assertEqual(big, {f"10000{i}" for i in range(10)})
        reg = {r["hex"] for r in fleet.airline_fleet(self.conn, "REG", NOW)}
        self.assertEqual(reg, {"110001"})
        frn = {r["hex"]: r["status"] for r in fleet.airline_fleet(self.conn, "FRN", NOW)}
        self.assertEqual(frn, {"200001": "confirmed", "200002": "confirmed"})

    def test_registered_operator_comes_first(self):
        # hexdb.io says the wet-lease belongs to LSE, and the regional jet to BIG.
        owners.store(self.conn, "300001", {"Registration": None, "OperatorFlagCode": "LSE",
                                           "RegisteredOwners": "Lease Air"})
        owners.store(self.conn, "110001", {"OperatorFlagCode": "BIG"})
        owners.store(self.conn, "200001", None)   # not in hexdb: falls back to the guess
        home.compute(self.conn, self.r, NOW)
        self.assertEqual(home.lookup(self.conn, "300001"), (True, "LSE"))
        self.assertEqual(home.lookup(self.conn, "110001"), (True, "BIG"))
        self.assertEqual(home.lookup(self.conn, "200001"), (True, "FRN"))

    def test_registered_owner_without_code(self):
        # A police helicopter that sometimes flies coastguard (BIG) flights.
        owners.store(self.conn, "100001", {"RegisteredOwners": "National Police Air Unit"})
        # Owner name of a known airline from the same country, no code.
        owners.store(self.conn, "100002", {"RegisteredOwners": "Big Regional B.V."})
        # A lessor says nothing: keep the guess.
        owners.store(self.conn, "100003", {"RegisteredOwners": "Sky Leasing Ltd"})
        home.compute(self.conn, self.r, NOW)
        self.assertEqual(home.lookup(self.conn, "100001"), (True, None))
        why, ff = self.conn.execute("SELECT reason, flying_for FROM airframe_home WHERE hex='100001'").fetchone()
        self.assertEqual((why, ff), ("registered to National Police Air Unit", None))
        self.assertEqual(home.lookup(self.conn, "100002"), (True, "REG"))
        self.assertEqual(home.lookup(self.conn, "100003"), (True, "BIG"))

    def test_helispot_operator_comes_first(self):
        c = self.conn
        c.execute("INSERT INTO airframes (hex, card_no, reg, type, operator, first_seen, last_seen) "
                  "VALUES ('100005', 2, 'X-HLP', 'EC35', NULL, ?, ?)", (NOW, NOW))
        c.execute("UPDATE ref_aircraft SET reg='X-POL' WHERE hex='100001'")
        owners.store(c, "100001", {"RegisteredOwners": "National Police Air Unit"})
        helispot.store(c, [
            {"reg": "X-HLP", "operator": "Medical Air Assistance BV", "raw": "", "page": "", "cancelled": False, "crashed": False},
            {"reg": "XPOL", "operator": "Air Police", "raw": "", "page": "", "cancelled": False, "crashed": False},
            # struck off: says nothing about the current owner of the hex
            {"reg": "Y-AAA", "operator": "Old Heli Co", "raw": "", "page": "", "cancelled": True, "crashed": False},
        ], NOW)
        home.compute(c, self.r, NOW)
        why = lambda h: c.execute("SELECT operator, reason FROM airframe_home WHERE hex=?", (h,)).fetchone()
        self.assertEqual(tuple(why("100005")), (None, "operated by Medical Air Assistance BV"))
        self.assertEqual(tuple(why("100001")), (None, "operated by Air Police"))
        self.assertEqual(home.lookup(c, "200001"), (True, "FRN"))

    def test_helispot_name_cleaning(self):
        for raw, want in [
            ("ANWB Medical Air Assistance BV, Lelystad (voor RAV)", "ANWB Medical Air Assistance BV"),
            ("Heli & Co, Liege (B) - owner TECAIR Arcangues (FR)", "Heli & Co"),
            ("Heliair, eigenaar Top Motion Works, Odijk (NL)", "Heliair"),
            ("Heli Luxembourg (owner: Tradlux SA)", "Heli Luxembourg"),
            ("Helihansa (AU) - Startrade (D)", "Helihansa"),
            ("Luchtvaartpolitie NL", "Luchtvaartpolitie NL"),
            ("Bristow Helicopters ", "Bristow Helicopters"),
        ]:
            self.assertEqual(helispot.clean_operator(raw), want)

    def test_helispot_page_parsing(self):
        page = ('<article class="post heli-card"><h3 class="heli-callsign"><a href="/helicopter/gMZZzm">PH-HLP</a></h3>'
                '<p class="heli-operator">ANWB Medical Air Assistance BV, Lelystad</p></article>'
                '<article class="post heli-card is-unsubscribed"><h3><a href="/helicopter/xqlrp6">PH-ULP</a>'
                '<span class="heli-badge cancelled">doorgehaald</span></h3><p class="heli-operator">ANWB</p></article>')
        a, b = helispot.parse_model_page(page)
        self.assertEqual((a["reg"], a["operator"], a["cancelled"]), ("PH-HLP", "ANWB Medical Air Assistance BV", False))
        self.assertEqual((b["reg"], b["cancelled"]), ("PH-ULP", True))

    def test_registered_operator_ignored_after_reregistration(self):
        self.conn.execute("UPDATE ref_aircraft SET reg='Y-NEW' WHERE hex='200001'")
        owners.store(self.conn, "200001", {"Registration": "Y-OLD", "OperatorFlagCode": "BIG"})
        home.compute(self.conn, self.r, NOW)
        self.assertEqual(home.lookup(self.conn, "200001"), (True, "FRN"))

    def test_next_lookup_prefers_caught_cards(self):
        self.assertEqual(owners.next_hex(self.conn, NOW), ("200001", True))
        owners.store(self.conn, "200001", None, NOW)
        hx, caught = owners.next_hex(self.conn, NOW)
        self.assertFalse(caught)

    def test_override(self):
        self.conn.execute("INSERT INTO home_overrides VALUES ('300001', 'LSE')")
        home.compute(self.conn, self.r, NOW)
        self.assertEqual(home.lookup(self.conn, "300001"), (True, "LSE"))


if __name__ == "__main__":
    unittest.main()
