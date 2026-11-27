"""Turn logged airframes into collectible cards: rarity, badges, points, art class."""

from __future__ import annotations

import time

TIERS = ["common", "uncommon", "rare", "epic", "legendary"]
POINTS = {"common": 10, "uncommon": 25, "rare": 60, "epic": 150, "legendary": 400}

# Bread-and-butter European traffic.
COMMON_TYPES = {
    "A318", "A319", "A320", "A321", "A19N", "A20N", "A21N",
    "B733", "B734", "B735", "B736", "B737", "B738", "B739", "B37M", "B38M", "B39M", "B3XM",
    "E170", "E175", "E75L", "E75S", "E190", "E195", "E290", "E295",
    "BCS1", "BCS3", "CRJ2", "CRJ7", "CRJ9", "CRJX",
    "AT43", "AT45", "AT72", "AT75", "AT76", "DH8D",
}

# Heavy hitters you won't see every day.
SPECIAL_TYPES = {
    # legendary
    "A124": "legendary", "A225": "legendary", "A3ST": "legendary", "A337": "legendary",
    "BLCF": "legendary", "SLCF": "legendary", "C5M": "legendary", "CONC": "legendary",
    "B52": "legendary", "U2": "legendary", "E3TF": "legendary", "E3CF": "legendary",
    "A400": "epic", "C17": "epic", "IL76": "epic", "A388": "epic", "B748": "epic",
    "B744": "epic", "B742": "epic", "MD11": "epic", "K35R": "epic",
    "A30B": "rare", "A306": "rare", "A310": "rare", "B762": "rare", "B752": "rare",
    "B753": "rare", "A342": "rare", "A343": "rare", "A345": "rare", "A346": "rare",
    "B712": "rare", "MD82": "rare", "MD83": "rare", "MD87": "rare", "MD88": "rare",
    "F100": "rare", "F70": "rare", "B461": "rare", "B462": "rare", "B463": "rare",
}


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


def base_tier(card: dict) -> str:
    t = card.get("type")
    desc = card.get("desc") or ""
    if card.get("interesting"):
        return "legendary"
    if t in SPECIAL_TYPES:
        tier = SPECIAL_TYPES[t]
    elif card.get("military"):
        tier = "epic"
    elif not t:
        tier = "rare"  # unknown airframe: a mystery card
    elif t in COMMON_TYPES:
        tier = "common"
    elif desc[:1] in ("H", "G", "T", "A", "S"):
        tier = "rare"  # rotorcraft, gyros, tiltrotors, amphibians, seaplanes
    elif desc[2:3] == "J" and desc[1:2] in ("4", "6", "8"):
        tier = "epic"
    else:
        tier = "uncommon"
    if card.get("military") and TIERS.index(tier) < TIERS.index("epic"):
        tier = "epic"
    return tier


def build_cards(rows: list[dict], now: float | None = None) -> list[dict]:
    """Annotate airframe rows (joined with ref_types/ref_operators) in place."""
    now = now or time.time()
    total = len(rows)
    per_type: dict[str, int] = {}
    first_of_type: dict[str, int] = {}
    for r in rows:
        t = r.get("type") or "?"
        per_type[t] = per_type.get(t, 0) + 1
        if t not in first_of_type or r["card_no"] < first_of_type[t]:
            first_of_type[t] = r["card_no"]

    for r in rows:
        tier = base_tier(r)
        t = r.get("type") or "?"
        # Local scarcity: once the collection is big enough, a type you've only
        # ever caught once gets bumped a tier (up to epic).
        if total >= 100 and t != "?" and per_type[t] == 1 and TIERS.index(tier) < 3:
            tier = TIERS[TIERS.index(tier) + 1]
        badges = []
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
        r["points"] = POINTS[tier] + (100 if r.get("emergency") else 0)
        r["badges"] = badges
        r["art"] = art_class(r.get("desc"), r.get("category"))
        r["series"] = time.strftime("%Y", time.localtime(r["first_seen"]))
        r["type_count"] = per_type[t]
    return rows
