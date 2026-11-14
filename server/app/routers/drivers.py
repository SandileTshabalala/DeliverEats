from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.driver import DriverProfileCreate, DriverProfileRead, DriverRead
from app.services.driver_service import (
    create_driver_profile,
    has_active_delivery,
    set_driver_availability,
    get_driver_profile
)
from app.models.driver import Driver
from app.models.order import Order
from app.utils.OrderStatus import OrderStatus
from app.services.order_service import update_order_status
from app.core.dependencies import require_role, get_current_user
from app.core.roles import Role
from app.core.dependencies import get_db

router = APIRouter(tags=["Drivers"])

# ----------------------------
# CREATE DRIVER PROFILE
# ----------------------------
@router.post("/profile", response_model=DriverProfileRead)
def create_profile(
    payload: DriverProfileCreate,
    db: Session = Depends(get_db),
    user = Depends(require_role(Role.DRIVER))
):
    """
    Create or update driver profile with vehicle type.
    """
    return create_driver_profile(db, user.id, payload.vehicle_type, payload.vehicle_number)

@router.get("/profile", response_model=DriverProfileRead)
def get_profile(
    db: Session = Depends(get_db),
    user = Depends(require_role(Role.DRIVER))
):
    """
    Get current driver's profile.
    """
    driver = get_driver_profile(db, user.id)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    return driver

# ----------------------------
# TOGGLE DRIVER AVAILABILITY
# ----------------------------
@router.post("/availability")
def toggle_availability(
    available: bool,
    db: Session = Depends(get_db),
    user = Depends(require_role(Role.DRIVER))
):
    """
    Driver goes online or offline. This never fails because of a delivery in
    progress: going offline mid-delivery just means no NEW jobs after this one.
    """
    driver = set_driver_availability(db, user.id, available)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    return {
        "user_id": driver.id,
        "is_available": driver.is_available,  # online / offline: the driver's own choice
        "on_delivery": has_active_delivery(db, user.id),
    }

# ----------------------------
# GET AVAILABLE DRIVER (FOR TEST / ADMIN)
# ----------------------------
@router.get("/available", response_model=DriverRead)
def available_driver(
    db: Session = Depends(get_db),
    admin = Depends(require_role(Role.SUPER_ADMIN))
):
    """
    Admin only: peek at the next driver in line. Read-only, it does not reserve them.
    """
    driver = (
        db.query(Driver)
        .filter(Driver.is_available == True)
        .order_by(Driver.last_assigned_at.asc().nullsfirst())
        .first()
    )
    if not driver:
        raise HTTPException(status_code=404, detail="No drivers available")
    return driver

# ----------------------------
# DRIVER: UPDATE ORDER STATUS
# ----------------------------
@router.post("/orders/{order_id}/status")
def update_status(
    order_id: str,
    status: OrderStatus,  # "picked_up" or "delivered"
    db: Session = Depends(get_db),
    user = Depends(require_role(Role.DRIVER))
):
    """
    Driver updates the status of an order assigned to them.
    """
    if status not in (OrderStatus.PICKED_UP, OrderStatus.DELIVERED):
        raise HTTPException(status_code=403, detail="Drivers can only mark orders as picked up or delivered")

    # Check ownership BEFORE changing anything
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order or order.driver_id != user.id:
        raise HTTPException(status_code=404, detail="Order not found")

    order = update_order_status(db, order_id, status, order=order)
    return {"order_id": order.id, "status": order.status}

# ----------------------------
# DRIVER STATS
# ----------------------------
from app.models.order import Order
from sqlalchemy import func
from datetime import datetime
from app.schemas.driver import DriverStats

@router.get("/stats", response_model=DriverStats)
def get_stats(
    db: Session = Depends(get_db),
    user = Depends(require_role(Role.DRIVER))
):
    """
    Get dashboard stats for the driver.
    """
    # 1. Today's Deliveries (Created today and assigned to driver)
    today = datetime.utcnow().date()
    today_count = db.query(Order).filter(
        Order.driver_id == user.id,
        func.date(Order.created_at) == today
    ).count()

    # 2. Total Completed
    completed_count = db.query(Order).filter(
        Order.driver_id == user.id,
        Order.status == "delivered"
    ).count()

    finished_count = db.query(Order).filter(
        Order.driver_id == user.id,
        Order.status.in_(["delivered", "cancelled"])
    ).count()

    # 3. Earnings: the delivery fees of the orders this driver delivered.
    # (Previously this summed the full order totals, i.e. the restaurants' money.)
    earnings = db.query(func.sum(Order.delivery_fee)).filter(
        Order.driver_id == user.id,
        Order.status == "delivered"
    ).scalar() or 0.0

    return {
        "today_deliveries": today_count,
        "completed_deliveries": completed_count,
        "total_earnings": float(earnings),
        # Share of this driver's finished jobs that were delivered (not cancelled)
        "reliability_score": round(100 * completed_count / finished_count) if finished_count else 0
    }
