from sqlalchemy.orm import Session
from app.core.cache import get_cache, set_cache
from app.models.restaurant import Restaurant
from app.schemas.restaurant import RestaurantCreate
from app.services.subscription_service import is_restaurant_live
from app.services import categories as cats, restaurant_info

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
    if not r or not is_restaurant_live(db, r):
        return None
    return restaurant_info.public_dict(r, restaurant_info.ratings(db, r.id).get(r.id),
                                      restaurant_info.delivery_terms(db, [r.id]).get(r.id),
                                      cats.names_by_restaurant(db, [r.id]).get(r.id))

def create_restaurant(db: Session, payload: RestaurantCreate):
    restaurant = Restaurant(**payload.model_dump())  # ✅ Pydantic v2
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    return restaurant

def fetch_from_db(db: Session):
    restaurants = db.query(Restaurant).filter(Restaurant.is_active == True).all()
    scores = restaurant_info.ratings(db)  # one query for every restaurant
    fees = restaurant_info.delivery_terms(db)
    kinds = cats.names_by_restaurant(db)
    listed = [
        restaurant_info.public_dict(r, scores.get(r.id), fees.get(r.id), kinds.get(r.id))
        for r in restaurants
        if is_restaurant_live(db, r)  # hidden while the subscription is suspended / expired
    ]
    # open kitchens first, then best rated
    listed.sort(key=lambda r: (not r["is_open"], -(r["rating"] or 0), r["name"].lower()))
    return listed

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
