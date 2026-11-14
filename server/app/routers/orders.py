from typing import Optional
from fastapi import Header, APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_role
from app.core.tenancy import manages_restaurant
from app.core.roles import Role
from app.models.order import Order
from app.schemas.order import OrderCreate, OrderQuote, OrderRead, ReviewCreate
from app.models.order_review import OrderReview
from app.services.order_service import (
    CUSTOMER_ORDER_OPTIONS,
    ORDER_LOAD_OPTIONS,
    assign_driver,
    broadcast_order,
    create_order,
    get_order,
    lock_order,
    price_order,
    update_order_status,
)
from app.utils.OrderStatus import OrderStatus

router = APIRouter(tags=["Orders"])


def get_order_for_restaurant_user(db: Session, order_id: str, user) -> Order:
    """Load an order and make sure it belongs to a restaurant this user runs."""
    order = get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if not manages_restaurant(db, user, order.restaurant_id):
        # 404 rather than 403 so order ids of other shops cannot be probed
        raise HTTPException(status_code=404, detail="Order not found")
    return order


# ----------------------------
# CREATE NEW ORDER
# ----------------------------
@router.post("/", response_model=OrderRead)
def new_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    user=Depends(require_role(Role.CUSTOMER)),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key", max_length=100),
):
    """
    Customer creates a new order. The customer is taken from the token and the
    total is calculated on the server from the menu prices.

    The app sends an Idempotency-Key per checkout: if the same request arrives
    again (weak signal, the phone resends it), the first order is returned
    instead of a second one being created.
    """
    from app.services import idempotency

    with idempotency.once(f"order:{user.id}", idempotency_key) as previous:
        if previous:
            existing = db.query(Order).filter(Order.id == previous, Order.customer_id == user.id).first()
            if existing:
                return existing
        order = create_order(db, user.id, payload.restaurant_id, payload.items, payload.address_id)
        idempotency.remember(f"order:{user.id}", idempotency_key, order.id)
        return order


# ----------------------------
# PRICE A BASKET (cart preview)
# ----------------------------
@router.post("/quote", response_model=OrderQuote)
def quote_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    user=Depends(require_role(Role.CUSTOMER))
):
    """
    What this basket would cost, including the restaurant's delivery fee to the
    chosen address. Creates nothing. Uses exactly the same pricing as placing the order.
    """
    return price_order(db, user.id, payload.restaurant_id, payload.items, payload.address_id)


# ----------------------------
# ACCEPT ORDER BY RESTAURANT
# ----------------------------
@router.post("/{order_id}/accept", response_model=OrderRead)
def accept_order(
    order_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_role(Role.RESTAURANT_ADMIN)),
):
    """
    Restaurant accepts the order.
    If a driver is free -> assigned and the order moves to "preparing".
    If not -> the order waits for a driver.
    """
    order = get_order_for_restaurant_user(db, order_id, user)

    if order.status != OrderStatus.PENDING:
        raise HTTPException(status_code=409, detail="Order already processed")

    if not order.is_payment_cleared:
        raise HTTPException(
            status_code=409,
            detail="This order has not been paid yet. It can be accepted once payment is confirmed."
        )

    # Prevent double acceptance
    if not lock_order(db, order_id):
        raise HTTPException(status_code=409, detail="Order already accepted")

    try:
        assign_driver(db, order_id)
    except Exception:
        # Do not leave the order locked forever if assignment blew up
        db.rollback()
        db.query(Order).filter(Order.id == order_id).update({"locked": False, "locked_at": None})
        db.commit()
        raise

    db.expire_all()
    return get_order(db, order_id)


