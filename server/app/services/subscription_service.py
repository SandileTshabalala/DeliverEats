"""
Restaurant subscriptions: the platform's only income.

Order money goes straight to each restaurant. Restaurants pay the platform a
subscription for one of the plans the owner creates in the admin panel, either
through PayFast recurring billing (on the PLATFORM's PayFast account) or by
EFT / cash that the admin records by hand.

Nothing is enforced until SUBSCRIPTIONS_ENFORCED=true, so existing restaurants
keep working while plans are being set up.
"""
import calendar
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.locger import logger
from app.models.order import Order
from app.models.restaurant import Restaurant
from app.models.subscription import (
    RestaurantSubscription,
    SubscriptionPayment,
    SubscriptionPlan,
    utcnow,
)
from app.services import payfast
from app.services.notification_service import send_notification
from app.utils.OrderStatus import OrderStatus

# Effective statuses in which a restaurant is open for business
LIVE_STATUSES = ("trialing", "active", "past_due")

# plan.interval_months -> PayFast "frequency" code
PAYFAST_FREQUENCY = {1: 3, 3: 4, 6: 5, 12: 6}


def add_months(moment: datetime, months: int) -> datetime:
    month_index = moment.month - 1 + months
    year = moment.year + month_index // 12
    month = month_index % 12 + 1
    day = min(moment.day, calendar.monthrange(year, month)[1])
    return moment.replace(year=year, month=month, day=day)


# --------------------------------------------------------------------------
# Reading state
# --------------------------------------------------------------------------
def get_subscription(db: Session, restaurant_id: str) -> Optional[RestaurantSubscription]:
    return db.query(RestaurantSubscription).filter(
        RestaurantSubscription.restaurant_id == restaurant_id
    ).first()


def effective_status(subscription: Optional[RestaurantSubscription], now: Optional[datetime] = None) -> str:
    """
    none | trialing | active | past_due | expired | suspended | cancelled

    past_due = the period has ended but the grace days have not: still open.
    expired  = grace is over as well: closed until a payment arrives.
    """
    if subscription is None:
        return "none"
    if subscription.status in ("suspended", "cancelled"):
        return subscription.status
    now = now or utcnow()
    if now <= subscription.current_period_end:
        return subscription.status
    if now <= subscription.current_period_end + timedelta(days=settings.SUBSCRIPTION_GRACE_DAYS):
        return "past_due"
    return "expired"


def orders_this_month(db: Session, restaurant_id: str) -> int:
    start = utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return db.query(Order).filter(
        Order.restaurant_id == restaurant_id,
        Order.created_at >= start,
        Order.status != OrderStatus.CANCELLED,
    ).count()


def is_restaurant_live(db: Session, restaurant: Restaurant) -> bool:
    """Should customers be able to see and order from this restaurant?"""
    if not restaurant.is_active:
        return False
    if not settings.SUBSCRIPTIONS_ENFORCED:
        return True
    return effective_status(get_subscription(db, restaurant.id)) in LIVE_STATUSES


def ensure_can_take_orders(db: Session, restaurant: Restaurant) -> None:
    """Raise if the restaurant may not receive a new order right now."""
    if not settings.SUBSCRIPTIONS_ENFORCED:
        return
    subscription = get_subscription(db, restaurant.id)
    if effective_status(subscription) not in LIVE_STATUSES:
        raise HTTPException(status_code=409, detail="This restaurant is not taking orders at the moment")
    limit = subscription.plan.max_orders_per_month if subscription.plan else None
    if limit is not None and orders_this_month(db, restaurant.id) >= limit:
        # Deliberately vague for customers; the restaurant sees the real reason on its dashboard
        raise HTTPException(status_code=409, detail="This restaurant is not taking more orders at the moment")


def describe(db: Session, restaurant: Restaurant) -> dict:
    """Everything the restaurant's billing screen and the admin list need."""
    subscription = get_subscription(db, restaurant.id)
    status = effective_status(subscription)
    plan = subscription.plan if subscription else None
    used = orders_this_month(db, restaurant.id)
    limit = plan.max_orders_per_month if plan else None
    return {
        "restaurant_id": restaurant.id,
        "restaurant_name": restaurant.name,
        "status": status,
        "is_live": is_restaurant_live(db, restaurant),
        "enforced": settings.SUBSCRIPTIONS_ENFORCED,
        "grace_days": settings.SUBSCRIPTION_GRACE_DAYS,
        "plan": plan,
        "current_period_end": subscription.current_period_end if subscription else None,
        "auto_renews": bool(subscription and subscription.payfast_token and subscription.status == "active"),
        # A PayFast debit order is running: starting another checkout would charge twice every month
        "recurring_active": bool(subscription and subscription.payfast_token),
        "orders_this_month": used,
        "orders_limit": limit,
        "limit_reached": limit is not None and used >= limit,
        "note": subscription.note if subscription else None,
    }


