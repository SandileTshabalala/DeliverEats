"""
Delivery fees, set by each restaurant (it uses its own drivers and keeps the fee).

    fee = base_fee + per_km_fee x distance from the shop to the customer

- per_km_fee = 0 gives a simple flat fee.
- free_delivery_over: orders with a food subtotal at or above this pay no fee.
- max_distance_km: customers further away cannot order for delivery.

Distance needs the shop's location (set on the settings screen) and the
customer's saved address. If either is missing, only the base fee is charged.
A restaurant that never saved settings charges the platform default
(DELIVERY_FEE in the environment).
"""
from decimal import ROUND_HALF_UP, Decimal
from math import asin, cos, radians, sin, sqrt
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.restaurant_delivery_settings import RestaurantDeliverySettings

CENT = Decimal("0.01")
# Roads are longer than a straight line. 1.3 is a common rule of thumb for
# turning straight-line distance into approximate driving distance in towns.
ROAD_FACTOR = Decimal("1.3")


def straight_line_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    lat1, lng1, lat2, lng2 = map(radians, (lat1, lng1, lat2, lng2))
    a = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lng2 - lng1) / 2) ** 2
    return 2 * asin(sqrt(a)) * 6371


def get_settings(db: Session, restaurant_id: str) -> RestaurantDeliverySettings:
    """Saved settings, or unsaved defaults for a restaurant that never set any."""
    row = db.query(RestaurantDeliverySettings).filter(
        RestaurantDeliverySettings.restaurant_id == restaurant_id
    ).first()
    if row:
        return row
    return RestaurantDeliverySettings(
        restaurant_id=restaurant_id,
        base_fee=Decimal(str(settings.DELIVERY_FEE)),
        per_km_fee=Decimal("0"),
    )


def serialize(row: RestaurantDeliverySettings) -> dict:
    return {
        "base_fee": Decimal(row.base_fee or 0),
        "per_km_fee": Decimal(row.per_km_fee or 0),
        "free_delivery_over": row.free_delivery_over,
        "max_distance_km": row.max_distance_km,
        "latitude": row.latitude,
        "longitude": row.longitude,
    }


def update_settings(db: Session, restaurant_id: str, data: dict) -> RestaurantDeliverySettings:
    row = get_settings(db, restaurant_id)
    for field in ("base_fee", "per_km_fee", "free_delivery_over", "max_distance_km", "latitude", "longitude"):
        if field in data:
            setattr(row, field, data[field])
    if row.base_fee is None:
        row.base_fee = Decimal("0")
    if row.per_km_fee is None:
        row.per_km_fee = Decimal("0")

    if (row.latitude is None) != (row.longitude is None):
        raise HTTPException(status_code=400, detail="Set both latitude and longitude for your shop, or neither")
    needs_location = Decimal(row.per_km_fee) > 0 or row.max_distance_km is not None
    if needs_location and row.latitude is None:
        raise HTTPException(
            status_code=400,
            detail="Set your shop's location first: it is needed to charge per kilometre or to limit the delivery distance"
        )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def quote(db: Session, restaurant_id: str, subtotal: Decimal,
          customer_lat: Optional[float], customer_lng: Optional[float]) -> dict:
    """
    Delivery fee for one order. Raises 400 if the customer is outside the
    restaurant's delivery area.
    """
    row = get_settings(db, restaurant_id)
    base = Decimal(row.base_fee or 0)
    per_km = Decimal(row.per_km_fee or 0)

    distance_km = None
    if None not in (row.latitude, row.longitude, customer_lat, customer_lng):
        straight = Decimal(str(straight_line_km(row.latitude, row.longitude, customer_lat, customer_lng)))
        distance_km = (straight * ROAD_FACTOR).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)

    if row.max_distance_km is not None and distance_km is not None and distance_km > Decimal(str(row.max_distance_km)):
        raise HTTPException(
            status_code=400,
            detail=f"Sorry, this restaurant only delivers within {row.max_distance_km:g} km and your address is about {distance_km} km away"
        )

    free = row.free_delivery_over is not None and subtotal >= Decimal(row.free_delivery_over)
    if free:
        fee = Decimal("0")
    else:
        fee = base + (per_km * distance_km if distance_km is not None else Decimal("0"))
        # whole rands: easier for cash at the door
        fee = fee.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    return {
        "delivery_fee": fee.quantize(CENT),
        "distance_km": float(distance_km) if distance_km is not None else None,
        "free_delivery": free,
        "free_delivery_over": row.free_delivery_over,
    }
