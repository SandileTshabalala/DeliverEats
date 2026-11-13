from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.orm import Session, joinedload, object_session, selectinload

from app.core.config import settings
from app.models.driver import Driver
from app.models.menu import Menu
from app.models.menu_item import MenuItem
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.payment import Payment
from app.models.restaurant import Restaurant
from app.models.user_address import UserAddress
from app.services import delivery_fee as delivery_fee_service
from app.services.delivery_service import assign_nearest_driver
from app.services.driver_service import get_available_driver, on_driver_available
from app.services.notification_service import send_notification
from app.utils.OrderStatus import OrderStatus
from app.utils.PaymentStatus import PaymentStatus
from app.utils.websocket_manager import manager

# Which status an order may move to from each status. Anything else is rejected,
# so an order cannot jump from "pending" straight to "delivered" or be revived
# after it was cancelled.
ALLOWED_TRANSITIONS = {
    OrderStatus.PENDING: {OrderStatus.ACCEPTED, OrderStatus.PREPARING, OrderStatus.WAITING_FOR_DRIVER, OrderStatus.CANCELLED},
    OrderStatus.WAITING_FOR_DRIVER: {OrderStatus.PREPARING, OrderStatus.READY, OrderStatus.CANCELLED},
    OrderStatus.ACCEPTED: {OrderStatus.PREPARING, OrderStatus.READY, OrderStatus.CANCELLED},
    OrderStatus.PREPARING: {OrderStatus.READY, OrderStatus.CANCELLED},
    OrderStatus.READY: {OrderStatus.PICKED_UP, OrderStatus.CANCELLED},
    OrderStatus.PICKED_UP: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}

ORDER_LOAD_OPTIONS = (
    joinedload(Order.customer),
    joinedload(Order.driver).joinedload(Driver.user),
    joinedload(Order.restaurant),
    selectinload(Order.items),
    selectinload(Order.payments).joinedload(Payment.provider),
)


def _status_value(status) -> str:
    return status.value if hasattr(status, "value") else str(status)


def short_id(order: Order) -> str:
    """The first 8 characters of the id: what people read out over the phone."""
    return order.id[:8].upper()


def notify_restaurant_of_new_order(order: Order) -> None:
    """A paid (or pay-on-delivery) order is waiting: tell the owner by SMS and email."""
    if not order.restaurant or not order.restaurant.admin_id:
        return
    items = ", ".join(f"{item.quantity} x {item.name}" for item in order.items)
    send_notification(
        order.restaurant.admin_id, "New order",
        f"#{short_id(order)} R {order.total_amount:.2f}: {items}",
    )
    send_notification(
        order.restaurant.admin_id, f"New order #{short_id(order)}",
        f"{items}\nTotal: R {order.total_amount:.2f}\nDeliver to: {order.delivery_address or 'see the app'}\nOpen your orders page to accept it.",
        sms=False, email=True,
        button_label="Open orders", button_url=f"{settings.FRONTEND_URL.rstrip('/')}/restaurant/orders",
    )


def order_audience(order: Order) -> list:
    """Users who are allowed to hear about this order."""
    audience = [order.customer_id, order.driver_id]
    db = object_session(order)
    if order.restaurant and db is not None:
        from app.core.tenancy import restaurant_member_ids
        audience.extend(restaurant_member_ids(db, order.restaurant))  # owner + staff
    elif order.restaurant:
        audience.append(order.restaurant.admin_id)
    return audience


def broadcast_order(order: Order, event_type: str = "order_updated") -> None:
    manager.notify(
        {
            "type": event_type,
            "order_id": order.id,
            "restaurant_id": order.restaurant_id,
            "status": _status_value(order.status),
            "driver_id": order.driver_id,
            "payment_status": order.payment_status,
        },
        order_audience(order),
    )


def get_order(db: Session, order_id: str):
    return db.query(Order).options(*ORDER_LOAD_OPTIONS).filter(Order.id == order_id).first()


