from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models.driver import Driver
from app.models.order import Order
from app.core.redis import redis_client
from app.utils.OrderStatus import OrderStatus
from datetime import datetime, timezone

DRIVER_CACHE_KEY = "available_drivers"

def create_driver_profile(db: Session, user_id: str, vehicle_type: str, vehicle_number: str = None):
    """Create the driver's profile, or update it if it already exists."""
    driver = db.query(Driver).filter(Driver.id == user_id).first()
    if driver:
        driver.vehicle_type = vehicle_type
        if vehicle_number is not None:
            driver.vehicle_number = vehicle_number
    else:
        driver = Driver(id=user_id, vehicle_type=vehicle_type, vehicle_number=vehicle_number, is_available=True)
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
def restaurant_driver_filter(restaurant_id):
    """Drivers of this restaurant, plus legacy drivers that belong to nobody."""
    return or_(Driver.restaurant_id == restaurant_id, Driver.restaurant_id.is_(None))


def get_available_driver(db: Session, restaurant_id: str = None):
    """
    Select the fairest available driver:
    - Available
    - Least recently assigned
    - Row-locked to prevent double assignment
    """

    driver = (
        db.query(Driver)
        .filter(Driver.is_available == True, restaurant_driver_filter(restaurant_id))
        # the restaurant's own drivers first, then whoever has waited longest
        .order_by(Driver.restaurant_id.is_(None).asc(), Driver.last_assigned_at.asc().nullsfirst())
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
            on_driver_available(db, driver)
            
    return driver

def has_active_delivery(db: Session, driver_id: str) -> bool:
    return db.query(Order).filter(
        Order.driver_id == driver_id,
        Order.status.notin_([OrderStatus.DELIVERED, OrderStatus.CANCELLED])
    ).first() is not None


def update_driver_location(db: Session, driver_id: str, latitude: float, longitude: float):
    """Persist the driver's last known position so nearest-driver matching works."""
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if driver:
        driver.latitude = latitude
        driver.longitude = longitude
        db.commit()
    return driver


def get_driver_profile(db: Session, user_id: str):
    return db.query(Driver).filter(Driver.id == user_id).first()

def on_driver_available(db: Session, driver: Driver = None):
    # Import locally to avoid circular dependency
    from app.services.order_service import assign_driver
    
    # Oldest accepted order that still has no driver (the kitchen may have
    # carried on cooking while it waited, so it can already be READY).
    scope = []
    if driver is not None and driver.restaurant_id:
        # A restaurant's driver only ever delivers that restaurant's orders
        scope.append(Order.restaurant_id == driver.restaurant_id)

    order = db.query(Order).filter(
        *scope,
        Order.driver_id.is_(None),
        Order.status.in_([
            OrderStatus.WAITING_FOR_DRIVER,
            OrderStatus.ACCEPTED,
            OrderStatus.PREPARING,
            OrderStatus.READY,
        ])
    ).order_by(Order.driver_wait_started_at.asc().nullslast(), Order.created_at.asc()).first()

    if order:
        assign_driver(db, order.id)
        # assign_driver handles status update to PREPARING
        # But we can double check or log here
        pass
