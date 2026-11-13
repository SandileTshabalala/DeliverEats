"""
A restaurant managing ITSELF: how it gets paid, its subscription, its drivers
and its staff. Every endpoint is scoped by `get_current_restaurant`, so there is
no restaurant id in any URL and no way to reach another restaurant's data.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_role
from app.core.roles import Role
from app.core.security import hash_password
from app.core.tenancy import get_current_restaurant, is_owner
from app.models.driver import Driver
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