def price_order(db: Session, customer_id: str, restaurant_id: str, items: list, address_id: str = None) -> dict:
    """
    Validate a basket and work out what it costs. Used both to show the customer
    a quote in the cart and to create the order, so the two can never disagree.

    Nothing about money is taken from the client: every line is priced from the
    menu, and the delivery fee comes from the restaurant's own settings.
    """
    restaurant = db.query(Restaurant).filter(
        Restaurant.id == restaurant_id,
        Restaurant.is_active == True
    ).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found or not open")

    # Subscription must be in good standing and within the plan's monthly order limit
    from app.services.subscription_service import ensure_can_take_orders
    ensure_can_take_orders(db, restaurant)

    if not items:
        raise HTTPException(status_code=400, detail="Your cart is empty")

    # Delivery address must belong to the customer placing the order
    address_snapshot = {}
    if address_id:
        addr = db.query(UserAddress).filter(
            UserAddress.id == address_id,
            UserAddress.user_id == customer_id
        ).first()
        if not addr:
            raise HTTPException(status_code=400, detail="Delivery address not found")
        address_snapshot = {
            "delivery_lat": addr.latitude,
            "delivery_lng": addr.longitude,
            "delivery_address": addr.formatted_address,
        }

    # Merge duplicate lines, then load only items that are on THIS restaurant's menu
    quantities = {}
    for item in items:
        quantities[item.menu_item_id] = quantities.get(item.menu_item_id, 0) + item.quantity

    menu_items = {
        mi.id: mi
        for mi in db.query(MenuItem)
        .join(Menu, MenuItem.menu_id == Menu.id)
        .filter(MenuItem.id.in_(list(quantities)), Menu.restaurant_id == restaurant_id)
        .all()
    }

    missing = [item_id for item_id in quantities if item_id not in menu_items]
    if missing:
        raise HTTPException(
            status_code=400,
            detail="Some items in your cart are no longer on this menu. Please refresh your cart."
        )
    unavailable = [mi.name for mi in menu_items.values() if not mi.is_available]
    if unavailable:
        raise HTTPException(status_code=400, detail=f"Currently unavailable: {', '.join(unavailable)}")

    subtotal = sum((mi.price * quantities[mi.id] for mi in menu_items.values()), Decimal("0")).quantize(Decimal("0.01"))
    delivery = delivery_fee_service.quote(
        db, restaurant_id, subtotal,
        address_snapshot.get("delivery_lat"), address_snapshot.get("delivery_lng"),
    )
    delivery_fee = delivery["delivery_fee"]

    return {
        "restaurant": restaurant,
        "menu_items": menu_items,
        "quantities": quantities,
        "address_snapshot": address_snapshot,
        "subtotal": subtotal,
        "delivery_fee": delivery_fee,
        "total": (subtotal + delivery_fee).quantize(Decimal("0.01")),
        "distance_km": delivery["distance_km"],
        "free_delivery": delivery["free_delivery"],
        "free_delivery_over": delivery["free_delivery_over"],
    }


def create_order(db: Session, customer_id: str, restaurant_id: str, items: list, address_id: str = None):
    """Create an order for `customer_id`, priced by `price_order`."""
    priced = price_order(db, customer_id, restaurant_id, items, address_id)
    menu_items, quantities = priced["menu_items"], priced["quantities"]
    address_snapshot, total, delivery_fee = priced["address_snapshot"], priced["total"], priced["delivery_fee"]

    order = Order(
        customer_id=customer_id,
        restaurant_id=restaurant_id,
        total_amount=total,
        delivery_fee=delivery_fee,
        status=OrderStatus.PENDING,
        **address_snapshot
    )
    db.add(order)
    db.flush()

    for menu_item in menu_items.values():
        db.add(OrderItem(
            order_id=order.id,
            menu_item_id=menu_item.id,
            name=menu_item.name,
            description=menu_item.description,
            quantity=quantities[menu_item.id],
            price=menu_item.price,  # price snapshot at the time of ordering
        ))

    db.commit()
    order = get_order(db, order.id)
    # The restaurant is told about the order once payment is settled
    # (see payment_service); the customer's own screens update straight away.
    manager.notify(
        {"type": "new_order", "order_id": order.id, "restaurant_id": order.restaurant_id,
         "status": _status_value(order.status), "payment_status": order.payment_status},
        [order.customer_id],
        include_admins=False,
    )
    return order


def lock_order(db: Session, order_id: str) -> bool:
    """
    Atomically claim a PENDING order so two people cannot accept it at once.
    """
    result = db.execute(
        update(Order)
        .where(Order.id == order_id, Order.locked == False, Order.status == OrderStatus.PENDING)
        .values(locked=True, locked_at=datetime.now(timezone.utc))
    )
    db.commit()
    return result.rowcount == 1


