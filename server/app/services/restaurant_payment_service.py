"""Per-restaurant payment methods. Order money always goes to the restaurant itself."""
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.crypto import decrypt, encrypt
from app.models.restaurant_payment_settings import RestaurantPaymentSettings
from app.services import payfast

SECRET_MASK = "********"

CASH = "cash_delivery"
CARD_MACHINE = "card_delivery"
PAYFAST = "payfast"

DISPLAY_NAMES = {
    CASH: "Cash on Delivery",
    CARD_MACHINE: "Card Machine on Delivery",
    PAYFAST: "Pay Online (Card, Instant EFT)",
}


def get_settings(db: Session, restaurant_id: str) -> RestaurantPaymentSettings:
    """Settings row, or unsaved defaults (cash + card machine) if the shop never changed them."""
    row = db.query(RestaurantPaymentSettings).filter(
        RestaurantPaymentSettings.restaurant_id == restaurant_id
    ).first()
    if row:
        return row
    return RestaurantPaymentSettings(
        restaurant_id=restaurant_id,
        accepts_cash=True,
        accepts_card_machine=True,
        payfast_enabled=False,
        payfast_sandbox=False,
    )


def payfast_credentials(db: Session, restaurant_id: str) -> Optional[payfast.PayFastCredentials]:
    """The RESTAURANT's own PayFast account, or None if it is not fully set up."""
    row = get_settings(db, restaurant_id)
    merchant_key = decrypt(row.payfast_merchant_key_enc)
    if not (row.payfast_enabled and row.payfast_merchant_id and merchant_key):
        return None
    return payfast.PayFastCredentials(
        merchant_id=row.payfast_merchant_id.strip(),
        merchant_key=merchant_key.strip(),
        passphrase=(decrypt(row.payfast_passphrase_enc) or "").strip() or None,
        sandbox=bool(row.payfast_sandbox),
    )


def enabled_methods(db: Session, restaurant_id: str) -> List[str]:
    row = get_settings(db, restaurant_id)
    methods = []
    if row.accepts_cash:
        methods.append(CASH)
    if row.accepts_card_machine:
        methods.append(CARD_MACHINE)
    if payfast_credentials(db, restaurant_id):
        methods.append(PAYFAST)
    return methods


def public_config(db: Session, restaurant_id: str) -> List[dict]:
    """What the checkout shows for this restaurant. Contains no keys of any kind."""
    return [
        {"provider_name": name, "display_name": DISPLAY_NAMES[name], "enabled": True, "public_key": None}
        for name in enabled_methods(db, restaurant_id)
    ]


def serialize(row: RestaurantPaymentSettings) -> dict:
    """Owner's view. Secrets are write-only: only whether they are set is revealed."""
    return {
        "accepts_cash": bool(row.accepts_cash),
        "accepts_card_machine": bool(row.accepts_card_machine),
        "payfast_enabled": bool(row.payfast_enabled),
        "payfast_merchant_id": row.payfast_merchant_id,
        "payfast_merchant_key": SECRET_MASK if row.payfast_merchant_key_enc else None,
        "payfast_passphrase": SECRET_MASK if row.payfast_passphrase_enc else None,
        "payfast_sandbox": bool(row.payfast_sandbox),
    }


def update_settings(db: Session, restaurant_id: str, data: dict) -> RestaurantPaymentSettings:
    row = get_settings(db, restaurant_id)

    for field in ("accepts_cash", "accepts_card_machine", "payfast_enabled", "payfast_sandbox"):
        if data.get(field) is not None:
            setattr(row, field, data[field])
    if "payfast_merchant_id" in data:
        row.payfast_merchant_id = (data["payfast_merchant_id"] or "").strip() or None

    # Sending the mask back (or leaving the field out) keeps the stored secret
    for field, column in (("payfast_merchant_key", "payfast_merchant_key_enc"), ("payfast_passphrase", "payfast_passphrase_enc")):
        if field in data and data[field] != SECRET_MASK:
            setattr(row, column, encrypt((data[field] or "").strip()))

    if row.payfast_enabled and not (row.payfast_merchant_id and row.payfast_merchant_key_enc):
        raise HTTPException(status_code=400, detail="Enter your PayFast merchant ID and merchant key to switch on online payments")
    if not (row.accepts_cash or row.accepts_card_machine or row.payfast_enabled):
        raise HTTPException(status_code=400, detail="Keep at least one payment method switched on")

    db.add(row)
    db.commit()
    db.refresh(row)
    return row
