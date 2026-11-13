from typing import List, Optional

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.dependencies import get_db, require_role
from app.core.roles import Role
from app.schemas.payment import PaymentCreate, PaymentResponse
from app.schemas.payment_provider import PublicPaymentConfig
from app.services import payfast
from app.services import restaurant_payment_service as pay_settings
from app.services.payment_service import (
    confirm_stripe_payment,
    create_payment,
    handle_payfast_itn,
)

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.get("/config", response_model=List[PublicPaymentConfig])
def get_payment_config(restaurant_id: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Payment methods offered by ONE restaurant (each shop chooses its own:
    cash, its card machine, or its own PayFast account). Never includes keys.
    """
    if not restaurant_id:
        return []
    return pay_settings.public_config(db, restaurant_id)


@router.post("/", response_model=PaymentResponse)
def new_payment(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    user=Depends(require_role(Role.CUSTOMER))
):
    """Start a payment for one of the caller's own orders (amount comes from the order)."""
    return create_payment(db, payload.order_id, payload.provider_name, user)


@router.post("/{payment_id}/stripe/confirm", response_model=PaymentResponse)
def stripe_confirm(
    payment_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_role(Role.CUSTOMER))
):
    return confirm_stripe_payment(db, payment_id, user)


def _client_ip(request: Request) -> str:
    """Caller's address. Behind our own nginx the real one is in X-Forwarded-For."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded and settings.is_production:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


@router.post("/payfast/notify", include_in_schema=False)
async def payfast_notify(request: Request, db: Session = Depends(get_db)):
    """
    PayFast ITN webhook (server to server, no login). The notification is fully
    validated before anything is marked as paid. Always answers 200 so PayFast
    stops retrying; rejected notifications are only logged.
    """
    pairs = payfast.parse_itn_body(await request.body())
    await run_in_threadpool(handle_payfast_itn, db, pairs, _client_ip(request))
    return Response(status_code=200)
