from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.locger import logger
from app.models.order import Order
from app.models.payment import Payment
from app.models.payment_provider import PaymentProvider
from app.services import ozow, payfast, peach
from app.services import restaurant_payment_service as pay_settings
from app.services.notification_service import send_notification
from app.services.order_service import broadcast_order, get_order, notify_restaurant_of_new_order, request_refund, short_id


def _status_value(status) -> str:
    return status.value if hasattr(status, "value") else str(status)
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
        elif name == pay_settings.OZOW:
            _init_ozow(db, payment, order)
        elif name == pay_settings.PEACH:
            checkout_fields = _init_peach(db, payment, order)
        elif "stripe" in name:
            _init_stripe(payment, provider)
        else:
            raise HTTPException(status_code=400, detail="That payment method is not supported yet")
    except HTTPException:
        db.rollback()
        raise
    except ozow.OzowError as exc:
        db.rollback()
        logger.error(f"Could not start Ozow payment for order {order.id}: {exc}")
        raise HTTPException(status_code=502, detail="Ozow is not answering right now. Please try another payment method.")
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
        return_url=f"{frontend}/customer/payment?status=success&order={order.id}",
        cancel_url=f"{frontend}/customer/payment?status=cancelled&order={order.id}",
        notify_url=f"{api}{settings.API_V1_STR}/payments/payfast/notify",
        name_first=user.name,
        name_last=user.sur_name,
        email_address=user.email,
        order_id=order.id,
    )
    payment.checkout_url = process_url
    payment.provider_metadata = {"provider": "payfast", "sandbox": creds.sandbox}
    return fields


def _urls():
    return settings.FRONTEND_URL.rstrip("/"), settings.PUBLIC_API_URL.rstrip("/") + settings.API_V1_STR


def _init_ozow(db: Session, payment: Payment, order: Order) -> None:
    """Ozow One API: create the payment and send the customer to Ozow's page."""
    creds = pay_settings.ozow_credentials(db, order.restaurant_id)
    if not creds:
        raise HTTPException(status_code=503, detail="Ozow is not set up for this restaurant. Please choose another payment method.")
    frontend, api = _urls()
    created = ozow.create_payment(
        creds,
        amount=payment.amount,
        merchant_reference=payment.id,
        bank_reference=f"{(order.restaurant.name if order.restaurant else 'ORDER')[:11]}{order.id[:8]}",
        return_url=f"{frontend}/customer/payment?status=returned&order={order.id}",
        notify_url=f"{api}/payments/ozow/notify",
    )
    payment.reference = created["id"]  # Ozow's payment id, used for the status check
    payment.checkout_url = created["redirectUrl"]
    payment.provider_metadata = {"provider": "ozow", "ozow_payment_id": created["id"], "sandbox": creds.sandbox}


def _init_peach(db: Session, payment: Payment, order: Order) -> dict:
    """Peach hosted checkout: signed fields the browser posts to Peach."""
    creds = pay_settings.peach_credentials(db, order.restaurant_id)
    if not creds:
        raise HTTPException(status_code=503, detail="Peach Payments is not set up for this restaurant. Please choose another payment method.")
    _, api = _urls()
    transaction_id = peach.new_transaction_id()
    url, fields = peach.build_checkout(
        creds,
        amount=payment.amount,
        merchant_transaction_id=transaction_id,
        shopper_result_url=f"{api}/payments/peach/return?order={order.id}",
        notification_url=f"{api}/payments/peach/notify",
    )
    payment.reference = transaction_id  # how the webhook finds this payment
    payment.checkout_url = url
    payment.provider_metadata = {"provider": "peach", "sandbox": creds.sandbox}
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
def _lock(db: Session, payment: Payment) -> Payment:
    """
    Re-read the payment with a row lock (Postgres) so two notifications arriving
    at the same moment are handled one after the other, never both at once.
    """
    db.expire(payment)
    return db.query(Payment).filter(Payment.id == payment.id).with_for_update().one()


