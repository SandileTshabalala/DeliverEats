"""
Tenant isolation.

Each restaurant is a tenant. Everything a restaurant owns (orders, menu,
drivers, staff, payment settings, subscription) is reached ONLY through the
helpers in this file, so a restaurant can never read or change another
restaurant's data. Customers and platform admins are not tenants.

Use `get_current_restaurant` as the dependency on every restaurant-facing
endpoint instead of writing an ownership check by hand.
"""
from typing import Optional

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import PRIVILEGED_ROLES, get_db, require_role
from app.core.roles import Role
from app.models.restaurant import Restaurant
from app.models.restaurant_admin import RestaurantAdmin


def restaurant_for_user(db: Session, user) -> Optional[Restaurant]:
    """The restaurant this user works for: as its owner, or as added staff."""
    owned = db.query(Restaurant).filter(Restaurant.admin_id == user.id).first()
    if owned:
        return owned
    membership = db.query(RestaurantAdmin).filter(RestaurantAdmin.user_id == user.id).first()
    if membership:
        return db.query(Restaurant).filter(Restaurant.id == membership.restaurant_id).first()
    return None


def manages_restaurant(db: Session, user, restaurant_id: str) -> bool:
    """True if the user may act for this restaurant (platform admins always may)."""
    if user.role in PRIVILEGED_ROLES:
        return True
    restaurant = restaurant_for_user(db, user)
    return restaurant is not None and restaurant.id == restaurant_id


def is_owner(restaurant: Restaurant, user) -> bool:
    return user.role in PRIVILEGED_ROLES or restaurant.admin_id == user.id


def get_current_restaurant(
    db: Session = Depends(get_db),
    user=Depends(require_role(Role.RESTAURANT_ADMIN)),
) -> Restaurant:
    restaurant = restaurant_for_user(db, user)
    if not restaurant:
        raise HTTPException(status_code=404, detail="No restaurant is linked to this account")
    return restaurant


def restaurant_member_ids(db: Session, restaurant: Restaurant) -> list:
    """Owner + staff user ids (used to address live order notifications)."""
    ids = [m.user_id for m in db.query(RestaurantAdmin).filter(RestaurantAdmin.restaurant_id == restaurant.id).all()]
    if restaurant.admin_id:
        ids.append(restaurant.admin_id)
    return ids