# --------------------------------------------------------------------------
# Plans (admin)
# --------------------------------------------------------------------------
def list_plans(db: Session, include_inactive: bool = False) -> List[SubscriptionPlan]:
    query = db.query(SubscriptionPlan)
    if not include_inactive:
        query = query.filter(SubscriptionPlan.is_active == True)
    return query.order_by(SubscriptionPlan.sort_order.asc(), SubscriptionPlan.price.asc()).all()


def get_plan(db: Session, plan_id: str) -> SubscriptionPlan:
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


def create_plan(db: Session, data: dict) -> SubscriptionPlan:
    if db.query(SubscriptionPlan).filter(SubscriptionPlan.name == data["name"]).first():
        raise HTTPException(status_code=400, detail="A plan with that name already exists")
    plan = SubscriptionPlan(**data)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def update_plan(db: Session, plan_id: str, data: dict) -> SubscriptionPlan:
    plan = get_plan(db, plan_id)
    if "name" in data and data["name"] != plan.name:
        if db.query(SubscriptionPlan).filter(SubscriptionPlan.name == data["name"]).first():
            raise HTTPException(status_code=400, detail="A plan with that name already exists")
    for key, value in data.items():
        setattr(plan, key, value)
    db.commit()
    db.refresh(plan)
    return plan


def delete_plan(db: Session, plan_id: str) -> str:
    """Delete an unused plan; a plan somebody is (or was) on is only retired."""
    plan = get_plan(db, plan_id)
    in_use = (
        db.query(RestaurantSubscription).filter(RestaurantSubscription.plan_id == plan_id).first()
        or db.query(SubscriptionPayment).filter(SubscriptionPayment.plan_id == plan_id).first()
    )
    if in_use:
        plan.is_active = False
        db.commit()
        return "retired"
    db.delete(plan)
    db.commit()
    return "deleted"


# --------------------------------------------------------------------------
# Changing a restaurant's subscription
# --------------------------------------------------------------------------
def _invalidate_restaurant_list() -> None:
    try:
        from app.core.redis import redis_client
        redis_client.delete("lvovo:restaurants:list")
    except Exception:
        pass


def extend_subscription(db: Session, restaurant_id: str, plan: SubscriptionPlan, token: Optional[str] = None) -> RestaurantSubscription:
    """A payment arrived: move the paid-until date forward by one billing cycle."""
    now = utcnow()
    subscription = get_subscription(db, restaurant_id)
    if subscription is None:
        subscription = RestaurantSubscription(restaurant_id=restaurant_id, plan_id=plan.id, current_period_end=now)
        db.add(subscription)

    # Paying early (or during a trial) adds to the time already paid for
    start = subscription.current_period_end if subscription.current_period_end and subscription.current_period_end > now else now
    subscription.current_period_end = add_months(start, plan.interval_months)
    subscription.plan_id = plan.id
    subscription.status = "active"
    if token:
        subscription.payfast_token = token
    db.commit()
    db.refresh(subscription)
    _invalidate_restaurant_list()

    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if restaurant:
        send_notification(
            restaurant.admin_id, "Subscription payment received",
            f"Thank you. {restaurant.name} is on the {plan.name} plan, paid until "
            f"{subscription.current_period_end:%d %B %Y}.",
            sms=False, email=True,
        )
    return subscription


def send_subscription_reminders(db: Session) -> int:
    """
    Run a few times a day by the scheduler. Each restaurant is told once per
    billing period for each stage: ending soon, overdue (grace days), closed.
    Restaurants on automatic PayFast renewal are not nagged before the due date.
    """
    from app.core.redis import redis_client

    now = utcnow()
    sent = 0
    for subscription in db.query(RestaurantSubscription).all():
        restaurant = subscription.restaurant
        if not restaurant or not restaurant.admin_id or not restaurant.is_active:
            continue
        status = effective_status(subscription, now)
        end = subscription.current_period_end
        days_left = (end - now).days

        stage = text = None
        if status in ("trialing", "active") and 0 <= days_left <= 3 and not subscription.payfast_token:
            what = "free trial" if status == "trialing" else "plan"
            stage, text = "ending", f"Your {what} for {restaurant.name} ends on {end:%d %b}. Pay in Settings to stay open."
        elif status == "past_due":
            stage, text = "overdue", (
                f"Payment for {restaurant.name} is overdue. You will be hidden from customers on "
                f"{end + timedelta(days=settings.SUBSCRIPTION_GRACE_DAYS):%d %b} unless you pay in Settings."
            )
        elif status == "expired":
            stage, text = "closed", f"{restaurant.name} is now hidden from customers because the plan was not paid. Pay in Settings to reopen."
        if not stage:
            continue

        key = f"lvovo:subscription_reminder:{subscription.id}:{end:%Y%m%d}:{stage}"
        try:
            if not redis_client.set(key, "1", nx=True, ex=60 * 60 * 24 * 45):
                continue  # already told about this stage
        except Exception:
            continue  # without Redis we cannot dedupe: better silent than spamming
        send_notification(
            restaurant.admin_id, "Subscription", text, sms=True, email=True,
            button_label="Open settings", button_url=f"{settings.FRONTEND_URL.rstrip('/')}/restaurant/settings",
        )
        sent += 1
    return sent


