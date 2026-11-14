"""
Things customers see about a restaurant beyond its name: category, whether it
is open right now, and its rating.
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.order_review import OrderReview
from app.models.restaurant import Restaurant



def local_now() -> datetime:
    """Wall-clock time where the restaurants are (South Africa is UTC+2 all year)."""
    return datetime.now(timezone.utc) + timedelta(hours=settings.LOCAL_UTC_OFFSET_HOURS)


def _minutes(clock: Optional[str]) -> Optional[int]:
    try:
        hours, minutes = (clock or "").split(":")
        value = int(hours) * 60 + int(minutes)
        return value if 0 <= value < 24 * 60 else None
    except ValueError:
        return None


def clock(value: Optional[str]) -> str:
    """ "22:00" -> "10:00 PM" (hours are stored 24-hour; people read 12-hour)."""
    minutes = _minutes(value)
    if minutes is None:
        return value or ""
    hours, mins = divmod(minutes, 60)
    return f"{hours % 12 or 12}:{mins:02d} {'AM' if hours < 12 else 'PM'}"


def is_open_now(restaurant: Restaurant, now: Optional[datetime] = None) -> bool:
    """
    Open = the owner's switch is on AND (no hours set, or we are inside them).
    Hours that run past midnight (18:00 to 02:00) are handled.
    """
    if restaurant.accepting_orders is False:
        return False
    opens, closes = _minutes(restaurant.opens_at), _minutes(restaurant.closes_at)
    if opens is None or closes is None or opens == closes:
        return True
    current = (now or local_now())
    minute = current.hour * 60 + current.minute
    if opens < closes:
        return opens <= minute < closes
    return minute >= opens or minute < closes


def ratings(db: Session, restaurant_id: Optional[str] = None) -> Dict[str, Tuple[float, int]]:
    """restaurant_id -> (average out of 5, number of reviews)"""
    query = db.query(OrderReview.restaurant_id, func.avg(OrderReview.rating), func.count(OrderReview.id))
    if restaurant_id:
        query = query.filter(OrderReview.restaurant_id == restaurant_id)
    return {
        rid: (round(float(average), 1), int(count))
        for rid, average, count in query.group_by(OrderReview.restaurant_id).all()
    }


def delivery_terms(db: Session, restaurant_ids=None) -> Dict[str, dict]:
    """restaurant_id -> what its delivery costs, for the restaurant cards (one query)."""
    from decimal import Decimal
    from app.models.restaurant_delivery_settings import RestaurantDeliverySettings
    query = db.query(RestaurantDeliverySettings)
    if restaurant_ids is not None:
        query = query.filter(RestaurantDeliverySettings.restaurant_id.in_(list(restaurant_ids)))
    return {
        row.restaurant_id: {
            "delivery_fee_from": Decimal(row.base_fee or 0),
            "delivery_per_km": Decimal(row.per_km_fee or 0) > 0,
            "free_delivery_over": row.free_delivery_over,
        }
        for row in query.all()
    }


def public_dict(restaurant: Restaurant, rating: Optional[Tuple[float, int]] = None, delivery: Optional[dict] = None,
                categories: Optional[list] = None) -> dict:
    from decimal import Decimal
    average, count = rating or (None, 0)
    # restaurants that never set a fee charge the platform default
    delivery = delivery or {"delivery_fee_from": Decimal(str(settings.DELIVERY_FEE)), "delivery_per_km": False, "free_delivery_over": None}
    return {
        "id": restaurant.id,
        "name": restaurant.name,
        "description": restaurant.description,
        "address": restaurant.address,
        "is_active": restaurant.is_active,
        "logo_img_url": restaurant.logo_img_url,
        # main category first; managed by the platform owner (app.services.categories)
        "category": (categories or [None])[0],
        "categories": categories or [],
        "is_open": is_open_now(restaurant),
        "accepting_orders": restaurant.accepting_orders is not False,
        "opens_at": restaurant.opens_at,
        "closes_at": restaurant.closes_at,
        "rating": average,
        "review_count": count,
        **delivery,
    }
