"""
A restaurant managing ITSELF: how it gets paid, its subscription, its drivers
and its staff. Every endpoint is scoped by `get_current_restaurant`, so there is
no restaurant id in any URL and no way to reach another restaurant's data.
"""
from typing import List

from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_role
from app.core.roles import Role
from app.core.security import hash_password
from app.core.tenancy import get_current_restaurant, is_owner
from app.models.driver import Driver
from app.models.menu import Menu
from app.models.menu_item import MenuItem
from app.models.order import Order
from app.models.subscription import utcnow
from app.services import categories as cats, restaurant_info, uploads
from app.models.order_review import OrderReview
from app.utils.OrderStatus import OrderStatus
from app.models.refresh_tokens import RefreshToken
from app.models.restaurant import Restaurant
from app.models.restaurant_admin import RestaurantAdmin
from app.models.subscription import SubscriptionPayment
from app.models.user import User
from app.schemas.billing import (
    BillingOverview,
    DeliverySettingsRead,
    DeliverySettingsUpdate,
    DriverCreate,
    DriverTeamRead,
    PaymentSettingsRead,
    PaymentSettingsUpdate,
    SubscribeRequest,
    SubscribeResponse,
    SubscriptionPaymentRead,
    TeamMemberCreate,
    TeamMemberRead,
)
from app.services import delivery_fee
from app.services import restaurant_payment_service as pay_settings
from app.services import subscription_service as subs

router = APIRouter(prefix="/manage", tags=["Restaurant Management"])

restaurant_user = require_role(Role.RESTAURANT_ADMIN)


def owner_only(restaurant: Restaurant, user) -> None:
    if not is_owner(restaurant, user):
        raise HTTPException(status_code=403, detail="Only the restaurant owner can do this")


def _new_user(db: Session, payload: TeamMemberCreate, role: Role) -> User:
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="That email address is already registered")
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        sur_name=payload.sur_name,
        contact_number=payload.contact_number,
        role=role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _deactivate(db: Session, user: User) -> None:
    user.is_active = False
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id, RefreshToken.is_revoked == False
    ).update({"is_revoked": True})
    try:
        from app.core.redis import redis_client
        redis_client.delete(f"lvovo:user_profile:{user.id}")
    except Exception:
        pass


# ---------------- the restaurant's own profile and logo ----------------
class RestaurantProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    address: Optional[str] = Field(default=None, min_length=1, max_length=300)
    description: Optional[str] = Field(default=None, max_length=500)
    # main category first, up to cats.MAX_PER_RESTAURANT
    category_ids: Optional[List[str]] = None
    category: Optional[str] = None  # older screens: one category by name
    accepting_orders: Optional[bool] = None
    # "HH:MM" in local time; send both as null to be open whenever the switch is on
    opens_at: Optional[str] = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    closes_at: Optional[str] = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    # South African VAT numbers are 10 digits starting with 4
    vat_number: Optional[str] = Field(default=None, pattern=r"^4\d{9}$")
    # Number customers call to change or cancel an order; empty = the owner's number
    phone: Optional[str] = Field(default=None, max_length=20)

    class Config:
        extra = "forbid"


def _clean_phone(raw: Optional[str]) -> Optional[str]:
    """Empty = use the owner's number. Otherwise digits (spaces, dashes and a leading + allowed)."""
    import re
    value = re.sub(r"[\s\-()]", "", raw or "")
    if not value:
        return None
    if not re.fullmatch(r"\+?\d{9,15}", value):
        raise HTTPException(status_code=400, detail="Enter a phone number customers can call, for example 072 123 4567")
    return value


def _profile(restaurant: Restaurant, db: Session) -> dict:
    chosen, options = cats.for_owner(db, restaurant.id)
    return {
        "id": restaurant.id, "name": restaurant.name, "address": restaurant.address,
        "description": restaurant.description, "logo_img_url": restaurant.logo_img_url,
        "is_active": bool(restaurant.is_active),
        "category": restaurant.category,
        "accepting_orders": restaurant.accepting_orders is not False,
        "opens_at": restaurant.opens_at, "closes_at": restaurant.closes_at,
        "vat_number": restaurant.vat_number,
        "phone": restaurant.phone,
        "owner_phone": restaurant.admin.contact_number if restaurant.admin else None,
        "menu_sections": restaurant.menu_sections or [],
        "is_open": restaurant_info.is_open_now(restaurant),
        "category_ids": chosen,
        "category_options": options,
        "max_categories": cats.MAX_PER_RESTAURANT,
    }


