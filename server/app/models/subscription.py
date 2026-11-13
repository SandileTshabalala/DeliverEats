import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.db.base import Base


def utcnow() -> datetime:
    """Naive UTC, matching the other DateTime columns in this project."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class SubscriptionPlan(Base):
    """A plan the platform owner creates and restaurants subscribe to."""
    __tablename__ = "subscription_plans"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    # Billing cycle length. PayFast recurring billing supports 1, 3, 6 or 12 months.
    interval_months = Column(Integer, nullable=False, default=1)
    # Free days for a restaurant's first ever subscription (0 = no trial)
    trial_days = Column(Integer, nullable=False, default=0)
    # None = unlimited orders
    max_orders_per_month = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=utcnow)


class RestaurantSubscription(Base):
    """One row per restaurant: which plan it is on and until when it is paid."""
    __tablename__ = "restaurant_subscriptions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    restaurant_id = Column(String, ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    plan_id = Column(String, ForeignKey("subscription_plans.id"), nullable=False)
    # Stored: trialing | active | suspended | cancelled.
    # "past_due" and "expired" are worked out from current_period_end when read.
    status = Column(String, nullable=False, default="trialing")
    current_period_end = Column(DateTime, nullable=False)
    payfast_token = Column(String, nullable=True)  # recurring billing token
    note = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    plan = relationship("SubscriptionPlan")
    restaurant = relationship("Restaurant", backref="subscription_rows")


class SubscriptionPayment(Base):
    """Every subscription charge, whether through PayFast or recorded by the admin (EFT, cash)."""
    __tablename__ = "subscription_payments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    restaurant_id = Column(String, ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(String, ForeignKey("subscription_plans.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String, nullable=False, default="pending")  # pending | completed | failed
    method = Column(String, nullable=False, default="payfast")  # payfast | manual
    # First charge of a PayFast subscription: id of that pending row. Renewals point back to it.
    parent_id = Column(String, nullable=True, index=True)
    reference = Column(String, nullable=True, index=True)  # PayFast pf_payment_id, or the admin's note
    created_at = Column(DateTime, default=utcnow)

    plan = relationship("SubscriptionPlan")
