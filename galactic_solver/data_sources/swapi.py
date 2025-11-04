from __future__ import annotations
import httpx
import os
from decimal import Decimal
from typing import Optional, Dict, Any
from ..utils import cache_get, cache_set, parse_decimal

BASE_URLS = [
    os.getenv("SWAPI_BASE_URL", "https://swapi.dev/api").rstrip("/"),
    "https://swapi.py4e.com/api",
]
HTTP_TIMEOUT = 8.0

client = httpx.Client(timeout=HTTP_TIMEOUT)


def _search(endpoint: str, name: str) -> Optional[Dict[str, Any]]:
    key = f"swapi:{endpoint}:{name.lower()}"
    cached = cache_get(key)
    if cached is not None:
        return cached  # type: ignore
    # Try multiple SWAPI base URLs (primary and mirror)
    for base in BASE_URLS:
        try:
            resp = client.get(f"{base}/{endpoint}", params={"search": name})
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            # Choose exact name match if available; otherwise first result
            item = None
            for r in results:
                if r.get("name", "").lower() == name.lower():
                    item = r
                    break
            if item is None and results:
                item = results[0]
            cache_set(key, item)
            return item
        except Exception:
            # try next base URL
            continue
    # Cache miss as None to avoid repeated failing lookups
    cache_set(key, None)
    return None


def _normalize_number(v) -> Optional[Decimal]:
    return parse_decimal(v)


def get_planet(name: str) -> Optional[Dict[str, Any]]:
    p = _search("planets/", name)
    if not p:
        return None
    return {
        "name": p.get("name"),
        "rotation_period": _normalize_number(p.get("rotation_period")),
        "orbital_period": _normalize_number(p.get("orbital_period")),
        "diameter": _normalize_number(p.get("diameter")),
        "surface_water": _normalize_number(p.get("surface_water")),
        "population": _normalize_number(p.get("population")),
    }


def _resolve_homeworld_name(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    key = f"swapi:planet-url:{url}"
    cached = cache_get(key)
    if cached is not None:
        return cached  # type: ignore
    try:
        resp = client.get(url)
        resp.raise_for_status()
        name = resp.json().get("name")
        if isinstance(name, str):
            cache_set(key, name)
            return name
        return None
    except Exception:
        return None


def get_character(name: str) -> Optional[Dict[str, Any]]:
    c = _search("people/", name)
    if not c:
        return None
    homeworld_name = _resolve_homeworld_name(c.get("homeworld"))
    return {
        "name": c.get("name"),
        "height": _normalize_number(c.get("height")),
        "mass": _normalize_number(c.get("mass")),
        "homeworld": homeworld_name,
    }
