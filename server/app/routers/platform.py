"""
Platform owner's view: real numbers for the dashboard, the list of restaurants,
and the state of the platform's own configuration. Plus the two public counters
shown on the landing page.

The owner sees how the platform is doing (counts and totals), not the contents
of individual restaurants' orders: those belong to the restaurants.
"""
from datetime import timedelta
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_db, require_role
from app.core.roles import Role
from app.models.order import Order
from app.models.restaurant import Restaurant
from app.models.subscription import RestaurantSubscription, SubscriptionPayment, utcnow
from app.models.user import User
from app.services import messaging
from app.services import subscription_service as subs
from app.utils.OrderStatus import OrderStatus

router = APIRouter(tags=["Platform"])

admin_only = require_role(Role.SUPER_ADMIN)


def _invalidate_restaurant_cache(restaurant_id: str) -> None:
    try:
        from app.core.redis import redis_client
        redis_client.delete("lvovo:restaurants:list", f"lvovo:restaurant:{restaurant_id}")
    except Exception:
        pass


# --------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------
@router.get("/admin/stats")
def admin_stats(db: Session = Depends(get_db), admin=Depends(admin_only)):
    now = utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today.replace(day=1)
    week_start = today - timedelta(days=6)

    restaurants = db.query(Restaurant).all()
    live = sum(1 for restaurant in restaurants if subs.is_restaurant_live(db, restaurant))

    by_status = {}
    monthly_recurring = Decimal("0")
    for subscription in db.query(RestaurantSubscription).all():
        status = subs.effective_status(subscription, now)
        by_status[status] = by_status.get(status, 0) + 1
        if status in ("active", "past_due") and subscription.plan:
            monthly_recurring += Decimal(subscription.plan.price) / subscription.plan.interval_months
    by_status["none"] = len(restaurants) - sum(by_status.values())

    def income_since(moment) -> Decimal:
        return db.query(func.coalesce(func.sum(SubscriptionPayment.amount), 0)).filter(
            SubscriptionPayment.status == "completed", SubscriptionPayment.created_at >= moment
        ).scalar() or Decimal("0")

    # Orders of the last 7 days, bucketed per day in Python (works on any database)
    recent = db.query(Order.created_at, Order.status).filter(Order.created_at >= week_start).all()
    days = []
    for offset in range(7):
        day = week_start + timedelta(days=offset)
        days.append({
            "date": day.date().isoformat(),
            "orders": sum(1 for created, status in recent
                          if created and day <= created < day + timedelta(days=1) and status != OrderStatus.CANCELLED),
        })

    def users_with(role: Role) -> int:
        return db.query(User).filter(User.role == role, User.is_active == True).count()

    return {
        "restaurants": {"total": len(restaurants), "live": live},
        "customers": users_with(Role.CUSTOMER),
        "drivers": users_with(Role.DRIVER),
        "orders": {
            "today": sum(1 for created, status in recent if created and created >= today and status != OrderStatus.CANCELLED),
            "this_month": db.query(Order).filter(Order.created_at >= month_start, Order.status != OrderStatus.CANCELLED).count(),
            "all_time": db.query(Order).filter(Order.status != OrderStatus.CANCELLED).count(),
            "last_7_days": days,
        },
        # The platform's own income: subscription payments from restaurants
        "subscription_income": {
            "this_month": income_since(month_start),
            "all_time": income_since(now - timedelta(days=365 * 50)),
            "monthly_recurring": monthly_recurring.quantize(Decimal("0.01")),
        },
        "subscriptions": by_status,
        "subscriptions_enforced": settings.SUBSCRIPTIONS_ENFORCED,
    }


# --------------------------------------------------------------------------
# Restaurants
# --------------------------------------------------------------------------
class AdminRestaurantUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    address: Optional[str] = Field(default=None, min_length=1, max_length=300)
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = None

    class Config:
        extra = "forbid"


def _restaurant_row(db: Session, restaurant: Restaurant, month_start) -> dict:
    owner = restaurant.admin
    subscription = subs.describe(db, restaurant)
    return {
        "id": restaurant.id,
        "name": restaurant.name,
        "address": restaurant.address,
        "description": restaurant.description,
        "logo_img_url": restaurant.logo_img_url,
        "is_active": bool(restaurant.is_active),
        "is_live": subscription["is_live"],
        "owner_name": f"{owner.name} {owner.sur_name}" if owner else None,
        "owner_email": owner.email if owner else None,
        "owner_phone": owner.contact_number if owner else None,
        "subscription_status": subscription["status"],
        "plan_name": subscription["plan"].name if subscription["plan"] else None,
        "paid_until": subscription["current_period_end"],
        "orders_this_month": subscription["orders_this_month"],
    }


@router.get("/admin/restaurants")
def admin_list_restaurants(db: Session = Depends(get_db), admin=Depends(admin_only)) -> List[dict]:
    month_start = utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return [
        _restaurant_row(db, restaurant, month_start)
        for restaurant in db.query(Restaurant).order_by(Restaurant.name.asc()).all()
    ]


@router.patch("/admin/restaurants/{restaurant_id}")
def admin_update_restaurant(
    restaurant_id: str,
    payload: AdminRestaurantUpdate,
    db: Session = Depends(get_db),
    admin=Depends(admin_only),
) -> dict:
    """Edit a restaurant's details, or close / reopen it (is_active)."""
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(restaurant, key, value)
    db.commit()
    db.refresh(restaurant)
    _invalidate_restaurant_cache(restaurant.id)
    return _restaurant_row(db, restaurant, utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0))


# --------------------------------------------------------------------------
# Platform configuration status (read-only: values come from the environment)
# --------------------------------------------------------------------------
@router.get("/admin/system")
def admin_system(admin=Depends(admin_only)):
    """What is switched on. Never returns a key or secret, only whether it is set."""
    return {
        "environment": settings.ENV,
        "app_name": settings.APP_NAME,
        "frontend_url": settings.FRONTEND_URL,
        "public_api_url": settings.PUBLIC_API_URL,
        "sms": {"configured": messaging.sms_configured(), "sandbox": settings.AT_SANDBOX, "sender_id": settings.AT_SENDER_ID},
        "email": {"configured": messaging.email_configured(), "from": settings.EMAIL_FROM},
        "payfast": {
            "configured": subs.platform_payfast_credentials() is not None,
            "sandbox": settings.PAYFAST_SANDBOX,
        },
        "subscriptions": {"enforced": settings.SUBSCRIPTIONS_ENFORCED, "grace_days": settings.SUBSCRIPTION_GRACE_DAYS},
        "default_delivery_fee": settings.DELIVERY_FEE,
        "secrets_encryption_key_set": bool(settings.ENCRYPTION_KEY),
    }


# --------------------------------------------------------------------------
# Public counters for the landing and sign-up pages (real numbers, cached)
# --------------------------------------------------------------------------
@router.get("/stats/public")
async def public_stats(db: Session = Depends(get_db)):
    from starlette.concurrency import run_in_threadpool

    from app.core.cache import get_cache, set_cache

    cached = await get_cache("stats:public")
    if cached:
        return cached

    def count():
        restaurants = [r for r in db.query(Restaurant).filter(Restaurant.is_active == True).all()
                       if subs.is_restaurant_live(db, r)]
        return {
            "restaurants": len(restaurants),
            "orders_delivered": db.query(Order).filter(Order.status == OrderStatus.DELIVERED).count(),
        }

    data = await run_in_threadpool(count)
    await set_cache("stats:public", data, ttl=300)
    return data
