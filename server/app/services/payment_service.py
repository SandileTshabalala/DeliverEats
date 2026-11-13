from typing import List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.locger import logger
from app.models.order import Order
from app.models.payment import Payment
from app.models.payment_provider import PaymentProvider
from app.services import payfast
from app.services import restaurant_payment_service as pay_settings
from app.services.notification_service import send_notification
from app.services.order_service import broadcast_order, get_order, notify_restaurant_of_new_order, short_id
from app.utils.OrderStatus import OrderStatus
from app.utils.PaymentStatus import PaymentStatus, is_offline_provider

PAYFAST_PROVIDER_NAME = "payfast"


def get_provider(db: Session, provider_name: str):
    """
    Catalogue row for a payment method (cash_delivery, card_delivery, payfast).
    Whether a restaurant actually offers it is decided by that restaurant's own
    settings, not by this table.
    """
    return (
        db.query(PaymentProvider)
        .filter(
            PaymentProvider.provider_name == provider_name,
            PaymentProvider.is_active == True,
        )
        .first()
    )


def ensure_default_payment_providers(db: Session) -> None:
    """Idempotent: make sure the catalogue of payment methods exists."""
    for name, display_name in pay_settings.DISPLAY_NAMES.items():
        row = db.query(PaymentProvider).filter(PaymentProvider.provider_name == name).first()
        if not row:
            db.add(PaymentProvider(provider_name=name, display_name=display_name, enabled=True, is_active=True, config={}))
    db.commit()


# --------------------------------------------------------------------------
# Creating a payment
# --------------------------------------------------------------------------
def create_payment(db: Session, order_id: str, provider_name: str, user) -> Payment:
    """
    Start paying for one of the user's own orders.

    The amount always comes from the order, never from the client.
    """
    order = get_order(db, order_id)
    if not order or order.customer_id != user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != OrderStatus.PENDING:
        raise HTTPException(status_code=409, detail="This order can no longer be paid for")
    if order.payment_status == "completed":
        raise HTTPException(status_code=409, detail="This order is already paid")

    # Each restaurant decides how it gets paid
    if provider_name not in pay_settings.enabled_methods(db, order.restaurant_id):
        raise HTTPException(status_code=400, detail="This restaurant does not accept that payment method")
    provider = get_provider(db, provider_name)
    if not provider:
        raise HTTPException(status_code=400, detail="That payment method is not available")

    # A new attempt replaces any earlier unfinished attempt
    for old in order.payments:
        if old.status == PaymentStatus.PENDING:
            old.status = PaymentStatus.FAILED

    name = provider.provider_name.lower()
    payment = Payment(
        order_id=order.id,
        provider_id=provider.id,
        amount=order.total_amount,
        status=PaymentStatus.PENDING,
        reference=f"{name}_{order.id}",
    )
    db.add(payment)
    db.flush()

    checkout_fields = None
    try:
        if is_offline_provider(name):
            pass  # settled in person when the order is delivered
        elif PAYFAST_PROVIDER_NAME in name:
            checkout_fields = _init_payfast(db, payment, order, provider, user)
        elif "stripe" in name:
            _init_stripe(payment, provider)
        else:
            raise HTTPException(status_code=400, detail="That payment method is not supported yet")
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.error(f"Could not start {name} payment for order {order.id}: {exc}")
        raise HTTPException(status_code=502, detail="Could not start the payment. Please try another method.")

    db.commit()
    db.refresh(payment)

    if is_offline_provider(name):
        # Nothing to wait for: the restaurant can see and accept the order now
        db.expire(order)
        order = get_order(db, order.id)
        broadcast_order(order, "new_order")
        notify_restaurant_of_new_order(order)

    # Extra, non-persisted fields for the API response
    payment.provider_name = provider.provider_name
    payment.checkout_fields = checkout_fields
    return payment


def _init_payfast(db: Session, payment: Payment, order: Order, provider: PaymentProvider, user) -> dict:
    # The RESTAURANT's own PayFast account: the money goes straight to the shop
    creds = pay_settings.payfast_credentials(db, order.restaurant_id)
    if not creds:
        raise HTTPException(status_code=503, detail="Online payment is not set up for this restaurant. Please choose another payment method.")

    frontend = settings.FRONTEND_URL.rstrip("/")
    api = settings.PUBLIC_API_URL.rstrip("/")
    restaurant_name = order.restaurant.name if order.restaurant else "Order"

    process_url, fields = payfast.build_checkout(
        creds,
        payment_id=payment.id,
        amount=payment.amount,
        item_name=f"{restaurant_name} order #{order.id[:8]}",
        item_description=", ".join(f"{i.quantity} x {i.name}" for i in order.items),
        return_url=f"{frontend}/customer/orders?payment=success&order={order.id}",
        cancel_url=f"{frontend}/customer/orders?payment=cancelled&order={order.id}",
        notify_url=f"{api}{settings.API_V1_STR}/payments/payfast/notify",
        name_first=user.name,
        name_last=user.sur_name,
        email_address=user.email,
        order_id=order.id,
    )
    payment.checkout_url = process_url
    payment.provider_metadata = {"provider": "payfast", "sandbox": creds.sandbox}
    return fields


