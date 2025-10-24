from __future__ import annotations
from decimal import Decimal
from typing import Optional, Union
import re
import os

# Simple in-memory cache
_CACHE: dict[str, object] = {}

def cache_get(key: str):
    return _CACHE.get(key)

def cache_set(key: str, value: object):
    _CACHE[key] = value

_NUM_RE = re.compile(r"[^0-9\.-]")

def parse_decimal(value: Union[str, int, float, Decimal, None]) -> Optional[Decimal]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        try:
            return Decimal(str(value))
        except Exception:
            return None
    s = str(value).strip().lower()
    if s in ("unknown", "n/a", "none", "null", "-"):
        return None
    s = _NUM_RE.sub("", s)
    if s == "" or s == "." or s == "-" or s == "-.":
        return None
    try:
        return Decimal(s)
    except Exception:
        return None

def get_env_token() -> Optional[str]:
    # Try to load from environment; .env handled in app startup
    token = os.getenv("CHALLENGE_TOKEN")
    return token