def _refresh_public_listing(restaurant_id: str) -> None:
    """Customers see restaurants through a 60s cache: drop it so changes show at once."""
    try:
        from app.core.redis import redis_client
        redis_client.delete("lvovo:restaurants:list", f"lvovo:restaurant:{restaurant_id}", "lvovo:stats:public")
    except Exception:
        pass


@router.get("/restaurant")
def read_profile(db: Session = Depends(get_db), restaurant: Restaurant = Depends(get_current_restaurant)) -> dict:
    return _profile(restaurant, db)


@router.patch("/restaurant")
def update_profile(
    payload: RestaurantProfileUpdate,
    db: Session = Depends(get_db),
    restaurant: Restaurant = Depends(get_current_restaurant),
    user=Depends(restaurant_user),
) -> dict:
    changes = payload.model_dump(exclude_unset=True)
    # Staff may open and close the kitchen for the day; everything else is the owner's
    if set(changes) - {"accepting_orders"}:
        owner_only(restaurant, user)
    category_ids = changes.pop("category_ids", None)
    if "category" in changes:
        name = changes.pop("category")
        if category_ids is None:
            category_ids = [cats.id_for_name(db, name)] if name else []
    if category_ids is not None:
        cats.set_for_restaurant(db, restaurant, category_ids)
    for required in ("name", "address"):
        if required in changes and not changes[required]:
            raise HTTPException(status_code=400, detail=f"The {required} cannot be empty")
    if "phone" in changes:
        changes["phone"] = _clean_phone(changes["phone"])
    for key, value in changes.items():
        setattr(restaurant, key, value)
    if bool(restaurant.opens_at) != bool(restaurant.closes_at):
        raise HTTPException(status_code=400, detail="Set both an opening and a closing time, or neither")
    db.commit()
    db.refresh(restaurant)
    _refresh_public_listing(restaurant.id)
    return _profile(restaurant, db)


class MenuSectionOrder(BaseModel):
    sections: List[str] = Field(max_length=40)


@router.put("/menu-sections")
def order_menu_sections(
    payload: MenuSectionOrder,
    db: Session = Depends(get_db),
    restaurant: Restaurant = Depends(get_current_restaurant),
    user=Depends(restaurant_user),
) -> dict:
    """The order the menu sections appear in for customers ("Mains" before "Drinks")."""
    owner_only(restaurant, user)
    names = []
    for name in payload.sections:
        name = " ".join(name.split())[:40]
        if name and name.lower() not in {n.lower() for n in names}:
            names.append(name)
    restaurant.menu_sections = names
    db.commit()
    _refresh_public_listing(restaurant.id)
    return {"menu_sections": names}


@router.get("/reviews")
def restaurant_reviews(db: Session = Depends(get_db), restaurant: Restaurant = Depends(get_current_restaurant)) -> dict:
    """What customers said about this restaurant's orders (newest first)."""
    average, count = restaurant_info.ratings(db, restaurant.id).get(restaurant.id, (None, 0))
    rows = db.query(OrderReview, User).join(User, User.id == OrderReview.customer_id).filter(
        OrderReview.restaurant_id == restaurant.id
    ).order_by(OrderReview.created_at.desc()).limit(50).all()
    return {
        "rating": average,
        "review_count": count,
        "reviews": [
            {"id": review.id, "order_id": review.order_id, "rating": review.rating, "comment": review.comment,
             "created_at": review.created_at, "customer_name": customer.name}
            for review, customer in rows
        ],
    }


@router.post("/restaurant/logo")
async def upload_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    restaurant: Restaurant = Depends(get_current_restaurant),
    user=Depends(restaurant_user),
) -> dict:
    """Replace the restaurant's logo with an uploaded PNG, JPG or WebP image."""
    owner_only(restaurant, user)
    previous = restaurant.logo_img_url
    restaurant.logo_img_url = await uploads.save_logo(file, restaurant.id)
    db.commit()
    db.refresh(restaurant)
    uploads.delete_uploaded(previous)
    _refresh_public_listing(restaurant.id)
    return _profile(restaurant, db)


