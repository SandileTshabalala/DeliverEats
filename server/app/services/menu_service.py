from sqlalchemy.orm import Session
from app.core.cache import get_cache, set_cache, delete_cache
from app.models.menu import Menu
from app.models.menu_item import MenuItem
from app.schemas.menu import MenuItemCreate
from app.services import menu_options

# Every change to a dish clears the menu cache, so it can be kept a while
CACHE_TTL = 300  # seconds


def _clean_section(name):
    """'  mains ' -> 'mains' kept as typed; empty -> None (the unnamed first section)."""
    name = " ".join((name or "").split())
    return name or None

async def create_menu_item(db: Session, menu_id: str, payload: MenuItemCreate):
    from starlette.concurrency import run_in_threadpool
    
    def create_sync():
        item = MenuItem(
            menu_id=menu_id,
            name=payload.name,
            description=payload.description,
            price=payload.price,
            image_url=payload.image_url,
            section=_clean_section(payload.section),
            options=menu_options.normalise(payload.options),
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
                "image_url": i.image_url,
                "section": i.section,
                "options": i.options or [],
            } for i in items
        ]

    result = await run_in_threadpool(fetch_items)

    await set_cache(key, result, ttl=CACHE_TTL)
    return result

async def get_restaurant_menu(db: Session, restaurant_id: str):
    """
    Public menu. Which menu a restaurant uses almost never changes, so that is
    cached too: a cached menu is served without asking the database at all
    (each question costs 300-500 ms while the database is far away).
    """
    from starlette.concurrency import run_in_threadpool
    key = f"menu_of:{restaurant_id}"
    menu_id = await get_cache(key)
    if not menu_id:
        menu = await run_in_threadpool(lambda: db.query(Menu).filter(Menu.restaurant_id == restaurant_id, Menu.is_active == True).first())
        if not menu:
            return []
        menu_id = menu.id
        await set_cache(key, menu_id, ttl=3600)
    return await get_menu_items(db, menu_id)

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
        
        for key in ("name", "description", "price", "image_url", "is_available"):
            if key in payload:
                setattr(item, key, payload[key])
        if "section" in payload:
            item.section = _clean_section(payload["section"])
        if "options" in payload and payload["options"] is not None:
            item.options = menu_options.normalise(payload["options"])
                
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
        # Past orders point at this item. Deleting it would fail on the foreign
        # key (500 error), so an item that has been ordered is hidden instead.
        from app.models.order_item import OrderItem
        if db.query(OrderItem).filter(OrderItem.menu_item_id == item_id).first():
            item.is_available = False
            db.commit()
            return menu_id, "hidden"
        db.delete(item)
        db.commit()
        return menu_id, "deleted"

    result = await run_in_threadpool(delete_sync)
    if not result:
        return False
    menu_id, outcome = result

    # Invalidate cache
    key = f"menu:{menu_id}:items"
    await delete_cache(key)

    return outcome


def get_all_restaurant_items(db: Session, restaurant_id: str):
    """Every item of a restaurant, available or not (for the owner menu screen)."""
    return (
        db.query(MenuItem)
        .join(Menu, MenuItem.menu_id == Menu.id)
        .filter(Menu.restaurant_id == restaurant_id)
        .order_by(MenuItem.name.asc())
        .all()
    )
