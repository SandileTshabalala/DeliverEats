from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.dependencies import get_db, require_role
from app.core.tenancy import manages_restaurant
from app.core.roles import Role
from app.models.menu import Menu
from app.models.menu_item import MenuItem
from app.schemas.menu import MenuItemCreate, MenuItemResponse, MenuItemUpdate
from app.services import uploads
from app.services.menu_service import (
    create_menu_item,
    delete_menu_item,
    get_active_menu_by_restaurant,
    get_all_restaurant_items,
    get_menu_items,
    get_restaurant_menu,
    update_menu_item,
)

router = APIRouter(tags=["Menus"])


def ensure_owns_restaurant(db: Session, restaurant_id: str, user) -> None:
    """A restaurant admin may only change the menu of their own restaurant."""
    if not manages_restaurant(db, user, restaurant_id):
        raise HTTPException(status_code=403, detail="You can only manage the menu of your own restaurant")


def restaurant_id_for_menu(db: Session, menu_id: str) -> str:
    menu = db.query(Menu).filter(Menu.id == menu_id).first()
    if not menu:
        raise HTTPException(status_code=404, detail="Menu not found")
    return menu.restaurant_id


def restaurant_id_for_item(db: Session, item_id: str) -> str:
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return restaurant_id_for_menu(db, item.menu_id)


@router.get("/{menu_id}/items", response_model=list[MenuItemResponse])
async def list_menu_items(menu_id: str, db: Session = Depends(get_db)):
    return await get_menu_items(db, menu_id)


@router.post("/{menu_id}/items", response_model=MenuItemResponse)
async def add_menu_item(
    menu_id: str,
    payload: MenuItemCreate,
    db: Session = Depends(get_db),
    user=Depends(require_role(Role.RESTAURANT_ADMIN))
):
    restaurant_id = await run_in_threadpool(restaurant_id_for_menu, db, menu_id)
    await run_in_threadpool(ensure_owns_restaurant, db, restaurant_id, user)
    return await create_menu_item(db, menu_id, payload)


@router.get("/restaurant/{restaurant_id}", response_model=list[MenuItemResponse])
async def get_restaurant_menu_endpoint(restaurant_id: str, db: Session = Depends(get_db)):
    """Public menu: only items that can be ordered right now."""
    return await get_restaurant_menu(db, restaurant_id)


@router.get("/restaurant/{restaurant_id}/manage", response_model=list[MenuItemResponse])
async def manage_restaurant_menu_endpoint(
    restaurant_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_role(Role.RESTAURANT_ADMIN))
):
    """Owner view: every item, including ones switched off, so they can be switched back on."""
    await run_in_threadpool(ensure_owns_restaurant, db, restaurant_id, user)
    return await run_in_threadpool(get_all_restaurant_items, db, restaurant_id)


@router.post("/restaurant/{restaurant_id}/items", response_model=MenuItemResponse)
async def add_restaurant_menu_item(
    restaurant_id: str,
    payload: MenuItemCreate,
    db: Session = Depends(get_db),
    user=Depends(require_role(Role.RESTAURANT_ADMIN))
):
    await run_in_threadpool(ensure_owns_restaurant, db, restaurant_id, user)
    menu = await run_in_threadpool(get_active_menu_by_restaurant, db, restaurant_id)
    return await create_menu_item(db, menu.id, payload)


@router.patch("/{item_id}", response_model=MenuItemResponse)
async def update_item_endpoint(
    item_id: str,
    payload: MenuItemUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_role(Role.RESTAURANT_ADMIN))
):
    restaurant_id = await run_in_threadpool(restaurant_id_for_item, db, item_id)
    await run_in_threadpool(ensure_owns_restaurant, db, restaurant_id, user)
    item = await update_menu_item(db, item_id, payload.model_dump(exclude_unset=True))
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.post("/{item_id}/image", response_model=MenuItemResponse)
async def upload_item_image(
    item_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_role(Role.RESTAURANT_ADMIN))
):
    """Upload a photo for a menu item (PNG, JPG or WebP), replacing any earlier one."""
    restaurant_id = await run_in_threadpool(restaurant_id_for_item, db, item_id)
    await run_in_threadpool(ensure_owns_restaurant, db, restaurant_id, user)
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    previous = item.image_url
    path = await uploads.save_image(file, "menu", restaurant_id)
    updated = await update_menu_item(db, item_id, {"image_url": path})
    uploads.delete_uploaded(previous)
    return updated


@router.delete("/{item_id}")
async def delete_item_endpoint(
    item_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_role(Role.RESTAURANT_ADMIN))
):
    restaurant_id = await run_in_threadpool(restaurant_id_for_item, db, item_id)
    await run_in_threadpool(ensure_owns_restaurant, db, restaurant_id, user)
    result = await delete_menu_item(db, item_id)
    if result == "hidden":
        return {"message": "Item has past orders, so it was hidden from the menu instead of deleted"}
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item deleted successfully"}
