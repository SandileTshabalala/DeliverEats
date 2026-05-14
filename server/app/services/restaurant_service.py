from sqlalchemy.orm import Session
from app.core.cache import get_cache, set_cache
from app.models.restaurant import Restaurant
from app.schemas.restaurant import RestaurantCreate

async def get_restaurant(db: Session, restaurant_id: str):
    key = f"restaurant:{restaurant_id}"
    cached = await get_cache(key)
    if cached:
        return cached
    from starlette.concurrency import run_in_threadpool
    data = await run_in_threadpool(get_restaurant_by_id, db, restaurant_id)
    if data:
        await set_cache(key, data, ttl=CACHE_TTL)
    return data

CACHE_TTL = 60  # seconds

def get_restaurant_by_id(db: Session, restaurant_id: str):
    r = db.query(Restaurant).filter(Restaurant.id == restaurant_id, Restaurant.is_active == True).first()
    if not r:
        return None
    return {
        "id": r.id,
        "name": r.name,
        "description": r.description,
        "address": r.address,
        "is_active": r.is_active,
        "logo_img_url": r.logo_img_url,
    }

def create_restaurant(db: Session, payload: RestaurantCreate):
    restaurant = Restaurant(**payload.model_dump())  # ✅ Pydantic v2
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    return restaurant

def fetch_from_db(db: Session):
    restaurants = db.query(Restaurant).filter(Restaurant.is_active == True).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "address": r.address,
            "is_active": r.is_active,
            "logo_img_url": r.logo_img_url,
        }
        for r in restaurants
    ]

async def get_restaurants(db: Session):
    key = "restaurants:list"

    cached = await get_cache(key)
    if cached:
        return cached

    # Run blocking DB call in threadpool
    from starlette.concurrency import run_in_threadpool
    data = await run_in_threadpool(fetch_from_db, db)
    await set_cache(key, data, ttl=CACHE_TTL)

    return data
