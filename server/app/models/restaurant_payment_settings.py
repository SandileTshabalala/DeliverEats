from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String

from app.db.base import Base
from app.models.subscription import utcnow


class RestaurantPaymentSettings(Base):
    """
    How ONE restaurant gets paid. The money always goes straight to the
    restaurant: cash, its own card machine (speedpoint), or its own account with
    an online gateway (PayFast, Ozow, Peach Payments). The platform never
    touches order money. Secrets are encrypted at rest (app.core.crypto) and
    never returned by the API.
    """
    __tablename__ = "restaurant_payment_settings"

    restaurant_id = Column(String, ForeignKey("restaurants.id", ondelete="CASCADE"), primary_key=True)

    accepts_cash = Column(Boolean, nullable=False, default=True)
    # The driver takes the shop's own card machine (FNB, Capitec, Yoco ...) to the door.
    # Off until the owner switches it on: countertop machines cannot travel.
    accepts_card_machine = Column(Boolean, nullable=False, default=False)

    payfast_enabled = Column(Boolean, nullable=False, default=False)
    payfast_merchant_id = Column(String, nullable=True)
    payfast_merchant_key_enc = Column(String, nullable=True)
    payfast_passphrase_enc = Column(String, nullable=True)
    payfast_sandbox = Column(Boolean, nullable=False, default=False)

    # Ozow instant EFT (One API client credentials)
    ozow_enabled = Column(Boolean, nullable=False, default=False, server_default="false")
    ozow_site_code = Column(String, nullable=True)
    ozow_client_id = Column(String, nullable=True)
    ozow_client_secret_enc = Column(String, nullable=True)
    ozow_sandbox = Column(Boolean, nullable=False, default=False, server_default="false")

    # Peach Payments hosted checkout
    peach_enabled = Column(Boolean, nullable=False, default=False, server_default="false")
    peach_entity_id = Column(String, nullable=True)
    peach_secret_token_enc = Column(String, nullable=True)
    peach_sandbox = Column(Boolean, nullable=False, default=False, server_default="false")

    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
