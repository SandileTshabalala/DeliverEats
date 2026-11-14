import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from app.db.base import Base
from app.models.subscription import utcnow


class OrderReview(Base):
    """A customer's rating of one delivered order. One review per order."""
    __tablename__ = "order_reviews"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    restaurant_id = Column(String, ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1 to 5
    comment = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow)
