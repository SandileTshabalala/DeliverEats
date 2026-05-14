from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas.menu import MenuItemCreate, MenuItemResponse
from app.services.menu_service import create_menu_item, get_menu_items, get_restaurant_menu, get_active_menu_by_restaurant, update_menu_item, delete_menu_item
from app.core.dependencies import require_role
from app.core.roles import Role
from app.core.dependencies import get_db 

router = APIRouter(tags=["Menus"])

@router.get("/{menu_id}/items", response_model=list[MenuItemResponse])
async def list_menu_items(menu_id: str, db: Session = Depends(get_db)):
    return await get_menu_items(db, menu_id)

@router.post("/{menu_id}/items", response_model=MenuItemResponse)
async def add_menu_item(menu_id: str, payload: MenuItemCreate, db: Session = Depends(get_db), user=Depends(require_role(Role.RESTAURANT_ADMIN))):
    return await create_menu_item(db, menu_id, payload)

@router.get("/restaurant/{restaurant_id}", response_model=list[MenuItemResponse])
async def get_restaurant_menu_endpoint(restaurant_id: str, db: Session = Depends(get_db)):
    return await get_restaurant_menu(db, restaurant_id)

@router.post("/restaurant/{restaurant_id}/items", response_model=MenuItemResponse)
async def add_restaurant_menu_item(
    restaurant_id: str, 
    payload: MenuItemCreate, 
    db: Session = Depends(get_db), 
    user=Depends(require_role(Role.RESTAURANT_ADMIN))
):
    from starlette.concurrency import run_in_threadpool
    menu = await run_in_threadpool(get_active_menu_by_restaurant, db, restaurant_id)
    return await create_menu_item(db, menu.id, payload)

@router.patch("/{item_id}", response_model=MenuItemResponse)
async def update_item_endpoint(item_id: str, payload: dict, db: Session = Depends(get_db), user=Depends(require_role(Role.RESTAURANT_ADMIN))):
    return await update_menu_item(db, item_id, payload)

@router.delete("/{item_id}")
async def delete_item_endpoint(item_id: str, db: Session = Depends(get_db), user=Depends(require_role(Role.RESTAURANT_ADMIN))):
    if await delete_menu_item(db, item_id):
        return {"message": "Item deleted successfully"}
    return {"message": "Item not found"}, 404