def mark_payment_completed(db: Session, payment: Payment, reference: Optional[str] = None) -> Payment:
    payment = _lock(db, payment)
    if payment.status == PaymentStatus.COMPLETED:
        db.commit()  # release the lock
        return payment  # notifications can arrive more than once

    # Was this order already paid by another checkout? (two payment pages completed)
    earlier = db.query(Payment).filter(
        Payment.order_id == payment.order_id, Payment.id != payment.id, Payment.status == PaymentStatus.COMPLETED
    ).first()

    payment.status = PaymentStatus.COMPLETED
    if reference:
        payment.reference = reference
    if earlier:
        meta = dict(payment.provider_metadata or {})
        meta.update(needs_refund=True, duplicate_of=earlier.id)
        payment.provider_metadata = meta
    db.commit()

    order = get_order(db, payment.order_id)
    if order and earlier:
        _report_double_payment(order, payment)
        return payment
    if order and _status_value(order.status) == OrderStatus.CANCELLED.value:
        # The payment came through after the order was cancelled (for example the
        # unpaid-order clean-up ran first): never send it to the kitchen, refund it.
        request_refund(db, order, payment, "paid_after_cancel")
        broadcast_order(order)
        return payment
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


def _report_double_payment(order: Order, payment: Payment) -> None:
    """The customer paid twice for one order: tell the restaurant (it received the money) and the customer."""
    ref = short_id(order)
    logger.warning(f"Order {order.id} paid twice: payment {payment.id} (R {payment.amount:.2f}) needs a refund")
    owner_id = order.restaurant.admin_id if order.restaurant else None
    send_notification(
        owner_id, "Refund needed: order paid twice",
        f"Order #{ref} was paid twice online. Please refund R {payment.amount:.2f} to the customer "
        f"from your {(_provider_name(payment) or 'payment').title()} account. Payment reference: {payment.reference or payment.id}.",
        sms=True, email=True,
    )
    send_notification(
        order.customer_id, "You were charged twice",
        f"Order #{ref} went through twice. The restaurant has been asked to refund R {payment.amount:.2f}. "
        f"You do not need to do anything, but contact the restaurant if you do not see the refund within 7 days.",
        sms=True, email=True,
    )


def mark_payment_failed(db: Session, payment: Payment) -> Payment:
    payment = _lock(db, payment)
    if payment.status != PaymentStatus.PENDING:
        db.commit()  # release the lock
        return payment
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


# --------------------------------------------------------------------------
# Ozow: every confirmation is checked with Ozow itself
# --------------------------------------------------------------------------
def _provider_name(payment: Payment) -> str:
    return (payment.provider.provider_name if payment.provider else "").lower()


def verify_ozow_payment(db: Session, payment: Payment) -> Optional[bool]:
    """Ask Ozow how this payment went and record the answer. Returns ozow.is_paid's result."""
    if payment.status != PaymentStatus.PENDING or _provider_name(payment) != pay_settings.OZOW:
        return None
    order = db.query(Order).filter(Order.id == payment.order_id).first()
    creds = pay_settings.ozow_credentials(db, order.restaurant_id) if order else None
    ozow_payment_id = (payment.provider_metadata or {}).get("ozow_payment_id") or payment.reference
    if not creds or not ozow_payment_id:
        return None
    created = (payment.created_at or datetime.now(timezone.utc)).date()
    result = ozow.is_paid(creds, ozow_payment_id, payment.id, payment.amount, created)
    if result is True:
        mark_payment_completed(db, payment)
    elif result is False:
        mark_payment_failed(db, payment)
    return result


def _ozow_identifiers(raw_body: bytes, content_type: str) -> List[str]:
    """Anything in an Ozow notification that could identify the payment."""
    import json
    from urllib.parse import parse_qsl

    found: List[str] = []
    try:
        if "json" in (content_type or ""):
            body = json.loads(raw_body or b"{}")
            items = [body, body.get("data") or {}] if isinstance(body, dict) else []
        else:
            items = [dict(parse_qsl(raw_body.decode("utf-8", errors="replace"), keep_blank_values=True))]
    except (ValueError, AttributeError):
        return found
    for item in items:
        for key in ("TransactionReference", "transactionReference", "merchantReference", "paymentId", "paymentRequestId", "id"):
            value = item.get(key) if isinstance(item, dict) else None
            if isinstance(value, str) and value and value not in found:
                found.append(value)
    return found[:5]


