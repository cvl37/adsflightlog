"""Turn logged airframes into collectible cards: rarity, badges, points, art class."""

from __future__ import annotations

import time

from .rarity import SUNSET, TIERS, RarityModel
POINTS = {"common": 10, "uncommon": 25, "rare": 60, "epic": 150, "legendary": 400}

def art_class(desc: str | None, category: str | None) -> str:
    """Which silhouette to draw: jet, quad, prop, heli, glider, balloon, drone."""
    if desc:
        kind, engines, etype = desc[:1], desc[1:2], desc[2:3]
        if kind in ("H", "G"):
            return "heli"
        if kind == "T":
            return "heli"
        if etype == "J" and engines in ("4", "6", "8"):
            return "quad"
        if etype == "J":
            return "jet"
        if etype in ("P", "T"):
            return "prop"
    cat = (category or "").upper()
    return {
        "A7": "heli", "B1": "glider", "B2": "balloon", "B6": "drone",
        "A5": "quad", "A1": "prop",
    }.get(cat, "jet")


def build_cards(rows: list[dict], model: RarityModel | None = None, now: float | None = None) -> list[dict]:
    """Annotate airframe rows (joined with ref_types/ref_operators) in place."""
    now = now or time.time()
    per_type: dict[str, int] = {}
    first_of_type: dict[str, int] = {}
    for r in rows:
        t = r.get("type") or "?"
        per_type[t] = per_type.get(t, 0) + 1
        if t not in first_of_type or r["card_no"] < first_of_type[t]:
            first_of_type[t] = r["card_no"]

    for r in rows:
        t = r.get("type") or "?"
        if model:
            tier, reasons = model.assess(r)
        else:
            tier, reasons = "common", []
        special = model.specials.get(r["hex"]) if model else None
        badges = []
        if special:
            badges.append("special livery")
        if r.get("type") in SUNSET:
            badges.append("retiring")
        if any(x.startswith("The only ") for x in reasons):
            badges.append("fleet one-off")
        if first_of_type.get(t) == r["card_no"] and t != "?":
            badges.append("1st edition")
        if now - r["first_seen"] < 86400:
            badges.append("new")
        if (r.get("closest_km") or 99) < 2 and (r.get("closest_alt_ft") or 99999) < 3000:
            badges.append("low pass")
        if r.get("emergency"):
            badges.append(f"squawk {r['emergency']}")
        if r.get("military"):
            badges.append("military")
        if (r.get("sightings") or 0) >= 10:
            badges.append("regular")

        r["rarity"] = tier
        r["rarity_reasons"] = reasons
        r["special"] = special
        r["points"] = POINTS[tier] + (100 if r.get("emergency") else 0)
        r["badges"] = badges
        r["art"] = art_class(r.get("desc"), r.get("category"))
        r["series"] = time.strftime("%Y", time.localtime(r["first_seen"]))
        r["type_count"] = per_type[t]
    return rows
