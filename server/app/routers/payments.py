from typing import List, Optional

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.dependencies import get_db, require_role
from app.core.roles import Role
from app.schemas.payment import PaymentCreate, PaymentResponse
from app.schemas.payment_provider import PublicPaymentConfig
from app.services import payfast, peach
from app.services import restaurant_payment_service as pay_settings
from app.services.payment_service import (
    confirm_stripe_payment,
    create_payment,
    check_order_payment,
    handle_ozow_notify,
    handle_payfast_itn,
    handle_peach_notify,
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


# ---------------- Ozow ----------------
@router.post("/ozow/notify", include_in_schema=False)
async def ozow_notify(request: Request, db: Session = Depends(get_db)):
    """
    Ozow notification. Only used to find the payment; the outcome is always
    confirmed by asking Ozow directly. Always 200 so Ozow stops retrying.
    """
    body = await request.body()
    await run_in_threadpool(handle_ozow_notify, db, body, request.headers.get("content-type", ""))
    return Response(status_code=200)


# ---------------- Peach Payments ----------------
@router.post("/peach/notify", include_in_schema=False)
async def peach_notify(request: Request, db: Session = Depends(get_db)):
    """Peach webhook: signature, amount and our transaction id are checked before anything is marked paid."""
    body = await request.body()
    url = settings.PUBLIC_API_URL.rstrip("/") + settings.API_V1_STR + "/payments/peach/notify"
    headers = {key.lower(): value for key, value in request.headers.items()}
    await run_in_threadpool(handle_peach_notify, db, payfast.parse_itn_body(body), body, headers, url)
    return Response(status_code=200)


@router.api_route("/peach/return", methods=["GET", "POST"], include_in_schema=False)
async def peach_return(request: Request, order: str = ""):
    """
    Peach sends the customer's browser here (as a POST) after checkout. A static
    web page cannot receive a POST, so bounce the browser to the orders page.
    Whether the order is paid is decided by the webhook, not by this.
    """
    code = ""
    if request.method == "POST":
        data = dict(payfast.parse_itn_body(await request.body()))
        code = peach.field(data, "result.code") or ""
    result = peach.outcome(code)
    state = "cancelled" if result == "failed" else "returned"
    safe_order = "".join(ch for ch in order if ch.isalnum() or ch == "-")[:64]
    target = f"{settings.FRONTEND_URL.rstrip('/')}/customer/payment?status={state}&order={safe_order}"
    return RedirectResponse(target, status_code=303)


# ---------------- customer is back from a payment page ----------------
@router.post("/order/{order_id}/check")
def check_payment(order_id: str, db: Session = Depends(get_db), user=Depends(require_role(Role.CUSTOMER))):
    """Ask the gateway now (where it supports that) instead of waiting for its notification."""
    return check_order_payment(db, order_id, user)
