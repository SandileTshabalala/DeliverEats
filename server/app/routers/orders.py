from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload, selectinload
from typing import Literal

from app.schemas.order import OrderCreate, OrderRead
from app.services.order_service import (
    create_order,
    lock_order,
    assign_driver,
    update_order_status
)
from app.core.roles import Role
from app.core.dependencies import get_db, require_role, get_current_user
from app.models.order import Order
from app.utils.OrderStatus import OrderStatus
from datetime import datetime, timezone

router = APIRouter(tags=["Orders"])

# ----------------------------
# CREATE NEW ORDER
# ----------------------------
@router.post("/", response_model=OrderRead)
def new_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    user = Depends(require_role(Role.CUSTOMER))
):
    """
    Customer creates a new order.
    """
    order = create_order(db, user.id, payload.restaurant_id, payload.items, payload.total, payload.address_id)
    return order

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
    If drivers exist → assign
    If not → wait for driver
    """

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # 🔒 Prevent double acceptance
    if not lock_order(db, order_id):
        raise HTTPException(status_code=409, detail="Order already accepted")

    if order.status != OrderStatus.PENDING:
        raise HTTPException(status_code=400, detail="Order already processed")

    driver = assign_driver(db, order_id)

    if driver:
        order.status = OrderStatus.PREPARING
    # If no driver found, order status is updated to WAITING_FOR_DRIVER in assign_driver
    # We do NOT raise 404 anymore.

    db.commit() # Commit the status change made by assign_driver or the PREPARING status

    order = db.query(Order).options(
        joinedload(Order.customer),
        joinedload(Order.driver),
        joinedload(Order.restaurant),
        joinedload(Order.items)
    ).filter(Order.id == order_id).first()
    return order

# ----------------------------
# UPDATE ORDER STATUS
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

    # ✅ Validate first
    if status not in ALLOWED_RESTAURANT_STATUSES:
        raise HTTPException(
            status_code=403,
            detail="Invalid status for restaurant"
        )

    # ✅ Then update
    order = update_order_status(db, order_id, status)
    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    return {
        "order_id": order.id,
        "status": order.status
    }



# ----------------------------
# DRIVER VIEW: GET JOBS
# ----------------------------
@router.get("/driver/jobs", response_model=list[OrderRead])
def driver_jobs(
    db: Session = Depends(get_db),
    user = Depends(require_role(Role.DRIVER))
):
    """
    Driver sees all assigned orders that are not delivered/cancelled.
    """
    orders = db.query(Order).options(
        joinedload(Order.customer),
        joinedload(Order.driver),
        joinedload(Order.restaurant),
        joinedload(Order.items)
    ).filter(
        Order.driver_id == user.id,
        Order.status.notin_(["delivered","cancelled"])
    ).all()
    return orders

@router.get("/driver/history", response_model=list[OrderRead])
def driver_history(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    user = Depends(require_role(Role.DRIVER))
):
    """
    Driver sees ALL assigned orders (history).
    """
    orders = db.query(Order).options(
        joinedload(Order.customer),
        joinedload(Order.driver),
        joinedload(Order.restaurant),
        selectinload(Order.items)
    ).filter(
        Order.driver_id == user.id
    ).order_by(Order.created_at.desc()).offset(offset).limit(limit).all()
    return orders

# ----------------------------
# CUSTOMER VIEW: GET MY ORDERS
# ----------------------------
@router.get("/my", response_model=list[OrderRead])
def my_orders(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    user = Depends(require_role(Role.CUSTOMER))
):
    """
    Customer sees all their orders.
    """
    orders = db.query(Order).options(
        joinedload(Order.customer),
        joinedload(Order.driver),
        joinedload(Order.restaurant),
        selectinload(Order.items)
    ).filter(Order.customer_id == user.id).order_by(Order.created_at.desc()).offset(offset).limit(limit).all()
    return orders
