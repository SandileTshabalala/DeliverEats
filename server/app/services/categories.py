"""
Food categories: the platform owner manages the list (names, pictures, order);
restaurants choose up to MAX_PER_RESTAURANT of them; customers browse by them.

restaurants.category (a plain text column) keeps a copy of each restaurant's
main category name for reports and older screens; this module keeps it in sync.
"""
from typing import Dict, Iterable, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.category import Category, RestaurantCategory
from app.models.platform_setting import PlatformSetting
from app.models.restaurant import Restaurant

MAX_PER_RESTAURANT = 3

# The starting list, created once. After that the platform owner is in charge of it.
DEFAULTS = [
    "Shisanyama",
    "Kota & Bunny Chow",
    "Chicken",
    "Burgers",
    "Traditional",
    "Fast Food",
    "Pizza",
    "Breakfast",
    "Bakery & Sweets",
    "Drinks",
    "Spaza & Groceries",
    "Other",
]
_SEEDED_FLAG = "categories_seeded"


def ensure_defaults(db: Session) -> None:
    """Create the starting list once, and link restaurants that already chose a category."""
    if db.get(PlatformSetting, _SEEDED_FLAG):
        return
    if db.query(Category).count() == 0:
        for position, name in enumerate(DEFAULTS):
            db.add(Category(name=name, sort_order=position))
        db.flush()
    by_name = {c.name.lower(): c for c in db.query(Category).all()}
    for restaurant in db.query(Restaurant).filter(Restaurant.category.isnot(None)).all():
        category = by_name.get(restaurant.category.lower())
        if category and not db.get(RestaurantCategory, (restaurant.id, category.id)):
            db.add(RestaurantCategory(restaurant_id=restaurant.id, category_id=category.id, position=0))
    db.add(PlatformSetting(key=_SEEDED_FLAG, value="1"))
    db.commit()


def listed(db: Session, include_hidden: bool = False) -> List[Category]:
    query = db.query(Category)
    if not include_hidden:
        query = query.filter(Category.is_active == True)  # noqa: E712
    return query.order_by(Category.sort_order, Category.name).all()


def public(category: Category) -> dict:
    return {"id": category.id, "name": category.name, "image_url": category.image_url}


def names_by_restaurant(db: Session, restaurant_ids: Optional[Iterable[str]] = None) -> Dict[str, List[str]]:
    """restaurant_id -> its visible category names, main one first (one query)."""
    query = db.query(RestaurantCategory.restaurant_id, Category.name).join(
        Category, Category.id == RestaurantCategory.category_id
    ).filter(Category.is_active == True)  # noqa: E712
    if restaurant_ids is not None:
        query = query.filter(RestaurantCategory.restaurant_id.in_(list(restaurant_ids)))
    result: Dict[str, List[str]] = {}
    for restaurant_id, name in query.order_by(RestaurantCategory.position, Category.sort_order).all():
        result.setdefault(restaurant_id, []).append(name)
    return result


def chosen_ids(db: Session, restaurant_id: str) -> List[str]:
    rows = db.query(RestaurantCategory).filter(RestaurantCategory.restaurant_id == restaurant_id).order_by(
        RestaurantCategory.position
    ).all()
    return [row.category_id for row in rows]


def _sync_main(db: Session, restaurant_ids: Iterable[str]) -> None:
    names = names_by_restaurant(db, restaurant_ids)
    for restaurant in db.query(Restaurant).filter(Restaurant.id.in_(list(restaurant_ids))).all():
        restaurant.category = (names.get(restaurant.id) or [None])[0]


def set_for_restaurant(db: Session, restaurant: Restaurant, category_ids: List[str]) -> None:
    """Replace the restaurant's categories. The first one is its main category."""
    ids = list(dict.fromkeys(category_ids))  # drop repeats, keep order
    if len(ids) > MAX_PER_RESTAURANT:
        raise HTTPException(status_code=400, detail=f"Choose up to {MAX_PER_RESTAURANT} categories")
    found = {c.id for c in db.query(Category).filter(Category.id.in_(ids), Category.is_active == True).all()}  # noqa: E712
    if len(found) != len(ids):
        raise HTTPException(status_code=400, detail="Choose categories from the list")
    db.query(RestaurantCategory).filter(RestaurantCategory.restaurant_id == restaurant.id).delete()
    for position, category_id in enumerate(ids):
        db.add(RestaurantCategory(restaurant_id=restaurant.id, category_id=category_id, position=position))
    db.flush()
    _sync_main(db, [restaurant.id])


def id_for_name(db: Session, name: str) -> str:
    category = db.query(Category).filter(Category.name == name, Category.is_active == True).first()  # noqa: E712
    if not category:
        raise HTTPException(status_code=400, detail="Choose a category from the list")
    return category.id


def restaurants_using(db: Session, category_id: str) -> List[str]:
    return [row.restaurant_id for row in db.query(RestaurantCategory.restaurant_id).filter(
        RestaurantCategory.category_id == category_id).all()]


def after_change(db: Session, category_id: str) -> None:
    """A category was renamed, hidden or shown: refresh the main-name copies that use it."""
    affected = restaurants_using(db, category_id)
    if affected:
        _sync_main(db, affected)


def counts(db: Session) -> Dict[str, int]:
    from sqlalchemy import func
    return dict(db.query(RestaurantCategory.category_id, func.count(RestaurantCategory.restaurant_id)).group_by(
        RestaurantCategory.category_id).all())


def for_owner(db: Session, restaurant_id: str):
    """(the restaurant's chosen ids in order, every visible category) in one query, for the settings screen."""
    rows = db.query(Category, RestaurantCategory.position).outerjoin(
        RestaurantCategory,
        (RestaurantCategory.category_id == Category.id) & (RestaurantCategory.restaurant_id == restaurant_id),
    ).filter(Category.is_active == True).order_by(Category.sort_order, Category.name).all()  # noqa: E712
    chosen = sorted((position, category.id) for category, position in rows if position is not None)
    return [category_id for _, category_id in chosen], [public(category) for category, _ in rows]
