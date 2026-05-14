from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.driver import DriverProfileCreate, DriverRead
from app.services.driver_service import (
    create_driver_profile,
    get_available_driver,
    set_driver_availability,
    get_driver_profile
)
from app.services.order_service import update_order_status
from app.core.dependencies import require_role, get_current_user
from app.core.roles import Role
from app.core.dependencies import get_db

router = APIRouter(tags=["Drivers"])

# ----------------------------
# CREATE DRIVER PROFILE
# ----------------------------
@router.post("/profile", response_model=DriverRead)
def create_profile(
    payload: DriverProfileCreate,
    db: Session = Depends(get_db),
    user = Depends(require_role(Role.DRIVER))
):
    """
    Create or update driver profile with vehicle type.
    """
    return create_driver_profile(db, user.id, payload.vehicle_type)

@router.get("/profile", response_model=DriverRead)
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
    Driver can set themselves available or unavailable.
    """
    driver = set_driver_availability(db, user.id, available)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    return {"user_id": driver.id, "is_available": driver.is_available}

# ----------------------------
# GET AVAILABLE DRIVER (FOR TEST / ADMIN)
# ----------------------------
@router.get("/available", response_model=DriverRead)
def available_driver(db: Session = Depends(get_db)):
    """
    Get first available driver (cached in Redis)
    """
    driver = get_available_driver(db)
    if not driver:
        raise HTTPException(status_code=404, detail="No drivers available")
    return driver

# ----------------------------
# DRIVER: UPDATE ORDER STATUS
# ----------------------------
@router.post("/orders/{order_id}/status")
def update_status(
    order_id: str,
    status: str,  # "picked_up" or "delivered"
    db: Session = Depends(get_db),
    user = Depends(require_role(Role.DRIVER))
):
    """
    Driver updates the status of an assigned order.
    """
    order = update_order_status(db, order_id, status)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.driver_id != user.id:
        raise HTTPException(status_code=403, detail="This order is not assigned to you")
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

    # 3. Earnings (Sum of totals for delivered orders)
    # Note: In real app, this should be a split (e.g. 20%). For now, we show total order value handled.
    earnings = db.query(func.sum(Order.total_amount)).filter(
        Order.driver_id == user.id,
        Order.status == "delivered"
    ).scalar() or 0.0

    return {
        "today_deliveries": today_count,
        "completed_deliveries": completed_count,
        "total_earnings": float(earnings),
        "reliability_score": 100 # Mock for now
    }