@router.delete("/restaurant/logo")
def remove_logo(
    db: Session = Depends(get_db),
    restaurant: Restaurant = Depends(get_current_restaurant),
    user=Depends(restaurant_user),
) -> dict:
    owner_only(restaurant, user)
    uploads.delete_uploaded(restaurant.logo_img_url)
    restaurant.logo_img_url = None
    db.commit()
    db.refresh(restaurant)
    _refresh_public_listing(restaurant.id)
    return _profile(restaurant, db)


@router.get("/stats")
def restaurant_stats(db: Session = Depends(get_db), restaurant: Restaurant = Depends(get_current_restaurant)) -> dict:
    """Real numbers for the restaurant's dashboard."""
    today = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today.replace(day=1)
    mine = Order.restaurant_id == restaurant.id

    def count(*conditions) -> int:
        return db.query(Order).filter(mine, *conditions).count()

    def sales(*conditions):
        # Money actually earned: orders that were delivered
        return db.query(func.coalesce(func.sum(Order.total_amount), 0)).filter(
            mine, Order.status == OrderStatus.DELIVERED, *conditions
        ).scalar() or 0

    not_cancelled = Order.status != OrderStatus.CANCELLED
    return {
        "orders_today": count(Order.created_at >= today, not_cancelled),
        "orders_this_month": count(Order.created_at >= month_start, not_cancelled),
        "sales_today": sales(Order.created_at >= today),
        "sales_this_month": sales(Order.created_at >= month_start),
        "open_orders": count(Order.status.notin_([OrderStatus.DELIVERED, OrderStatus.CANCELLED])),
        "menu_items_available": db.query(MenuItem).join(Menu, MenuItem.menu_id == Menu.id).filter(
            Menu.restaurant_id == restaurant.id, MenuItem.is_available == True
        ).count(),
    }


# ---------------- how the restaurant gets paid ----------------
@router.get("/payment-settings", response_model=PaymentSettingsRead)
def read_payment_settings(db: Session = Depends(get_db), restaurant: Restaurant = Depends(get_current_restaurant)):
    return pay_settings.serialize(pay_settings.get_settings(db, restaurant.id))


@router.put("/payment-settings", response_model=PaymentSettingsRead)
def save_payment_settings(
    payload: PaymentSettingsUpdate,
    db: Session = Depends(get_db),
    restaurant: Restaurant = Depends(get_current_restaurant),
    user=Depends(restaurant_user),
):
    owner_only(restaurant, user)
    row = pay_settings.update_settings(db, restaurant.id, payload.model_dump(exclude_unset=True))
    return pay_settings.serialize(row)


# ---------------- what the restaurant charges for delivery ----------------
@router.get("/delivery-settings", response_model=DeliverySettingsRead)
def read_delivery_settings(db: Session = Depends(get_db), restaurant: Restaurant = Depends(get_current_restaurant)):
    return delivery_fee.serialize(delivery_fee.get_settings(db, restaurant.id))


@router.put("/delivery-settings", response_model=DeliverySettingsRead)
def save_delivery_settings(
    payload: DeliverySettingsUpdate,
    db: Session = Depends(get_db),
    restaurant: Restaurant = Depends(get_current_restaurant),
    user=Depends(restaurant_user),
):
    """Fields left out keep their value; a field sent as null is cleared."""
    owner_only(restaurant, user)
    row = delivery_fee.update_settings(db, restaurant.id, payload.model_dump(exclude_unset=True))
    return delivery_fee.serialize(row)


# ---------------- subscription ----------------
@router.get("/billing", response_model=BillingOverview)
def billing_overview(db: Session = Depends(get_db), restaurant: Restaurant = Depends(get_current_restaurant)):
    return {
        "subscription": subs.describe(db, restaurant),
        "plans": subs.list_plans(db),
        "online_payment_available": subs.platform_payfast_credentials() is not None,
    }


@router.post("/billing/subscribe", response_model=SubscribeResponse)
def billing_subscribe(
    payload: SubscribeRequest,
    db: Session = Depends(get_db),
    restaurant: Restaurant = Depends(get_current_restaurant),
    user=Depends(restaurant_user),
):
    owner_only(restaurant, user)
    return subs.subscribe(db, restaurant, payload.plan_id, user)


