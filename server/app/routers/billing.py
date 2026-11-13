"""
Platform owner's side of subscriptions: create plans, see who is paid up,
record EFT / cash payments, suspend or reactivate a restaurant.
Also receives PayFast's notifications for subscription charges.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.dependencies import get_db, require_role
from app.core.roles import Role
from app.models.restaurant import Restaurant
from app.models.subscription import SubscriptionPayment
from app.schemas.billing import (
    AdminSubscriptionUpdate,
    ManualPayment,
    PlanCreate,
    PlanRead,
    PlanUpdate,
    SubscriptionPaymentRead,
    SubscriptionRead,
)
from app.services import payfast, subscription_service as subs

router = APIRouter(tags=["Billing"])

admin_only = require_role(Role.SUPER_ADMIN)


def _restaurant(db: Session, restaurant_id: str) -> Restaurant:
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return restaurant


# ---------------- plans ----------------
@router.get("/admin/billing/plans", response_model=List[PlanRead])
def admin_list_plans(db: Session = Depends(get_db), admin=Depends(admin_only)):
    return subs.list_plans(db, include_inactive=True)


@router.post("/admin/billing/plans", response_model=PlanRead)
def admin_create_plan(payload: PlanCreate, db: Session = Depends(get_db), admin=Depends(admin_only)):
    return subs.create_plan(db, payload.model_dump())


@router.patch("/admin/billing/plans/{plan_id}", response_model=PlanRead)
def admin_update_plan(plan_id: str, payload: PlanUpdate, db: Session = Depends(get_db), admin=Depends(admin_only)):
    return subs.update_plan(db, plan_id, payload.model_dump(exclude_unset=True))


@router.delete("/admin/billing/plans/{plan_id}")
def admin_delete_plan(plan_id: str, db: Session = Depends(get_db), admin=Depends(admin_only)):
    outcome = subs.delete_plan(db, plan_id)
    if outcome == "retired":
        return {"message": "Restaurants have used this plan, so it was retired (hidden from new sign-ups) instead of deleted"}
    return {"message": "Plan deleted"}


# ---------------- subscriptions ----------------
@router.get("/admin/billing/subscriptions", response_model=List[SubscriptionRead])
def admin_list_subscriptions(db: Session = Depends(get_db), admin=Depends(admin_only)):
    """Every restaurant with its plan and payment state, including ones with no plan yet."""
    restaurants = db.query(Restaurant).order_by(Restaurant.name.asc()).all()
    return [subs.describe(db, restaurant) for restaurant in restaurants]


@router.put("/admin/billing/restaurants/{restaurant_id}/subscription", response_model=SubscriptionRead)
def admin_set_subscription(
    restaurant_id: str,
    payload: AdminSubscriptionUpdate,
    db: Session = Depends(get_db),
    admin=Depends(admin_only),
):
    restaurant = _restaurant(db, restaurant_id)
    subs.admin_set_subscription(db, restaurant, payload.model_dump(exclude_unset=True))
    return subs.describe(db, restaurant)


@router.post("/admin/billing/restaurants/{restaurant_id}/payments", response_model=SubscriptionRead)
def admin_record_payment(
    restaurant_id: str,
    payload: ManualPayment,
    db: Session = Depends(get_db),
    admin=Depends(admin_only),
):
    """Record a subscription payment received by EFT or cash; adds one billing cycle."""
    restaurant = _restaurant(db, restaurant_id)
    subs.record_manual_payment(db, restaurant, payload.plan_id, payload.amount, payload.note)
    return subs.describe(db, restaurant)


@router.get("/admin/billing/restaurants/{restaurant_id}/payments", response_model=List[SubscriptionPaymentRead])
def admin_payment_history(restaurant_id: str, db: Session = Depends(get_db), admin=Depends(admin_only)):
    return db.query(SubscriptionPayment).filter(
        SubscriptionPayment.restaurant_id == restaurant_id
    ).order_by(SubscriptionPayment.created_at.desc()).limit(100).all()


# ---------------- PayFast webhook for subscription charges ----------------
@router.post("/billing/payfast/notify", include_in_schema=False)
async def subscription_payfast_notify(request: Request, db: Session = Depends(get_db)):
    pairs = payfast.parse_itn_body(await request.body())
    forwarded = request.headers.get("x-forwarded-for")
    remote_ip = forwarded.split(",")[0].strip() if forwarded and settings.is_production else (
        request.client.host if request.client else ""
    )
    await run_in_threadpool(subs.handle_subscription_itn, db, pairs, remote_ip)
    return Response(status_code=200)
