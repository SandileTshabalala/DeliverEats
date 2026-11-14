from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


# ---------------- plans ----------------
class PlanBase(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    description: Optional[str] = Field(default=None, max_length=500)
    price: Decimal = Field(ge=0)
    interval_months: Literal[1, 3, 6, 12] = 1
    trial_days: int = Field(default=0, ge=0, le=365)
    max_orders_per_month: Optional[int] = Field(default=None, ge=1)
    is_active: bool = True
    sort_order: int = 0


class PlanCreate(PlanBase):
    pass


class PlanUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=60)
    description: Optional[str] = Field(default=None, max_length=500)
    price: Optional[Decimal] = Field(default=None, ge=0)
    interval_months: Optional[Literal[1, 3, 6, 12]] = None
    trial_days: Optional[int] = Field(default=None, ge=0, le=365)
    max_orders_per_month: Optional[int] = Field(default=None, ge=1)
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None

    class Config:
        extra = "forbid"


class PlanRead(PlanBase):
    id: str

    class Config:
        from_attributes = True


# ---------------- subscriptions ----------------
class SubscriptionRead(BaseModel):
    restaurant_id: str
    restaurant_name: str
    # none | trialing | active | past_due | expired | suspended | cancelled
    status: str
    is_live: bool
    enforced: bool
    grace_days: int
    plan: Optional[PlanRead] = None
    current_period_end: Optional[datetime] = None
    auto_renews: bool = False
    recurring_active: bool = False
    orders_this_month: int = 0
    orders_limit: Optional[int] = None
    limit_reached: bool = False
    note: Optional[str] = None


class BillingOverview(BaseModel):
    subscription: SubscriptionRead
    plans: list[PlanRead]
    online_payment_available: bool


class SubscribeRequest(BaseModel):
    plan_id: str


class SubscribeResponse(BaseModel):
    action: Literal["trial_started", "activated", "checkout"]
    checkout_url: Optional[str] = None
    checkout_fields: Optional[dict] = None


class AdminSubscriptionUpdate(BaseModel):
    plan_id: Optional[str] = None
    status: Optional[Literal["trialing", "active", "suspended", "cancelled"]] = None
    current_period_end: Optional[datetime] = None
    note: Optional[str] = Field(default=None, max_length=500)
    # set after cancelling the restaurant's debit order on the PayFast dashboard
    stop_recurring: Optional[bool] = None

    class Config:
        extra = "forbid"


class ManualPayment(BaseModel):
    plan_id: str
    amount: Optional[Decimal] = Field(default=None, ge=0)
    note: Optional[str] = Field(default=None, max_length=250)


class SubscriptionPaymentRead(BaseModel):
    id: str
    restaurant_id: str
    amount: Decimal
    status: str
    method: str
    reference: Optional[str] = None
    invoice_number: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------- restaurant payment methods ----------------
class PaymentSettingsRead(BaseModel):
    accepts_cash: bool
    accepts_card_machine: bool
    payfast_enabled: bool
    payfast_merchant_id: Optional[str] = None
    payfast_merchant_key: Optional[str] = None  # mask only
    payfast_passphrase: Optional[str] = None  # mask only
    payfast_sandbox: bool
    ozow_enabled: bool = False
    ozow_site_code: Optional[str] = None
    ozow_client_id: Optional[str] = None
    ozow_client_secret: Optional[str] = None  # mask only
    ozow_sandbox: bool = False
    peach_enabled: bool = False
    peach_entity_id: Optional[str] = None
    peach_secret_token: Optional[str] = None  # mask only
    peach_sandbox: bool = False


class PaymentSettingsUpdate(BaseModel):
    accepts_cash: Optional[bool] = None
    accepts_card_machine: Optional[bool] = None
    payfast_enabled: Optional[bool] = None
    payfast_merchant_id: Optional[str] = Field(default=None, max_length=40)
    payfast_merchant_key: Optional[str] = Field(default=None, max_length=80)
    payfast_passphrase: Optional[str] = Field(default=None, max_length=80)
    payfast_sandbox: Optional[bool] = None
    ozow_enabled: Optional[bool] = None
    ozow_site_code: Optional[str] = Field(default=None, max_length=50)
    ozow_client_id: Optional[str] = Field(default=None, max_length=200)
    ozow_client_secret: Optional[str] = Field(default=None, max_length=500)
    ozow_sandbox: Optional[bool] = None
    peach_enabled: Optional[bool] = None
    peach_entity_id: Optional[str] = Field(default=None, max_length=32)
    peach_secret_token: Optional[str] = Field(default=None, max_length=200)
    peach_sandbox: Optional[bool] = None

    class Config:
        extra = "forbid"


# ---------------- restaurant delivery fee ----------------
class DeliverySettingsRead(BaseModel):
    base_fee: Decimal
    per_km_fee: Decimal
    free_delivery_over: Optional[Decimal] = None
    max_distance_km: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class DeliverySettingsUpdate(BaseModel):
    base_fee: Optional[Decimal] = Field(default=None, ge=0, le=1000)
    per_km_fee: Optional[Decimal] = Field(default=None, ge=0, le=200)
    free_delivery_over: Optional[Decimal] = Field(default=None, gt=0)
    max_distance_km: Optional[float] = Field(default=None, gt=0, le=200)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)

    class Config:
        extra = "forbid"


# ---------------- team ----------------
class TeamMemberCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1)
    sur_name: str = Field(min_length=1)
    contact_number: str = Field(min_length=5)


class DriverCreate(TeamMemberCreate):
    vehicle_type: str = Field(min_length=1, max_length=40)
    vehicle_number: Optional[str] = Field(default=None, max_length=20)


class TeamMemberRead(BaseModel):
    id: str
    email: str
    name: str
    sur_name: str
    contact_number: str
    is_active: bool
    is_owner: bool = False


class DriverTeamRead(TeamMemberRead):
    vehicle_type: str
    vehicle_number: Optional[str] = None
    is_available: bool
