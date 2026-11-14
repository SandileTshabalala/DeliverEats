import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String

from app.db.base import Base
from app.models.subscription import utcnow


class Category(Base):
    """
    A kind of food customers browse by (Chicken, Kota, Pizza...). The platform
    owner manages the list and its pictures; each restaurant picks the ones it sells.
    """
    __tablename__ = "categories"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(40), nullable=False, unique=True)
    image_url = Column(String, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0, server_default="0")
    # Hidden categories disappear for customers and owners but keep their links
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime, default=utcnow)


class RestaurantCategory(Base):
    """Which categories a restaurant sells. position 0 is its main one (shown on its card)."""
    __tablename__ = "restaurant_categories"

    restaurant_id = Column(String, ForeignKey("restaurants.id", ondelete="CASCADE"), primary_key=True)
    category_id = Column(String, ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True, index=True)
    position = Column(Integer, nullable=False, default=0, server_default="0")
