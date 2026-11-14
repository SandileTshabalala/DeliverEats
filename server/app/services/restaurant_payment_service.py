"""Per-restaurant payment methods. Order money always goes to the restaurant itself."""
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.crypto import decrypt, encrypt
from app.models.restaurant_payment_settings import RestaurantPaymentSettings
from app.services import ozow, payfast, peach

SECRET_MASK = "********"

CASH = "cash_delivery"
CARD_MACHINE = "card_delivery"
PAYFAST = "payfast"
OZOW = "ozow"
PEACH = "peach"

# What the customer sees at checkout, in this order
DISPLAY_NAMES = {
    CASH: "Cash on Delivery",
    CARD_MACHINE: "Card Machine on Delivery",
    PAYFAST: "Pay Online with PayFast (Card, Instant EFT)",
    OZOW: "Instant EFT from your bank (Ozow)",
    PEACH: "Pay Online by Card (Peach Payments)",
}

ONLINE_METHODS = (PAYFAST, OZOW, PEACH)

# Plain text fields per gateway, and secret fields -> encrypted column
PLAIN_FIELDS = (
    "payfast_merchant_id", "ozow_site_code", "ozow_client_id", "peach_entity_id",
)
SECRET_FIELDS = {
    "payfast_merchant_key": "payfast_merchant_key_enc",
    "payfast_passphrase": "payfast_passphrase_enc",
    "ozow_client_secret": "ozow_client_secret_enc",
    "peach_secret_token": "peach_secret_token_enc",
}
SWITCHES = (
    "accepts_cash", "accepts_card_machine",
    "payfast_enabled", "payfast_sandbox",
    "ozow_enabled", "ozow_sandbox",
    "peach_enabled", "peach_sandbox",
)


def get_settings(db: Session, restaurant_id: str) -> RestaurantPaymentSettings:
    """
    Settings row, or unsaved defaults if the shop never changed them: cash only.
    The card machine starts OFF because a countertop speedpoint cannot go with
    the driver; the owner switches it on once they know theirs is portable.
    """
    row = db.query(RestaurantPaymentSettings).filter(
        RestaurantPaymentSettings.restaurant_id == restaurant_id
    ).first()
    if row:
        return row
    return RestaurantPaymentSettings(
        restaurant_id=restaurant_id,
        accepts_cash=True,
        accepts_card_machine=False,
        payfast_enabled=False, payfast_sandbox=False,
        ozow_enabled=False, ozow_sandbox=False,
        peach_enabled=False, peach_sandbox=False,
    )


# ---------------------------------------------------------------- credentials
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


def _ozow_from_row(row: RestaurantPaymentSettings) -> Optional[ozow.OzowCredentials]:
    secret = decrypt(row.ozow_client_secret_enc)
    if not (row.ozow_site_code and row.ozow_client_id and secret):
        return None
    return ozow.OzowCredentials(
        site_code=row.ozow_site_code.strip(),
        client_id=row.ozow_client_id.strip(),
        client_secret=secret.strip(),
        sandbox=bool(row.ozow_sandbox),
    )


def ozow_credentials(db: Session, restaurant_id: str) -> Optional[ozow.OzowCredentials]:
    row = get_settings(db, restaurant_id)
    return _ozow_from_row(row) if row.ozow_enabled else None


def peach_credentials(db: Session, restaurant_id: str) -> Optional[peach.PeachCredentials]:
    row = get_settings(db, restaurant_id)
    secret = decrypt(row.peach_secret_token_enc)
    if not (row.peach_enabled and row.peach_entity_id and secret):
        return None
    return peach.PeachCredentials(
        entity_id=row.peach_entity_id.strip(),
        secret_token=secret.strip(),
        sandbox=bool(row.peach_sandbox),
    )


# ---------------------------------------------------------------- what checkout offers
def enabled_methods(db: Session, restaurant_id: str) -> List[str]:
    row = get_settings(db, restaurant_id)
    methods = []
    if row.accepts_cash:
        methods.append(CASH)
    if row.accepts_card_machine:
        methods.append(CARD_MACHINE)
    if payfast_credentials(db, restaurant_id):
        methods.append(PAYFAST)
    if ozow_credentials(db, restaurant_id):
        methods.append(OZOW)
    if peach_credentials(db, restaurant_id):
        methods.append(PEACH)
    return methods


def public_config(db: Session, restaurant_id: str) -> List[dict]:
    """What the checkout shows for this restaurant. Contains no keys of any kind."""
    return [
        {"provider_name": name, "display_name": DISPLAY_NAMES[name], "enabled": True, "public_key": None}
        for name in enabled_methods(db, restaurant_id)
    ]


def serialize(row: RestaurantPaymentSettings) -> dict:
    """Owner's view. Secrets are write-only: only whether they are set is revealed."""
    data = {name: bool(getattr(row, name)) for name in SWITCHES}
    data.update({name: getattr(row, name) for name in PLAIN_FIELDS})
    data.update({name: SECRET_MASK if getattr(row, column) else None for name, column in SECRET_FIELDS.items()})
    return data


# ---------------------------------------------------------------- saving
def update_settings(db: Session, restaurant_id: str, data: dict, check_ozow=None) -> RestaurantPaymentSettings:
    row = get_settings(db, restaurant_id)
    ozow_before = (row.ozow_site_code, row.ozow_client_id, row.ozow_client_secret_enc, row.ozow_sandbox)

    for name in SWITCHES:
        if data.get(name) is not None:
            setattr(row, name, data[name])
    for name in PLAIN_FIELDS:
        if name in data:
            setattr(row, name, (data[name] or "").strip() or None)
    # Sending the mask back (or leaving the field out) keeps the stored secret
    for name, column in SECRET_FIELDS.items():
        if name in data and data[name] != SECRET_MASK:
            setattr(row, column, encrypt((data[name] or "").strip()))

    if row.payfast_enabled and not (row.payfast_merchant_id and row.payfast_merchant_key_enc):
        raise HTTPException(status_code=400, detail="Enter your PayFast merchant ID and merchant key to switch on PayFast")
    if row.ozow_enabled and not (row.ozow_site_code and row.ozow_client_id and row.ozow_client_secret_enc):
        raise HTTPException(status_code=400, detail="Enter your Ozow site code, client ID and client secret to switch on Ozow")
    if row.peach_enabled and not (row.peach_entity_id and row.peach_secret_token_enc):
        raise HTTPException(status_code=400, detail="Enter your Peach Payments entity ID and secret token to switch on Peach Payments")
    if not (row.accepts_cash or row.accepts_card_machine or row.payfast_enabled or row.ozow_enabled or row.peach_enabled):
        raise HTTPException(status_code=400, detail="Keep at least one payment method switched on")

    # Catch a mistyped Ozow secret now, not when a customer is trying to pay
    ozow_after = (row.ozow_site_code, row.ozow_client_id, row.ozow_client_secret_enc, row.ozow_sandbox)
    if row.ozow_enabled and ozow_after != ozow_before:
        creds = _ozow_from_row(row)
        try:
            (check_ozow or (lambda c: ozow.access_token(c, use_cache=False)))(creds)
        except ozow.OzowError as exc:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"Could not connect to Ozow: {exc}. Check the details and the test-mode switch.")

    db.add(row)
    db.commit()
    db.refresh(row)
    return row
