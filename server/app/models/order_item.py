import uuid
from sqlalchemy.orm import relationship
from sqlalchemy import Column, String, Integer, Numeric, ForeignKey, JSON
from app.db.base import Base

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    order_id = Column(String, ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    # menu_item_id = Column(String, ForeignKey("menu_items.id", ondelete="RESTRICT"))
    menu_item_id = Column(String, ForeignKey("menu_items.id"), nullable=False)
    description = Column(String, nullable=True)
    quantity = Column(Integer, nullable=False)
    # Price of ONE, including the extras picked
    price = Column(Numeric(10, 2), nullable=False)
    # What the customer picked, as it was when ordering: [{"group", "name", "price"}]
    options = Column(JSON, nullable=True)

    # Relationships
    order = relationship("Order", back_populates="items")
    menu_item = relationship("MenuItem", back_populates="order_items")
