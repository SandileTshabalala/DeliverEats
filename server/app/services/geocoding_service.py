"""
Addresses <-> coordinates, using OpenStreetMap's public Nominatim service.

Nominatim is free but has a usage policy (operations.osmfoundation.org/policies/nominatim):
  * at most 1 request per second, for the whole app
  * identify the app with real contact details
  * keep (cache) the results instead of asking again
This module does all three. The 1-per-second slot lives in Redis so every API
worker shares it. If the slot is not free within MAX_WAIT_SECONDS, or Nominatim
is slow or down, GeocodingUnavailable is raised: callers carry on without a
street name (an order only needs the coordinates).
"""
import json
import logging
import time
from typing import Optional

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 4
MAX_WAIT_SECONDS = 2.0
SLOT_MS = 1100                      # a little over 1 s, to stay safely under the limit
REVERSE_TTL = 30 * 24 * 3600        # a street does not move
SEARCH_TTL = 7 * 24 * 3600
_SLOT_KEY = "lvovo:geocode:slot"


class GeocodingUnavailable(Exception):
    """Nominatim could not be asked right now (busy, slow or down)."""


def _user_agent() -> str:
    """Nominatim requires a real way to contact us. Uses the support email from admin settings."""
    contact = settings.GEOCODER_CONTACT_EMAIL
    if not contact:
        try:
            from app.services import business
            contact = business.current().get("support_email")
        except Exception:
            contact = None
    name = settings.APP_NAME.replace(" ", "")
    return f"{name}/1.0 ({contact or settings.FRONTEND_URL})"


def _redis():
    from app.core.redis import redis_client
    return redis_client


def _wait_for_slot() -> None:
    """Take the app-wide 'one request per second' slot, waiting briefly if someone else has it."""
    deadline = time.monotonic() + MAX_WAIT_SECONDS
    while True:
        try:
            if _redis().set(_SLOT_KEY, "1", nx=True, px=SLOT_MS):
                return
        except Exception:
            # Redis is down: better one extra request than no addresses at all
            logger.warning("geocoding: Redis unavailable, skipping the shared rate limit")
            return
        if time.monotonic() >= deadline:
            raise GeocodingUnavailable("busy")
        time.sleep(0.1)


def _cache_get(key: str):
    try:
        data = _redis().get(key)
        return json.loads(data) if data else None
    except Exception:
        return None


def _cache_set(key: str, value, ttl: int) -> None:
    try:
        _redis().set(key, json.dumps(value), ex=ttl)
    except Exception:
        pass


def _http_get(url: str, **kwargs):
    return requests.get(url, **kwargs)


def _ask(path: str, params: dict):
    _wait_for_slot()
    try:
        response = _http_get(
            f"{settings.GEOCODER_URL.rstrip('/')}/{path}",
            params={**params, "format": "json"},
            headers={"User-Agent": _user_agent(), "Accept-Language": "en"},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as error:
        logger.warning("geocoding: %s failed: %s", path, error)
        raise GeocodingUnavailable(str(error)) from error


def reverse_key(lat: float, lng: float) -> str:
    # 4 decimals is about 11 m: close enough to share a street name, never a neighbour's suburb
    return f"lvovo:geo:rev:{round(lat, 4):.4f}:{round(lng, 4):.4f}"


def reverse_geocode(lat: float, lng: float) -> dict:
    """Street address for a point. Raises GeocodingUnavailable."""
    key = reverse_key(lat, lng)
    cached = _cache_get(key)
    if cached is not None:
        return cached
    result = _ask("reverse", {"lat": lat, "lon": lng})
    if isinstance(result, dict) and not result.get("error"):
        _cache_set(key, result, REVERSE_TTL)
    return result


def forward_geocode(address: str) -> list:
    """Places matching typed text (up to 5). Raises GeocodingUnavailable."""
    query = " ".join(address.lower().split())
    if len(query) < 3:
        return []
    key = f"lvovo:geo:search:{query}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    result = _ask("search", {"q": query, "addressdetails": 1, "limit": 5, "countrycodes": settings.GEOCODER_COUNTRY})
    results = result if isinstance(result, list) else []
    _cache_set(key, results, SEARCH_TTL)
    return results


def describe(lat: float, lng: float) -> dict:
    """
    What to store for a saved address. Never fails: when Nominatim cannot be
    asked, the pin is saved with a plain description and no suburb/city.
    """
    try:
        geo = reverse_geocode(lat, lng)
    except GeocodingUnavailable:
        geo = {}
    parts = geo.get("address") or {}
    return {
        "formatted_address": geo.get("display_name") or f"Pinned location ({lat:.5f}, {lng:.5f})",
        "suburb": parts.get("suburb") or parts.get("township") or parts.get("neighbourhood") or parts.get("village"),
        "city": parts.get("city") or parts.get("town") or parts.get("municipality"),
    }


def search_or_none(address: str) -> Optional[list]:
    try:
        return forward_geocode(address)
    except GeocodingUnavailable:
        return None
