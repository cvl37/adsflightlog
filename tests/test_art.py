import unittest
import xml.etree.ElementTree as ET

from adsflightlog import art
from adsflightlog.art import models


class ArtTest(unittest.TestCase):
    def test_every_drawing_renders_valid_svg(self):
        for item in art.catalogue():
            for view in art.VIEWS:
                body = art.svg(item["key"], view)
                self.assertIsNotNone(body, (item["key"], view))
                root = ET.fromstring(body)
                self.assertTrue(root.tag.endswith("svg"))
                self.assertNotIn("nan", root.get("viewBox"), (item["key"], view))

    def test_known_type_uses_its_own_drawing(self):
        self.assertEqual(art.key_for("B738", "L2J", "M"), "B738")
        self.assertEqual(art.key_for("a20n", "L2J", "M"), "A20N")

    def test_unknown_types_fall_back_by_description(self):
        self.assertEqual(art.key_for("ZZZZ", "L1P", "L"), "P28A")
        self.assertEqual(art.key_for("ZZZZ", "H2T", "L"), "A139")
        self.assertEqual(art.key_for("ZZZZ", "L2J", "H"), "_WIDE")
        self.assertEqual(art.key_for(None, None, None), "_JET")

    def test_cargo_airline_gets_freighter(self):
        self.assertEqual(art.key_for("B77L", "L2J", "H", "MPH"), "B77L-F")
        self.assertEqual(art.key_for("B77L", "L2J", "H", "KLM"), "B77L")
        self.assertEqual(art.key_for("C172", "L1P", "L", "MPH"), "C172")  # no freighter of a Cessna

    def test_special_angles_only_for_epic_and_up(self):
        self.assertEqual(art.view_for("484abc", "rare"), "side")
        self.assertIn(art.view_for("484abc", "epic"), ("front", "below"))
        self.assertEqual(art.view_for("484abc", "legendary"), art.view_for("484abc", "legendary"))

    def test_classic_style_turns_art_off(self):
        d = art.annotate({"type": "B738", "hex": "484abc", "rarity": "common"}, "classic")
        self.assertIsNone(d["art_img"])
        d = art.annotate({"type": "B738", "hex": "484abc", "rarity": "common"}, "vector")
        self.assertTrue(d["art_img"].startswith("/art/B738/side.svg"))

    def test_variants_differ_where_the_aircraft_do(self):
        self.assertNotEqual(models.SPECS["B738"].wingtip, models.SPECS["B38M"].wingtip)
        self.assertGreater(models.SPECS["A20N"].engines[0].dia, models.SPECS["A320"].engines[0].dia)
        self.assertGreater(models.SPECS["B78X"].L, models.SPECS["B789"].L)


if __name__ == "__main__":
    unittest.main()