# ----------------------------
# UPDATE ORDER STATUS (restaurant)
# ----------------------------
@router.post("/{order_id}/status")
def change_status(
    order_id: str,
    status: OrderStatus,
    db: Session = Depends(get_db),
    user=Depends(require_role(Role.RESTAURANT_ADMIN))
):
    ALLOWED_RESTAURANT_STATUSES = {
        OrderStatus.ACCEPTED,
        OrderStatus.PREPARING,
        OrderStatus.READY,
        OrderStatus.CANCELLED
    }

    if status not in ALLOWED_RESTAURANT_STATUSES:
        raise HTTPException(status_code=403, detail="Invalid status for restaurant")

    order = get_order_for_restaurant_user(db, order_id, user)

    if status != OrderStatus.CANCELLED and not order.is_payment_cleared:
        raise HTTPException(status_code=409, detail="This order has not been paid yet")

    order = update_order_status(db, order_id, status, order=order)
    return {"order_id": order.id, "status": order.status}


# ----------------------------
# CUSTOMER: CANCEL OWN ORDER
# ----------------------------
@router.post("/{order_id}/cancel", response_model=OrderRead)
def cancel_my_order(
    order_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_role(Role.CUSTOMER))
):
    """A customer may cancel only while the restaurant has not accepted yet."""
    order = get_order(db, order_id)
    if not order or order.customer_id != user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != OrderStatus.PENDING:
        raise HTTPException(status_code=409, detail="The restaurant has already started on this order")
    if order.payment_status == "completed":
        raise HTTPException(
            status_code=409,
            detail="This order is already paid. Please contact the restaurant to cancel and refund it."
        )
    update_order_status(db, order_id, OrderStatus.CANCELLED, order=order)
    db.expire_all()
    order = get_order(db, order_id)
    broadcast_order(order)
    return order


# ----------------------------
# CUSTOMER: RATE A DELIVERED ORDER
# ----------------------------
@router.post("/{order_id}/review", response_model=OrderRead)
def review_order(
    order_id: str,
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    user=Depends(require_role(Role.CUSTOMER))
):
    """One rating per order, only by the customer who received it."""
    order = get_order(db, order_id)
    if not order or order.customer_id != user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != OrderStatus.DELIVERED:
        raise HTTPException(status_code=409, detail="You can rate an order once it has been delivered")
    if order.review:
        raise HTTPException(status_code=409, detail="You have already rated this order")

    db.add(OrderReview(
        order_id=order.id, restaurant_id=order.restaurant_id, customer_id=user.id,
        rating=payload.rating, comment=(payload.comment or "").strip() or None,
    ))
    db.commit()
    try:  # the public list shows the average: refresh it
        from app.core.redis import redis_client
        redis_client.delete("lvovo:restaurants:list", f"lvovo:restaurant:{order.restaurant_id}")
    except Exception:
        pass
    db.expire_all()
    return db.query(Order).options(*CUSTOMER_ORDER_OPTIONS).filter(Order.id == order_id).first()


# ----------------------------
# DRIVER VIEW: GET JOBS
# ----------------------------
@router.get("/driver/jobs", response_model=list[OrderRead])
def driver_jobs(
    db: Session = Depends(get_db),
    user=Depends(require_role(Role.DRIVER))
):
    """Driver sees all assigned orders that are not delivered/cancelled."""
    return db.query(Order).options(*ORDER_LOAD_OPTIONS).filter(
        Order.driver_id == user.id,
        Order.status.notin_([OrderStatus.DELIVERED, OrderStatus.CANCELLED])
    ).order_by(Order.created_at.asc()).all()


@router.get("/driver/history", response_model=list[OrderRead])
def driver_history(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    user=Depends(require_role(Role.DRIVER))
):
    """Driver sees ALL assigned orders (history)."""
    limit = max(1, min(limit, 100))
    return db.query(Order).options(*ORDER_LOAD_OPTIONS).filter(
        Order.driver_id == user.id
    ).order_by(Order.created_at.desc()).offset(max(0, offset)).limit(limit).all()


# ----------------------------
# CUSTOMER VIEW: GET MY ORDERS
# ----------------------------
@router.get("/my", response_model=list[OrderRead])
def my_orders(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    user=Depends(require_role(Role.CUSTOMER))
):
    """Customer sees all their orders."""
    limit = max(1, min(limit, 100))
    return db.query(Order).options(*CUSTOMER_ORDER_OPTIONS).filter(
        Order.customer_id == user.id
    ).order_by(Order.created_at.desc()).offset(max(0, offset)).limit(limit).all()
