import requests

from app.services.address_cache import get_cached_search, set_cached_search

def reverse_geocode(lat: float, lng: float) -> dict:
    response = requests.get(
        "https://nominatim.openstreetmap.org/reverse",
        params={
            "lat": lat,
            "lon": lng,
            "format": "json"
        },
        headers={
            "User-Agent": "lvovo-app/1.0 (admin@lvovo.app)"
        },
        timeout=5
    )
    response.raise_for_status()
    return response.json()

def forward_geocode(address: str) -> list:
    cached = get_cached_search(address)
    if cached:
        return cached

    response = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={
            "q": address,
            "format": "json",
            "addressdetails": 1,
            "limit": 5
        },
        headers={
            "User-Agent": "lvovo-app/1.0 (admin@lvovo.app)"
        },
        timeout=5
    )
    response.raise_for_status()
    results = response.json()
    set_cached_search(address, results)
    return results
