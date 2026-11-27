"""Airline logos from Soaring Symbols (https://soaringsymbols.org).

The catalog (MIT-licensed data) maps ICAO codes to a slug, display name,
alliance, brand colour and which marks exist. Logo SVGs are fetched from the
version-pinned jsDelivr copy of the npm package on first use and cached under
``data/logos`` so the browser never hotlinks the upstream API.

Airline marks are trademarks of their owners; they are shown here only to
identify the airline operating a flight.
"""

from __future__ import annotations

import json
import re
import threading
import time
import urllib.request
from pathlib import Path

CATALOG_URL = "https://soaringsymbols.org/api/airlines"
# Image API crops the 64x64 canvas to the drawing (viewbox=auto); CDN is the fallback.
IMAGE_API = "https://soaringsymbols.org/api/airlines/{slug}/{variant}.svg?viewbox=auto"
CDN = "https://cdn.jsdelivr.net/npm/soaring-symbols@{version}/dist/airlines/{slug}/{variant}.svg"

# Subsidiaries that fly under the parent's brand but have their own ICAO code.
# They borrow the parent's marks and colour; their own name is kept.
BRAND_ALIASES = {
    "KLC": "KLM",  # KLM Cityhopper
    "EJU": "EZY",  # easyJet Europe
    "EZS": "EZY",  # easyJet Switzerland
    "CLH": "DLH",  # Lufthansa CityLine
    "BCY": "BAW",  # BA CityFlyer
    "EFW": "BAW",  # BA Euroflyer
    "IBS": "IBE",  # Iberia Express
    "ANE": "IBE",  # Air Nostrum (Iberia Regional)
}
VARIANTS = {"icon", "icon-mono", "icon-dark", "logo", "logo-mono", "logo-dark"}
ICAO = re.compile(r"^[A-Z]{3}$")
UA = {"User-Agent": "adsflightlog"}


class Logos:
    def __init__(self, data_dir: Path, refresh_days: float = 7):
        self.dir = data_dir / "logos"
        self.catalog_file = data_dir / "soaring-symbols.json"
        self.refresh_s = refresh_days * 86400
        self.lock = threading.Lock()
        self.version = None
        self.by_icao: dict[str, dict] = {}
        self._checked = 0.0
        self._failed: dict[str, float] = {}  # url -> time of last failed fetch

    # ---------- catalog ----------
    def _load_catalog(self) -> None:
        stale = (not self.catalog_file.exists()
                 or time.time() - self.catalog_file.stat().st_mtime > self.refresh_s)
        if stale:
            try:
                req = urllib.request.Request(CATALOG_URL, headers=UA)
                with urllib.request.urlopen(req, timeout=30) as r:
                    raw = r.read()
                data = json.loads(raw)
                if not data.get("airlines"):
                    raise ValueError("empty catalog")
                self.catalog_file.parent.mkdir(parents=True, exist_ok=True)
                self.catalog_file.write_bytes(raw)
            except Exception as e:  # noqa: BLE001 — logos are optional
                print(f"logos: catalog download failed ({e})", flush=True)
                if self.catalog_file.exists():
                    self.catalog_file.touch()  # retry next period, not every request
        if not self.catalog_file.exists():
            return
        data = json.loads(self.catalog_file.read_text())
        self.version = data.get("version")
        # Several entries can share an ICAO code (e.g. QTR = Qatar Airways and
        # Qatar Airways Cargo). Prefer the main, active, passenger brand.
        def rank(a):
            return (bool(a.get("cargo")), bool(a.get("defunct")), bool(a.get("parent")))

        self.by_icao = {}
        for a in data.get("airlines", []):
            code = (a.get("icao") or "").upper()
            if code and (code not in self.by_icao or rank(a) < rank(self.by_icao[code])):
                self.by_icao[code] = a

    def _ensure(self) -> None:
        with self.lock:
            if time.time() - self._checked > 3600:
                self._checked = time.time()
                self._load_catalog()

    def _lookup(self, icao: str) -> tuple[dict | None, bool]:
        icao = icao.upper()
        if icao in self.by_icao:
            return self.by_icao[icao], False
        parent = BRAND_ALIASES.get(icao)
        return (self.by_icao.get(parent), True) if parent else (None, False)

    def info(self, icao: str | None) -> dict | None:
        """Compact airline info for the API, or None if not in the catalog."""
        if not icao:
            return None
        self._ensure()
        a, via_parent = self._lookup(icao)
        if not a:
            return None
        assets = a.get("assets", {})
        return {
            "name": None if via_parent else a.get("name"),
            "parent": a.get("name") if via_parent else None,
            "alliance": a.get("alliance"),
            "color": (a.get("branding") or {}).get("primary_color"),
            "icon": bool((assets.get("icon") or {}).get("color")),
            "logo": bool((assets.get("logo") or {}).get("color")),
            "page": (a.get("links") or {}).get("page"),
        }

    # ---------- SVG files ----------
    def svg(self, icao: str, variant: str) -> bytes | None:
        icao = icao.upper()
        if not ICAO.match(icao) or variant not in VARIANTS:
            return None
        self._ensure()
        a, _ = self._lookup(icao)
        if not a or not self.version:
            return None
        slug = a["slug"]
        if not re.fullmatch(r"[a-z0-9-]+", slug):
            return None
        path = self.dir / self.version / slug / f"{variant}.svg"
        if path.exists():
            return path.read_bytes()
        for tpl in (IMAGE_API, CDN):
            url = tpl.format(version=self.version, slug=slug, variant=variant)
            body = self._fetch_svg(url)
            if body:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(body)
                return body
        return None

    def _fetch_svg(self, url: str) -> bytes | None:
        if time.time() - self._failed.get(url, 0) < 86400:
            return None
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=20) as r:
                body = r.read(512 * 1024 + 1)
            if len(body) > 512 * 1024 or b"<svg" not in body[:2048]:
                raise ValueError("not an SVG")
            return body
        except Exception:  # noqa: BLE001 — logos are optional
            self._failed[url] = time.time()
            return None