@router.get("/billing/payments", response_model=List[SubscriptionPaymentRead])
def billing_history(db: Session = Depends(get_db), restaurant: Restaurant = Depends(get_current_restaurant)):
    return db.query(SubscriptionPayment).filter(
        SubscriptionPayment.restaurant_id == restaurant.id,
        SubscriptionPayment.status == "completed",
    ).order_by(SubscriptionPayment.created_at.desc()).limit(50).all()


# ---------------- drivers (each restaurant has its own) ----------------
def _driver_row(user: User, driver: Driver) -> dict:
    return {
        "id": user.id, "email": user.email, "name": user.name, "sur_name": user.sur_name,
        "contact_number": user.contact_number, "is_active": user.is_active, "is_owner": False,
        "vehicle_type": driver.vehicle_type, "vehicle_number": driver.vehicle_number,
        "is_available": bool(driver.is_available),
    }


@router.get("/drivers", response_model=List[DriverTeamRead])
def list_drivers(db: Session = Depends(get_db), restaurant: Restaurant = Depends(get_current_restaurant)):
    rows = db.query(User, Driver).join(Driver, Driver.id == User.id).filter(
        Driver.restaurant_id == restaurant.id
    ).order_by(User.name.asc()).all()
    return [_driver_row(user, driver) for user, driver in rows]


@router.post("/drivers", response_model=DriverTeamRead)
def add_driver(
    payload: DriverCreate,
    db: Session = Depends(get_db),
    restaurant: Restaurant = Depends(get_current_restaurant),
):
    user = _new_user(db, payload, Role.DRIVER)
    driver = Driver(
        id=user.id,
        restaurant_id=restaurant.id,
        vehicle_type=payload.vehicle_type,
        vehicle_number=payload.vehicle_number,
        is_available=True,
    )
    db.add(driver)
    db.commit()
    return _driver_row(user, driver)


@router.delete("/drivers/{driver_id}")
def remove_driver(driver_id: str, db: Session = Depends(get_db), restaurant: Restaurant = Depends(get_current_restaurant)):
    driver = db.query(Driver).filter(Driver.id == driver_id, Driver.restaurant_id == restaurant.id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    driver.is_available = False
    _deactivate(db, driver.user)
    db.commit()
    return {"message": "Driver removed"}


# ---------------- staff (extra logins for the same restaurant) ----------------
def _staff_row(user: User, restaurant: Restaurant) -> dict:
    return {
        "id": user.id, "email": user.email, "name": user.name, "sur_name": user.sur_name,
        "contact_number": user.contact_number, "is_active": user.is_active,
        "is_owner": restaurant.admin_id == user.id,
    }


@router.get("/staff", response_model=List[TeamMemberRead])
def list_staff(db: Session = Depends(get_db), restaurant: Restaurant = Depends(get_current_restaurant)):
    member_ids = [m.user_id for m in db.query(RestaurantAdmin).filter(RestaurantAdmin.restaurant_id == restaurant.id).all()]
    if restaurant.admin_id:
        member_ids.append(restaurant.admin_id)
    users = db.query(User).filter(User.id.in_(member_ids)).order_by(User.name.asc()).all() if member_ids else []
    return [_staff_row(user, restaurant) for user in users]


@router.post("/staff", response_model=TeamMemberRead)
def add_staff(
    payload: TeamMemberCreate,
    db: Session = Depends(get_db),
    restaurant: Restaurant = Depends(get_current_restaurant),
    user=Depends(restaurant_user),
):
    """Staff can run orders and the menu, but not payment settings, billing or the team."""
    owner_only(restaurant, user)
    member = _new_user(db, payload, Role.RESTAURANT_ADMIN)
    db.add(RestaurantAdmin(user_id=member.id, restaurant_id=restaurant.id))
    db.commit()
    return _staff_row(member, restaurant)


@router.delete("/staff/{user_id}")
def remove_staff(
    user_id: str,
    db: Session = Depends(get_db),
    restaurant: Restaurant = Depends(get_current_restaurant),
    user=Depends(restaurant_user),
):
    owner_only(restaurant, user)
    membership = db.query(RestaurantAdmin).filter(
        RestaurantAdmin.user_id == user_id, RestaurantAdmin.restaurant_id == restaurant.id
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Staff member not found")
    member = db.query(User).filter(User.id == user_id).first()
    db.delete(membership)
    if member:
        _deactivate(db, member)
    db.commit()
    return {"message": "Staff member removed"}