def _init_stripe(payment: Payment, provider: PaymentProvider) -> None:
    import stripe

    if not provider.secret_key:
        raise HTTPException(status_code=503, detail="Stripe has not been set up yet")
    stripe.api_key = provider.secret_key
    intent = stripe.PaymentIntent.create(
        amount=int(round(payment.amount * 100)),  # cents
        currency="zar",
        metadata={"payment_id": payment.id, "order_id": payment.order_id},
    )
    # The frontend treats checkout_url as the PaymentIntent client secret
    payment.checkout_url = intent.client_secret
    payment.reference = intent.id
    payment.provider_metadata = {"provider": "stripe_intent", "intent_id": intent.id}


# --------------------------------------------------------------------------
# Completing a payment
# --------------------------------------------------------------------------
def mark_payment_completed(db: Session, payment: Payment, reference: Optional[str] = None) -> Payment:
    if payment.status == PaymentStatus.COMPLETED:
        return payment  # notifications can arrive more than once
    payment.status = PaymentStatus.COMPLETED
    if reference:
        payment.reference = reference
    db.commit()

    order = get_order(db, payment.order_id)
    if order:
        send_notification(
            order.customer_id, "Payment received",
            f"We received R {payment.amount:.2f} for order #{short_id(order)}. The restaurant has your order now.",
            sms=False, email=True,
        )
        # Only now does the restaurant get the order to accept
        broadcast_order(order, "new_order")
        notify_restaurant_of_new_order(order)
    return payment


def mark_payment_failed(db: Session, payment: Payment) -> Payment:
    if payment.status == PaymentStatus.PENDING:
        payment.status = PaymentStatus.FAILED
        db.commit()
        order = get_order(db, payment.order_id)
        if order:
            broadcast_order(order)
    return payment


def handle_payfast_itn(db: Session, pairs: List[Tuple[str, str]], remote_ip: Optional[str]) -> None:
    """
    Process a PayFast notification. Never raises for bad notifications: they are
    logged and ignored, and the endpoint still answers 200 as PayFast expects.
    """
    data = dict(pairs)
    payment_id = data.get("m_payment_id")
    payment = db.query(Payment).filter(Payment.id == payment_id).first() if payment_id else None
    if not payment:
        logger.warning(f"PayFast ITN for unknown payment {payment_id!r}")
        return

    # Validate against the account of the restaurant the order belongs to
    order = db.query(Order).filter(Order.id == payment.order_id).first()
    creds = pay_settings.payfast_credentials(db, order.restaurant_id) if order else None
    if not creds:
        logger.error(f"PayFast ITN for payment {payment.id} but the restaurant has no PayFast account configured")
        return

    ok, reason = payfast.validate_itn(
        creds,
        pairs,
        expected_amount=payment.amount,
        remote_ip=remote_ip,
        # The sandbox is often used through a tunnel that hides the caller's address;
        # the confirmation call back to PayFast still runs in every mode.
        check_source_ip=not creds.sandbox,
    )
    if not ok:
        logger.warning(f"PayFast ITN rejected for payment {payment.id}: {reason}")
        return

    status = (data.get("payment_status") or "").upper()
    if status == "COMPLETE":
        mark_payment_completed(db, payment, reference=data.get("pf_payment_id"))
    elif status in ("FAILED", "CANCELLED"):
        mark_payment_failed(db, payment)
    # "PENDING" needs no action: PayFast sends another notification later


def confirm_stripe_payment(db: Session, payment_id: str, user) -> Payment:
    """Ask Stripe (server to server) whether the PaymentIntent really succeeded."""
    import stripe

    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment or not payment.order or payment.order.customer_id != user.id:
        raise HTTPException(status_code=404, detail="Payment not found")
    provider = payment.provider
    if not provider or "stripe" not in provider.provider_name.lower() or not provider.secret_key:
        raise HTTPException(status_code=400, detail="Not a Stripe payment")

    stripe.api_key = provider.secret_key
    intent = stripe.PaymentIntent.retrieve(payment.reference)
    if intent.status == "succeeded" and intent.amount == int(round(payment.amount * 100)):
        mark_payment_completed(db, payment)
    elif intent.status in ("canceled", "requires_payment_method"):
        mark_payment_failed(db, payment)

    db.refresh(payment)
    payment.provider_name = provider.provider_name
    payment.checkout_fields = None
    return payment
