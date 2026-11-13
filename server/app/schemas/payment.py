from pydantic import BaseModel
from typing import Optional
from enum import Enum
from app.schemas.payment_provider import PaymentProviderRead
from app.schemas.order import OrderRead
from decimal import Decimal

class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
class PaymentBase(BaseModel):
    amount: float
    status: PaymentStatus = PaymentStatus.PENDING    

class PaymentCreate(BaseModel):
    order_id: str
    provider_name: str
    # Ignored: the amount charged is always the order total stored on the server
    amount: Optional[Decimal] = None

class PaymentResponse(BaseModel):
    id: str
    status: PaymentStatus = PaymentStatus.PENDING
    provider_name: str
    amount: Decimal
    # Where to send the customer. PayFast: POST `checkout_fields` to this URL.
    # Stripe: this is the PaymentIntent client secret.
    checkout_url: Optional[str] = None
    checkout_fields: Optional[dict] = None
    provider_metadata: Optional[dict] = None

    class Config:
        from_attributes = True

class PaymentRead(PaymentBase):
    id: str
    order: OrderRead
    provider_info: PaymentProviderRead

    class Config:
        from_attributes = True