def ensure_invoice_number(db: Session, payment: SubscriptionPayment) -> None:
    """
    Give a completed payment the next invoice number, once. Numbers follow the
    order payments were completed in, never change and are never reused.
    """
    if payment.status != "completed" or payment.invoice_number:
        return
    from sqlalchemy.exc import IntegrityError
    for _ in range(5):  # two payments completing at the same moment: retry with the next number
        payment.invoice_number = (db.query(func.max(SubscriptionPayment.invoice_number)).scalar() or 0) + 1
        try:
            db.commit()
            return
        except IntegrityError:
            db.rollback()
    raise RuntimeError("Could not assign an invoice number")


def record_manual_payment(db: Session, restaurant: Restaurant, plan_id: str, amount: Optional[Decimal], note: Optional[str]) -> RestaurantSubscription:
    """Admin received an EFT / cash payment outside PayFast."""
    plan = get_plan(db, plan_id)
    payment = SubscriptionPayment(
        restaurant_id=restaurant.id,
        plan_id=plan.id,
        amount=amount if amount is not None else plan.price,
        status="completed",
        method="manual",
        reference=(note or "Recorded by admin")[:250],
    )
    db.add(payment)
    subscription = extend_subscription(db, restaurant.id, plan)
    ensure_invoice_number(db, payment)
    return subscription


def admin_set_subscription(db: Session, restaurant: Restaurant, data: dict) -> RestaurantSubscription:
    """Admin override: put a restaurant on a plan, change status or the paid-until date."""
    subscription = get_subscription(db, restaurant.id)
    plan_id = data.get("plan_id") or (subscription.plan_id if subscription else None)
    if not plan_id:
        raise HTTPException(status_code=400, detail="Choose a plan for this restaurant")
    plan = get_plan(db, plan_id)

    if subscription is None:
        subscription = RestaurantSubscription(
            restaurant_id=restaurant.id,
            plan_id=plan.id,
            status="trialing" if plan.trial_days else "active",
            current_period_end=utcnow() + timedelta(days=plan.trial_days) if plan.trial_days else add_months(utcnow(), plan.interval_months),
        )
        db.add(subscription)

    subscription.plan_id = plan.id
    if data.get("stop_recurring"):
        # The admin cancelled the debit order on PayFast: the restaurant may now check out again
        subscription.payfast_token = None
    if data.get("status"):
        subscription.status = data["status"]
    if data.get("current_period_end"):
        subscription.current_period_end = data["current_period_end"].replace(tzinfo=None)
    if "note" in data:
        subscription.note = data["note"]
    db.commit()
    db.refresh(subscription)
    _invalidate_restaurant_list()
    return subscription


# --------------------------------------------------------------------------
# Restaurant self-service
# --------------------------------------------------------------------------
def platform_payfast_credentials() -> Optional[payfast.PayFastCredentials]:
    """The PLATFORM's own PayFast account (from the environment): subscriptions are paid into it."""
    if not (settings.PAYFAST_MERCHANT_ID and settings.PAYFAST_MERCHANT_KEY):
        return None
    return payfast.PayFastCredentials(
        merchant_id=settings.PAYFAST_MERCHANT_ID.strip(),
        merchant_key=settings.PAYFAST_MERCHANT_KEY.strip(),
        passphrase=(settings.PAYFAST_PASSPHRASE or "").strip() or None,
        sandbox=settings.PAYFAST_SANDBOX,
    )


