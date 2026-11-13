from sqlalchemy import Column, DateTime, Float, ForeignKey, Numeric, String

from app.db.base import Base
from app.models.subscription import utcnow


class RestaurantDeliverySettings(Base):
    """What ONE restaurant charges for delivery. See app.services.delivery_fee."""
    __tablename__ = "restaurant_delivery_settings"

    restaurant_id = Column(String, ForeignKey("restaurants.id", ondelete="CASCADE"), primary_key=True)

    base_fee = Column(Numeric(10, 2), nullable=False, default=0)
    per_km_fee = Column(Numeric(10, 2), nullable=False, default=0)
    # Food subtotal from which delivery is free (NULL = never free)
    free_delivery_over = Column(Numeric(10, 2), nullable=True)
    # Furthest the restaurant delivers (NULL = no limit)
    max_distance_km = Column(Float, nullable=True)

    # Where the shop is, for working out the distance to the customer
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
