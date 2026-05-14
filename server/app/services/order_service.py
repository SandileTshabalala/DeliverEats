from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import update
from datetime import datetime, timezone
import json

from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.user_address import UserAddress
from app.services.driver_service import set_driver_availability
from app.services.delivery_service import assign_nearest_driver
from app.services.notification_service import send_notification
from app.utils.OrderStatus import OrderStatus
from app.models.menu_item import MenuItem

# Import WebSocket manager for real-time updates
try:
    from app.utils.websocket_manager import manager
except ImportError:
    manager = None

def create_order(db: Session, customer_id: str, restaurant_id: str, items: list, total: float, address_id: str = None):
    # Fetch address if provided
    address_snapshot = {}
    if address_id:
        addr = db.query(UserAddress).filter(UserAddress.id == address_id).first()
        if addr:
            address_snapshot = {
                "delivery_lat": addr.latitude,
                "delivery_lng": addr.longitude,
                "delivery_address": addr.formatted_address
            }

    # Create valid order
    order = Order(
        customer_id=customer_id, 
        restaurant_id=restaurant_id, 
        total_amount=total, # Fixed field name
        status="pending",
        **address_snapshot
    )
    db.add(order)
    db.flush()

    # Fetch all menu items in one query
    menu_item_ids = [item.menu_item_id for item in items]
    menu_items = {
        mi.id: mi for mi in db.query(MenuItem).filter(MenuItem.id.in_(menu_item_ids)).all()
    }

    for item_data in items:
        menu_item = menu_items.get(item_data.menu_item_id)
        if menu_item:
            order_item = OrderItem(
                order_id=order.id,
                menu_item_id=menu_item.id,
                name=menu_item.name,
                description=menu_item.description,
                quantity=item_data.quantity,
                price=menu_item.price # Use server-side price
            )
            db.add(order_item)

    db.commit()
    db.refresh(order)
    
    # Broadcast new order to connected clients
    if manager:
        import asyncio
        loop = None
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            pass

        if loop and loop.is_running():
            loop.create_task(manager.broadcast(json.dumps({
                "type": "new_order",
                "order_id": order.id,
                "restaurant_id": order.restaurant_id,
                "status": order.status
            })))
        else:
            print("Warning: No running event loop found for broadcast")
    
    return order

def lock_order(db: Session, order_id: str) -> bool:
    """
    Lock an order to prevent double acceptance
    """
    result = db.execute(
        update(Order)
        .where(Order.id == order_id, Order.locked == False)
        .values(locked=True, locked_at=datetime.now(timezone.utc))
    )
    db.commit()
    return result.rowcount == 1

def assign_driver(db: Session, order_id: str):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return None

    # Use nearest driver assignment if coordinates available
    if order.delivery_lat and order.delivery_lng:
        driver = assign_nearest_driver(db, order.delivery_lat, order.delivery_lng)
    else:
        # Fallback to general available driver retrieval
        from app.services.driver_service import get_available_driver
        driver = get_available_driver(db)

    if not driver:
        # Queue the order if no driver is available
        order.status = OrderStatus.WAITING_FOR_DRIVER.value
        order.driver_wait_started_at = datetime.now(timezone.utc)
        db.commit()
        # Broadcast the status update so frontend knows
        if manager:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop and loop.is_running():
                    loop.create_task(manager.broadcast(json.dumps({
                        "type": "order_updated",
                        "order_id": order.id,
                        "status": order.status
                    })))
            except:
                pass
        return None

    order.driver_id = driver.id
    order.status = OrderStatus.PREPARING # Driver assigned -> Preparing
    set_driver_availability(db, driver.id, False)

    db.commit()

    # Notify driver and customer
    send_notification(driver.id, "New Delivery Assigned", f"Order {order.id} assigned to you")
    send_notification(order.customer_id, "Order Accepted", f"Your order {order.id} is now being prepared")

    # Broadcast order update
    if manager:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop and loop.is_running():
                loop.create_task(manager.broadcast(json.dumps({
                    "type": "order_updated",
                    "order_id": order.id,
                    "status": order.status,
                    "driver_id": order.driver_id
                })))
        except:
            pass

    return driver

def update_order_status(
    db: Session,
    order_id: str,
    new_status: OrderStatus
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return None

    # ✅ assign enum value to DB
    order.status = new_status.value
    db.commit()
    db.refresh(order)

    # ✅ human-readable text
    status_text = new_status.value.replace("_", " ").title()

    # Notify customer
    send_notification(
        order.customer_id,
        f"Order {status_text}",
        f"Your order {order.id} is now {status_text}"
    )

    # ✅ Release driver if done
    if new_status in {OrderStatus.DELIVERED, OrderStatus.CANCELLED}:
        if order.driver_id:
            set_driver_availability(db, order.driver_id, True)

    # Broadcast order update
    if manager:
        import asyncio, json
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(manager.broadcast(json.dumps({
                "type": "order_updated",
                "order_id": order.id,
                "status": new_status.value
            })))
        except RuntimeError:
            pass

    return order


def get_restaurant_orders(db: Session, restaurant_id: str, limit: int = 20, offset: int = 0):
    return db.query(Order).options(
        joinedload(Order.customer),
        joinedload(Order.driver),
        joinedload(Order.restaurant),
        selectinload(Order.items)
    ).filter(Order.restaurant_id == restaurant_id).order_by(Order.created_at.desc()).offset(offset).limit(limit).all()

def cancel_stale_orders(db: Session):
    from datetime import datetime, timedelta
    from app.core.config import settings
    MAX_WAIT_MINUTES = settings.MAX_WAIT_MINUTES
    limit = datetime.utcnow() - timedelta(minutes=MAX_WAIT_MINUTES)

    orders = db.query(Order).filter(
        Order.status == OrderStatus.WAITING_FOR_DRIVER,
        Order.driver_wait_started_at < limit
    )

    for order in orders:
        order.status = OrderStatus.CANCELLED
        # refund(order) #refund logic
        db.commit()