def handle_ozow_notify(db: Session, raw_body: bytes, content_type: str) -> None:
    """
    Ozow says something happened. We do not trust the message: we only use it
    to find the payment, then ask Ozow directly. Never raises.
    """
    for identifier in _ozow_identifiers(raw_body, content_type):
        payment = db.query(Payment).filter(or_(Payment.id == identifier, Payment.reference == identifier)).first()
        if payment and _provider_name(payment) == pay_settings.OZOW:
            try:
                verify_ozow_payment(db, payment)
            except ozow.OzowError as exc:
                logger.warning(f"Ozow status check for payment {payment.id} failed: {exc}")
            return
    logger.warning("Ozow notification did not match any payment")


def check_pending_ozow_payments(db: Session, max_age_hours: int = 3) -> int:
    """Background safety net: confirm recent unfinished Ozow payments even if no notification matched."""
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=max_age_hours)
    pending = (
        db.query(Payment)
        .join(PaymentProvider, Payment.provider_id == PaymentProvider.id)
        .filter(Payment.status == PaymentStatus.PENDING, PaymentProvider.provider_name == pay_settings.OZOW,
                Payment.created_at >= since)
        .all()
    )
    settled = 0
    for payment in pending:
        try:
            if verify_ozow_payment(db, payment) is not None:
                settled += 1
        except ozow.OzowError as exc:
            logger.warning(f"Ozow status check for payment {payment.id} failed: {exc}")
    return settled


# --------------------------------------------------------------------------
# Peach Payments: signed webhook
# --------------------------------------------------------------------------
def handle_peach_notify(db: Session, pairs: List[Tuple[str, str]], raw_body: bytes, headers: dict, url: str) -> None:
    """Process a Peach webhook. Never raises: bad ones are logged and ignored."""
    data = dict(pairs)
    transaction_id = peach.field(data, "merchantTransactionId")
    payment = db.query(Payment).filter(Payment.reference == transaction_id).first() if transaction_id else None
    if not payment or _provider_name(payment) != pay_settings.PEACH:
        logger.warning(f"Peach webhook for unknown transaction {transaction_id!r}")
        return

    order = db.query(Order).filter(Order.id == payment.order_id).first()
    creds = pay_settings.peach_credentials(db, order.restaurant_id) if order else None
    if not creds:
        logger.error(f"Peach webhook for payment {payment.id} but the restaurant has no Peach account configured")
        return
    if not peach.webhook_signature_valid(pairs, raw_body, headers, url, creds.secret_token):
        logger.warning(f"Peach webhook rejected for payment {payment.id}: invalid signature")
        return
    if not payfast.amounts_match(payment.amount, data.get("amount")) or (data.get("currency") or "ZAR") != "ZAR":
        logger.warning(f"Peach webhook rejected for payment {payment.id}: amount or currency mismatch")
        return

    result = peach.outcome(peach.field(data, "result.code"))
    if result == "completed":
        meta = dict(payment.provider_metadata or {})
        meta["peach_id"] = data.get("id")
        payment.provider_metadata = meta
        mark_payment_completed(db, payment)
    elif result == "failed":
        mark_payment_failed(db, payment)


# --------------------------------------------------------------------------
# Customer came back from a payment page
# --------------------------------------------------------------------------
def check_order_payment(db: Session, order_id: str, user) -> dict:
    """Re-check the latest payment of the customer's own order where the gateway allows it."""
    order = get_order(db, order_id)
    if not order or order.customer_id != user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    payment = order.latest_payment
    if payment and payment.status == PaymentStatus.PENDING and _provider_name(payment) == pay_settings.OZOW:
        try:
            verify_ozow_payment(db, payment)
        except ozow.OzowError as exc:
            logger.warning(f"Ozow status check for payment {payment.id} failed: {exc}")
        db.expire_all()
        order = get_order(db, order_id)
    return {"order_id": order.id, "payment_status": order.payment_status}


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