def assign_driver(db: Session, order_id: str):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return None

    # Prefer the closest driver, but drivers who have not shared a location yet
    # must still get work: fall back to the fairest (least recently used) driver.
    driver = None
    if order.delivery_lat is not None and order.delivery_lng is not None:
        driver = assign_nearest_driver(db, order.delivery_lat, order.delivery_lng, order.restaurant_id)
    if not driver:
        driver = get_available_driver(db, order.restaurant_id)

    if not driver:
        # Nobody is free: queue the order, it is picked up when a driver goes online
        if order.status == OrderStatus.PENDING:
            order.status = OrderStatus.WAITING_FOR_DRIVER
        if not order.driver_wait_started_at:
            order.driver_wait_started_at = datetime.now(timezone.utc)
        db.commit()
        broadcast_order(order)
        return None

    order.driver_id = driver.id
    # The kitchen may already be further along (e.g. READY) if it cooked while waiting
    if order.status in (OrderStatus.PENDING, OrderStatus.WAITING_FOR_DRIVER):
        order.status = OrderStatus.PREPARING
    order.driver_wait_started_at = None
    driver.last_assigned_at = datetime.now(timezone.utc)
    db.commit()

    shop = order.restaurant.name if order.restaurant else "the restaurant"
    send_notification(
        driver.id, "New delivery",
        f"Order #{short_id(order)} from {shop} to {order.delivery_address or 'the customer'}. Open the app for details.",
    )
    send_notification(order.customer_id, shop, f"Your order #{short_id(order)} was accepted and is being prepared.")
    broadcast_order(order)
    return driver


def update_order_status(db: Session, order_id: str, new_status: OrderStatus, order: Order = None):
    """
    Move an order to `new_status`. Raises 409 if that step is not allowed from
    the order's current status. Returns None when the order does not exist.
    """
    if not isinstance(new_status, OrderStatus):
        try:
            new_status = OrderStatus(new_status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Unknown order status")

    order = order or db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return None

    current = OrderStatus(_status_value(order.status))
    if new_status == current:
        return order
    if new_status not in ALLOWED_TRANSITIONS[current]:
        raise HTTPException(
            status_code=409,
            detail=f"An order that is '{current.value}' cannot be changed to '{new_status.value}'"
        )

    order.status = new_status
    db.commit()
    db.refresh(order)

    # Customer updates. SMS only for the moments that matter (each SMS costs money):
    # on the way, and cancelled. Delivered is an email receipt.
    shop = order.restaurant.name if order.restaurant else "the restaurant"
    if new_status == OrderStatus.PICKED_UP:
        send_notification(order.customer_id, shop, f"Your order #{short_id(order)} is on its way to you.")
    elif new_status == OrderStatus.CANCELLED:
        send_notification(order.customer_id, shop, f"Your order #{short_id(order)} was cancelled.", email=True)
        if order.driver_id:
            send_notification(order.driver_id, "Delivery cancelled", f"Order #{short_id(order)} from {shop} was cancelled.")
    elif new_status == OrderStatus.DELIVERED:
        send_notification(
            order.customer_id, f"Your order from {shop}",
            f"Order #{short_id(order)} was delivered.\nTotal: R {order.total_amount:.2f}\nThank you for ordering local.",
            sms=False, email=True,
        )

    # Free the driver once the delivery is finished or called off
    if new_status in {OrderStatus.DELIVERED, OrderStatus.CANCELLED} and order.driver_id:
        # The driver is free again. If they are still online, hand them the
        # next order of their restaurant that is waiting for a driver.
        finished_driver = db.query(Driver).filter(Driver.id == order.driver_id).first()
        if finished_driver and finished_driver.is_available:
            on_driver_available(db, finished_driver)

    # Cash / card on delivery is settled the moment the order is handed over
    if new_status == OrderStatus.DELIVERED:
        for payment in order.payments:
            if payment.status == PaymentStatus.PENDING and order.payment_status == "pay_on_delivery":
                payment.status = PaymentStatus.COMPLETED
        db.commit()

    broadcast_order(order)
    return order


def get_restaurant_orders(db: Session, restaurant_id: str, limit: int = 20, offset: int = 0):
    return (
        db.query(Order)
        .options(*ORDER_LOAD_OPTIONS)
        .filter(Order.restaurant_id == restaurant_id)
        .order_by(Order.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def cancel_stale_orders(db: Session):
    """
    Run periodically by Celery beat:
    - orders that waited too long for a driver are cancelled
    - orders whose online payment was never completed are cancelled
    """
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=settings.MAX_WAIT_MINUTES)

    waiting = db.query(Order).filter(
        Order.status == OrderStatus.WAITING_FOR_DRIVER,
        Order.driver_wait_started_at < cutoff
    ).all()

    abandoned = [
        order for order in db.query(Order).options(*ORDER_LOAD_OPTIONS).filter(
            Order.status == OrderStatus.PENDING,
            Order.created_at < cutoff
        ).all()
        if not order.is_payment_cleared
    ]

    for order in waiting + abandoned:
        order.status = OrderStatus.CANCELLED
        for payment in order.payments:
            if payment.status == PaymentStatus.PENDING:
                payment.status = PaymentStatus.FAILED
        # NOTE: an order cancelled here after a completed online payment still
        # needs a refund, which has to be issued from the PayFast dashboard.
        db.commit()
        send_notification(
            order.customer_id, "Order cancelled",
            f"Your order #{short_id(order)} was cancelled because it could not be completed in time.", email=True,
        )
        broadcast_order(order)
