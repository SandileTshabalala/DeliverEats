from sqlalchemy.orm import Session
from app.models.driver import Driver
from app.models.order import Order
from app.core.redis import redis_client
from app.utils.OrderStatus import OrderStatus
from datetime import datetime, timezone

DRIVER_CACHE_KEY = "available_drivers"

def create_driver_profile(db: Session, user_id: str, vehicle_type: str):
    driver = Driver(id=user_id, vehicle_type=vehicle_type, is_available=True)
    db.add(driver)
    db.commit()
    db.refresh(driver)

    # Update Redis cache
    redis_client.sadd(DRIVER_CACHE_KEY, driver.id)
    return driver


"""
Use DB-only version first
Switch to Redis ZSET later

Final recommendation (TL;DR)
Stage	Strategy
MVP	DB + locking
Growth	Redis ZSET
Scale	Geo-hash + ETA

Version 2 — Redis + DB (Uber-scale)

Use Redis Sorted Set:

Redis structure
drivers:available → ZSET
score = unix_timestamp_when_available
value = driver_id

Driver goes online
r.zadd("drivers:available", {driver_id: time.time()})

Get fair driver (atomic)
def get_available_driver():
    result = r.zpopmin("drivers:available")
    if not result:
        return None

    driver_id, _ = result[0]
    return driver_id


Then confirm in DB:

driver = db.query(Driver).filter(
    Driver.id == driver_id,
    Driver.is_available == True
).first()
"""
# def get_available_driver(db: Session):
#     """
#     Select the first available driver from Redis cache, fallback to DB
#     """
#     driver_id = redis_client.spop(DRIVER_CACHE_KEY)
#     if driver_id:
#         return db.query(Driver).filter(Driver.id == driver_id.decode()).first()

#     # fallback DB query
#     return db.query(Driver).filter(Driver.is_available == True).first()
def get_available_driver(db: Session):
    """
    Select the fairest available driver:
    - Available
    - Least recently assigned
    - Row-locked to prevent double assignment
    """

    driver = (
        db.query(Driver)
        .filter(Driver.is_available == True)
        .order_by(Driver.last_assigned_at.asc().nullsfirst())
        .with_for_update(skip_locked=True)
        .first()
    )

    if not driver:
        return None

    # Mark driver busy immediately
    driver.is_available = False
    driver.last_assigned_at = datetime.now(timezone.utc)

    db.flush()  # reserve driver before commit
    return driver

def set_driver_availability(db: Session, driver_id: str, available: bool):
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if driver:
        driver.is_available = available
        if available:
            # from datetime import datetime, timezone
            # driver.driver_wait_started_at = datetime.now(timezone.utc)
            redis_client.sadd(DRIVER_CACHE_KEY, driver.id)
        else:
            # driver.driver_wait_started_at = None
            redis_client.srem(DRIVER_CACHE_KEY, driver.id)
        
        db.commit()

        if available:
            # Trigger assignment for waiting orders
            on_driver_available(db)
            
    return driver

def get_driver_profile(db: Session, user_id: str):
    return db.query(Driver).filter(Driver.id == user_id).first()

def on_driver_available(db: Session):
    # Import locally to avoid circular dependency
    from app.services.order_service import assign_driver
    
    order = db.query(Order).filter(
        Order.status == OrderStatus.WAITING_FOR_DRIVER
    ).order_by(Order.driver_wait_started_at.asc()).first()

    if order:
        assign_driver(db, order.id)
        # assign_driver handles status update to PREPARING
        # But we can double check or log here
        pass
