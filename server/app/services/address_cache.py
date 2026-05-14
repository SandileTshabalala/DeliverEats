import json
from app.core.redis import redis_client

def get_cached_geo(lat, lng):
    key = f"geo:{lat}:{lng}"
    data = redis_client.get(key)
    return json.loads(data) if data else None

def set_cached_geo(lat, lng, geo):
    key = f"geo:{lat}:{lng}"
    redis_client.setex(key, 86400, json.dumps(geo))  # 24 hours

def get_cached_search(query: str):
    key = f"search:{query.lower().strip()}"
    data = redis_client.get(key)
    return json.loads(data) if data else None

def set_cached_search(query: str, results: list):
    key = f"search:{query.lower().strip()}"
    redis_client.setex(key, 3600, json.dumps(results))  # 1 hour
