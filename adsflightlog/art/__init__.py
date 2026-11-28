"""Card art: vector drawings per aircraft type and variant.

Drawings are generated on demand from ``models.SPECS`` (and cached), so there
is no build step and nothing to keep in sync. ``annotate`` adds the image
URLs to a card or binder row; the ``[web] art`` setting switches back to the
old silhouettes ("classic") without touching anything else.
"""

from __future__ import annotations

import hashlib
import inspect
import zlib
from dataclasses import replace
from functools import lru_cache

from . import draw, models

VIEWS = ("side", "top", "front", "below")
SPECIAL_TIERS = ("epic", "legendary")

# Generic drawings for types without their own spec, keyed by ICAO aircraft
# description (kind, engine count, engine type) and wake category.
GENERIC = {
    "L1P": "P28A", "L2P": "PA34", "L1T": "TBM9", "L2T/L": "BE20", "L2T": "AT76", "L4T": "C130",
    "L2J/L": "C25A", "L2J": "_JET", "L2J/H": "_WIDE", "L3J": "FA7X", "L4J": "_QUAD", "L4J/H": "_QUAD",
    "A1P": "P28A", "H1P": "R44", "H1T": "AS50", "H2T": "A139", "H2T/M": "A189", "G": "GLID", "B": "BALL",
    "T": "C172",
}

# Cargo airlines: their widebodies are freighters (no cabin windows).
CARGO = {
    "MPH", "CLX", "ICV", "FDX", "UPS", "GTI", "ABW", "CKS", "BOX", "GEC", "CAO", "CKK", "NCA", "SQC", "TAY",
    "ABR", "AHK", "MSX", "SWN", "DHK", "DAE", "BCS", "QAC", "CSS", "WGN", "ATN",
    "ABX", "PAC", "SOO", "NPT", "AZG", "CTJ", "FRH", "TMN", "LCO",
}

_generic_specs = {
    "_JET": replace(models.SPECS["A320"], name="Twin-engined jet", wingtip="plain", doors=(0.1, 0.82), exits=()),
    "_WIDE": replace(models.SPECS["B763"], name="Twin-engined widebody"),
    "_QUAD": replace(models.SPECS["A343"], name="Four-engined jet"),
}


def spec(key: str) -> draw.Spec | None:
    freighter = key.endswith("-F")
    base = key[:-2] if freighter else key
    s = models.SPECS.get(base) or _generic_specs.get(base)
    if s and freighter:
        s = replace(s, freighter=True, name=s.name + " (freighter)")
    return s


def has_freighter(s: draw.Spec) -> bool:
    return s.kind == "jet" and s.cockpit == "airliner" and s.windows and s.L > 30


def key_for(type_code: str | None, desc: str | None = None, wtc: str | None = None,
            operator: str | None = None) -> str:
    t = (type_code or "").upper()
    key = t if t in models.SPECS else None
    if not key:
        d = (desc or "").upper()
        kind = d[:1]
        w = (wtc or "").upper()
        if kind in ("G", "B", "T"):
            key = GENERIC[kind]
        elif d:
            key = GENERIC.get(f"{d[:3]}/{w}") or GENERIC.get(d[:3])
        key = key or "_JET"
    s = spec(key)
    if operator and operator.upper() in CARGO and s and has_freighter(s):
        key += "-F"
    return key


def view_for(hex_: str, rarity: str | None) -> str:
    """Side profile by default; epic and legendary cards get a special angle."""
    if rarity in SPECIAL_TIERS:
        return ("front", "below")[zlib.crc32(hex_.encode()) % 2]
    return "side"


def _code_version() -> str:
    src = inspect.getsource(draw) + inspect.getsource(models)
    return hashlib.sha1(src.encode()).hexdigest()[:8]


VERSION = _code_version()


def url(key: str, view: str) -> str:
    return f"/art/{key}/{view}.svg?v={VERSION}"


def annotate(d: dict, style: str = "vector") -> dict:
    """Add art_img (card face) and art_top (plan view) to a card or binder row."""
    if style == "classic":
        d["art_img"] = d["art_top"] = None
        return d
    key = key_for(d.get("type"), d.get("desc"), d.get("wtc"), d.get("operator"))
    d["art_key"] = key
    d["art_img"] = url(key, view_for(d.get("hex") or "", d.get("rarity")))
    d["art_side"] = url(key, "side")
    d["art_top"] = url(key, "top")
    return d


@lru_cache(maxsize=512)
def svg(key: str, view: str) -> bytes | None:
    s = spec(key)
    if not s or view not in VIEWS:
        return None
    return getattr(draw, view)(s).encode()


def catalogue() -> list[dict]:
    """Every drawable key, for the gallery page."""
    out = []
    for k, s in list(models.SPECS.items()) + list(_generic_specs.items()):
        out.append({"key": k, "name": s.name, "kind": s.kind, "generic": k.startswith("_")})
        if has_freighter(s) and not k.startswith("_"):
            out.append({"key": k + "-F", "name": s.name + " (freighter)", "kind": s.kind, "generic": False})
    return out
