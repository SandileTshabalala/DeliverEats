"""
Food categories. Customers read the list (with pictures); the platform owner
adds, renames, reorders, hides and removes categories and sets their pictures.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_role
from app.core.roles import Role
from app.models.category import Category, RestaurantCategory
from app.services import categories as cats
from app.services import uploads

router = APIRouter(tags=["Categories"])
admin_only = require_role(Role.SUPER_ADMIN)


def _refresh_listings() -> None:
    """Restaurant cards show category names through a 60s cache: drop it."""
    try:
        from app.core.redis import redis_client
        keys = list(redis_client.scan_iter("lvovo:restaurant*")) + ["lvovo:categories:public"]
        redis_client.delete(*keys)
    except Exception:
        pass


def _admin_view(category: Category, used: dict) -> dict:
    return {**cats.public(category), "is_active": bool(category.is_active), "sort_order": category.sort_order,
            "restaurant_count": used.get(category.id, 0)}


def _clean_name(name: str) -> str:
    name = " ".join(name.split())
    if not name:
        raise HTTPException(status_code=400, detail="The category needs a name")
    return name


def _name_taken(db: Session, name: str, except_id: Optional[str] = None) -> bool:
    from sqlalchemy import func
    query = db.query(Category).filter(func.lower(Category.name) == name.lower())
    if except_id:
        query = query.filter(Category.id != except_id)
    return db.query(query.exists()).scalar()


def _get(db: Session, category_id: str) -> Category:
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


# ---------------------------------------------------------------- public
PUBLIC_CACHE_KEY = "categories:public"  # stored as lvovo:categories:public


@router.get("/categories")
async def public_categories(db: Session = Depends(get_db)) -> List[dict]:
    """Shown on every customer page and changes rarely: kept in the cache for 5 minutes."""
    from starlette.concurrency import run_in_threadpool
    from app.core.cache import get_cache, set_cache
    cached = await get_cache(PUBLIC_CACHE_KEY)
    if cached is not None:
        return cached
    result = await run_in_threadpool(lambda: [cats.public(c) for c in cats.listed(db)])
    await set_cache(PUBLIC_CACHE_KEY, result, ttl=300)
    return result


# ---------------------------------------------------------------- platform owner
class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=40)


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=40)
    is_active: Optional[bool] = None

    class Config:
        extra = "forbid"


class CategoryOrder(BaseModel):
    ids: List[str]


@router.get("/admin/categories")
def admin_categories(db: Session = Depends(get_db), admin=Depends(admin_only)) -> List[dict]:
    used = cats.counts(db)
    return [_admin_view(c, used) for c in cats.listed(db, include_hidden=True)]


@router.post("/admin/categories", status_code=201)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db), admin=Depends(admin_only)) -> dict:
    name = _clean_name(payload.name)
    if _name_taken(db, name):
        raise HTTPException(status_code=400, detail="There is already a category with that name")
    last = db.query(Category).order_by(Category.sort_order.desc()).first()
    category = Category(name=name, sort_order=(last.sort_order + 1) if last else 0)
    db.add(category)
    db.commit()
    db.refresh(category)
    _refresh_listings()
    return _admin_view(category, {})


@router.patch("/admin/categories/{category_id}")
def update_category(category_id: str, payload: CategoryUpdate, db: Session = Depends(get_db), admin=Depends(admin_only)) -> dict:
    category = _get(db, category_id)
    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes:
        name = _clean_name(changes["name"] or "")
        if _name_taken(db, name, except_id=category.id):
            raise HTTPException(status_code=400, detail="There is already a category with that name")
        category.name = name
    if changes.get("is_active") is not None:
        category.is_active = changes["is_active"]
    db.flush()
    cats.after_change(db, category.id)
    db.commit()
    db.refresh(category)
    _refresh_listings()
    return _admin_view(category, cats.counts(db))


@router.put("/admin/categories/order")
def reorder_categories(payload: CategoryOrder, db: Session = Depends(get_db), admin=Depends(admin_only)) -> List[dict]:
    """Save the order customers see the categories in (ids, first to last)."""
    rows = {c.id: c for c in db.query(Category).all()}
    if set(payload.ids) != set(rows) or len(payload.ids) != len(rows):
        raise HTTPException(status_code=400, detail="Send every category once, in the new order")
    for position, category_id in enumerate(payload.ids):
        rows[category_id].sort_order = position
    db.commit()
    _refresh_listings()
    return admin_categories(db, admin)


@router.post("/admin/categories/{category_id}/image")
async def upload_category_image(
    category_id: str, file: UploadFile = File(...), db: Session = Depends(get_db), admin=Depends(admin_only)
) -> dict:
    category = _get(db, category_id)
    previous = category.image_url
    category.image_url = await uploads.save_image(file, "categories", category.id)
    db.commit()
    db.refresh(category)
    uploads.delete_uploaded(previous)
    _refresh_listings()
    return _admin_view(category, cats.counts(db))


@router.delete("/admin/categories/{category_id}/image")
def remove_category_image(category_id: str, db: Session = Depends(get_db), admin=Depends(admin_only)) -> dict:
    category = _get(db, category_id)
    uploads.delete_uploaded(category.image_url)
    category.image_url = None
    db.commit()
    db.refresh(category)
    _refresh_listings()
    return _admin_view(category, cats.counts(db))


@router.delete("/admin/categories/{category_id}", status_code=204)
def delete_category(category_id: str, db: Session = Depends(get_db), admin=Depends(admin_only)) -> None:
    """Remove a category. Restaurants that used it keep their other categories."""
    category = _get(db, category_id)
    affected = cats.restaurants_using(db, category.id)
    db.query(RestaurantCategory).filter(RestaurantCategory.category_id == category.id).delete()
    uploads.delete_uploaded(category.image_url)
    db.delete(category)
    db.flush()
    if affected:
        cats._sync_main(db, affected)
    db.commit()
    _refresh_listings()
