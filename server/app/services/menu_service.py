from sqlalchemy.orm import Session
from app.core.cache import get_cache, set_cache, delete_cache
from app.models.menu import Menu
from app.models.menu_item import MenuItem
from app.schemas.menu import MenuItemCreate

CACHE_TTL = 60  # seconds

async def create_menu_item(db: Session, menu_id: str, payload: MenuItemCreate):
    from starlette.concurrency import run_in_threadpool
    
    def create_sync():
        item = MenuItem(
            menu_id=menu_id,
            name=payload.name,
            description=payload.description,
            price=payload.price,
            image_url=payload.image_url
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    item = await run_in_threadpool(create_sync)

    # Invalidate cache
    key = f"menu:{menu_id}:items"
    await delete_cache(key)

    return item

async def get_menu_items(db: Session, menu_id: str):
    from starlette.concurrency import run_in_threadpool
    key = f"menu:{menu_id}:items"
    cached = await get_cache(key)
    if cached:
        return cached

    def fetch_items():
        items = db.query(MenuItem).filter(
            MenuItem.menu_id == menu_id,
            MenuItem.is_available == True
        ).all()

        return [
            {
                "id": i.id,
                "name": i.name,
                "description": i.description,
                "price": float(i.price),
                "is_available": i.is_available,
                "image_url": i.image_url
            } for i in items
        ]

    result = await run_in_threadpool(fetch_items)

    await set_cache(key, result, ttl=CACHE_TTL)
    return result

async def get_restaurant_menu(db: Session, restaurant_id: str):
    from starlette.concurrency import run_in_threadpool
    menu = await run_in_threadpool(lambda: db.query(Menu).filter(Menu.restaurant_id == restaurant_id, Menu.is_active == True).first())
    if not menu:
        return []
    return await get_menu_items(db, menu.id)

def get_active_menu_by_restaurant(db: Session, restaurant_id: str):
    menu = db.query(Menu).filter(Menu.restaurant_id == restaurant_id, Menu.is_active == True).first()
    if not menu:
        # Create a default menu if none exists
        menu = Menu(restaurant_id=restaurant_id, name="Default Menu", is_active=True)
        db.add(menu)
        db.commit()
        db.refresh(menu)
    return menu

async def update_menu_item(db: Session, item_id: str, payload: dict):
    from starlette.concurrency import run_in_threadpool
    
    def update_sync():
        item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
        if not item:
            return None
        
        for key, value in payload.items():
            if hasattr(item, key):
                setattr(item, key, value)
                
        db.commit()
        db.refresh(item)
        return item

    item = await run_in_threadpool(update_sync)
    if not item:
        return None
    
    # Invalidate cache
    key = f"menu:{item.menu_id}:items"
    await delete_cache(key)
    
    return item

async def delete_menu_item(db: Session, item_id: str):
    from starlette.concurrency import run_in_threadpool
    
    def delete_sync():
        item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
        if not item:
            return None
        menu_id = item.menu_id
        db.delete(item)
        db.commit()
        return menu_id

    menu_id = await run_in_threadpool(delete_sync)
    if not menu_id:
        return False
    
    # Invalidate cache
    key = f"menu:{menu_id}:items"
    await delete_cache(key)
    
    return True
