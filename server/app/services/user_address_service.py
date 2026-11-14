from app.models.user_address import UserAddress
from app.services.geocoding_service import describe
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.core.redis import get_async_redis

def create_user_address(db: Session, user_id: str, payload):
    # street name if OpenStreetMap can tell us; the pin is saved either way
    place = describe(payload.latitude, payload.longitude)

    if payload.is_default:
        db.query(UserAddress).filter(
            UserAddress.user_id == user_id
        ).update({"is_default": False})

    address = UserAddress(
        user_id=user_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        formatted_address=place["formatted_address"],
        suburb=place["suburb"],
        city=place["city"],
        instructions=payload.instructions,
        is_default=payload.is_default
    )

    db.add(address)
    db.commit()
    db.refresh(address)

    # Invalidate user profile cache asynchronously (fire and forget is okay here or just call it)
    import asyncio
    async def invalidate():
        redis = await get_async_redis()
        await redis.delete(f"lvovo:user_profile:{user_id}")
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(invalidate())
    except Exception:
        pass

    return address

def update_user_address(db: Session, user_id: str, address_id: str, payload):
    address = db.query(UserAddress).filter(
        UserAddress.id == address_id,
        UserAddress.user_id == user_id
    ).first()

    if not address:
        raise HTTPException(status_code=404, detail="Address not found")

    if payload.is_default:
        db.query(UserAddress).filter(
            UserAddress.user_id == user_id
        ).update({"is_default": False})

    if payload.latitude and payload.longitude:
        place = describe(payload.latitude, payload.longitude)

        address.latitude = payload.latitude
        address.longitude = payload.longitude
        address.formatted_address = place["formatted_address"]
        address.suburb = place["suburb"]
        address.city = place["city"]

    if payload.instructions is not None:
        address.instructions = payload.instructions
    
    if payload.is_default is not None:
        address.is_default = payload.is_default

    db.commit()
    db.refresh(address)

    # Invalidate user profile cache
    import asyncio
    async def invalidate():
        redis = await get_async_redis()
        await redis.delete(f"lvovo:user_profile:{user_id}")
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(invalidate())
    except Exception:
        pass

    return address

def delete_user_address(db: Session, user_id: str, address_id: str):
    address = db.query(UserAddress).filter(
        UserAddress.id == address_id,
        UserAddress.user_id == user_id
    ).first()

    if not address:
        raise HTTPException(status_code=404, detail="Address not found")

    db.delete(address)
    db.commit()

    # Invalidate user profile cache
    import asyncio
    async def invalidate():
        redis = await get_async_redis()
        await redis.delete(f"lvovo:user_profile:{user_id}")
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(invalidate())
    except Exception:
        pass

    return True