def subscribe(db: Session, restaurant: Restaurant, plan_id: str, user) -> dict:
    """
    Restaurant picks a plan.
    - First ever subscription on a plan with trial days: the trial starts, nothing to pay yet.
    - Otherwise: returns a signed PayFast recurring-billing form to post.
    """
    plan = get_plan(db, plan_id)
    if not plan.is_active:
        raise HTTPException(status_code=400, detail="That plan is no longer offered")

    subscription = get_subscription(db, restaurant.id)
    if subscription is not None and subscription.payfast_token:
        raise HTTPException(
            status_code=409,
            detail="Your plan is already paid automatically by PayFast every month. To change plan, contact us "
                   "first so we stop the current debit order and you are not charged twice.",
        )
    if subscription is None and plan.trial_days > 0:
        subscription = RestaurantSubscription(
            restaurant_id=restaurant.id,
            plan_id=plan.id,
            status="trialing",
            current_period_end=utcnow() + timedelta(days=plan.trial_days),
        )
        db.add(subscription)
        db.commit()
        _invalidate_restaurant_list()
        return {"action": "trial_started", "checkout_url": None, "checkout_fields": None}

    if Decimal(plan.price) <= 0:
        extend_subscription(db, restaurant.id, plan)
        return {"action": "activated", "checkout_url": None, "checkout_fields": None}

    creds = platform_payfast_credentials()
    frequency = PAYFAST_FREQUENCY.get(plan.interval_months)
    if not creds or not frequency:
        raise HTTPException(
            status_code=503,
            detail="Online subscription payment is not available yet. Please contact us to pay by EFT."
        )

    payment = SubscriptionPayment(
        restaurant_id=restaurant.id, plan_id=plan.id, amount=plan.price, status="pending", method="payfast"
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    frontend = settings.FRONTEND_URL.rstrip("/")
    api = settings.PUBLIC_API_URL.rstrip("/")
    url, fields = payfast.build_checkout(
        creds,
        payment_id=payment.id,
        amount=plan.price,
        item_name=f"{plan.name} plan - {restaurant.name}",
        item_description=f"Subscription billed every {plan.interval_months} month(s)",
        return_url=f"{frontend}/restaurant/payment?status=success",
        cancel_url=f"{frontend}/restaurant/payment?status=cancelled",
        notify_url=f"{api}{settings.API_V1_STR}/billing/payfast/notify",
        name_first=user.name,
        name_last=user.sur_name,
        email_address=user.email,
        order_id=restaurant.id,
        extra_fields={
            "subscription_type": "1",  # recurring
            "recurring_amount": payfast.format_amount(plan.price),
            "frequency": str(frequency),
            "cycles": "0",  # until cancelled
        },
    )
    return {"action": "checkout", "checkout_url": url, "checkout_fields": fields}


def handle_subscription_itn(db: Session, pairs: List[Tuple[str, str]], remote_ip: Optional[str]) -> None:
    """
    PayFast notification for a subscription charge: the first payment and every
    automatic renewal after it (renewals reuse the first payment's m_payment_id).
    """
    data = dict(pairs)
    first = db.query(SubscriptionPayment).filter(SubscriptionPayment.id == data.get("m_payment_id")).first()
    if not first:
        logger.warning(f"Subscription ITN for unknown payment {data.get('m_payment_id')!r}")
        return

    creds = platform_payfast_credentials()
    if not creds:
        logger.error("Subscription ITN received but the platform PayFast account is not configured")
        return

    ok, reason = payfast.validate_itn(
        creds, pairs, expected_amount=first.amount, remote_ip=remote_ip, check_source_ip=not creds.sandbox
    )
    if not ok:
        logger.warning(f"Subscription ITN rejected for payment {first.id}: {reason}")
        return

    status = (data.get("payment_status") or "").upper()
    pf_payment_id = data.get("pf_payment_id")

    if status == "COMPLETE":
        # Two notifications for the same charge can arrive at the same moment: handle them one at a time
        first = db.query(SubscriptionPayment).filter(SubscriptionPayment.id == first.id).with_for_update().one()
        # PayFast repeats notifications: each real charge has its own pf_payment_id
        if pf_payment_id and db.query(SubscriptionPayment).filter(
            SubscriptionPayment.reference == pf_payment_id, SubscriptionPayment.status == "completed"
        ).first():
            return
        if first.status == "pending":
            first.status = "completed"
            first.reference = pf_payment_id
            charged = first
        else:
            charged = SubscriptionPayment(
                restaurant_id=first.restaurant_id, plan_id=first.plan_id, amount=first.amount,
                status="completed", method="payfast", parent_id=first.id, reference=pf_payment_id,
            )
            db.add(charged)
        try:
            db.commit()
        except IntegrityError:
            # the database already holds this pf_payment_id (unique): a repeat, nothing more to do
            db.rollback()
            return
        ensure_invoice_number(db, charged)
        extend_subscription(db, first.restaurant_id, first.plan, token=data.get("token"))
    elif status in ("FAILED", "CANCELLED"):
        if first.status == "pending":
            first.status = "failed"
            db.commit()
        if status == "CANCELLED":
            # Recurring billing was cancelled at PayFast: stays open until the paid period ends
            subscription = get_subscription(db, first.restaurant_id)
            if subscription and subscription.payfast_token == data.get("token"):
                subscription.payfast_token = None
                db.commit()
