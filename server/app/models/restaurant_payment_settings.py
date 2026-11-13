from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String

from app.db.base import Base
from app.models.subscription import utcnow


class RestaurantPaymentSettings(Base):
    """
    How ONE restaurant gets paid. The money always goes straight to the
    restaurant: cash, its own card machine (speedpoint), or its own PayFast
    account. The platform never touches order money.
    """
    __tablename__ = "restaurant_payment_settings"

    restaurant_id = Column(String, ForeignKey("restaurants.id", ondelete="CASCADE"), primary_key=True)

    accepts_cash = Column(Boolean, nullable=False, default=True)
    # Driver brings the shop's own card machine (FNB, Capitec, Yoco ...) to the door
    accepts_card_machine = Column(Boolean, nullable=False, default=True)

    payfast_enabled = Column(Boolean, nullable=False, default=False)
    payfast_merchant_id = Column(String, nullable=True)
    # Encrypted at rest (see app.core.crypto). Never returned by the API.
    payfast_merchant_key_enc = Column(String, nullable=True)
    payfast_passphrase_enc = Column(String, nullable=True)
    payfast_sandbox = Column(Boolean, nullable=False, default=False)

    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
