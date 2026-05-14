import uuid
from sqlalchemy import Column, String, Boolean, Numeric, ForeignKey, Index
from app.db.base import Base
from sqlalchemy.orm import relationship

class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    menu_id = Column(String, ForeignKey("menus.id", ondelete="CASCADE"), index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    price = Column(Numeric(10, 2), nullable=False)
    is_available = Column(Boolean, default=True, index=True)
    image_url = Column(String, nullable=True)
    # Relationships
    menu = relationship("Menu", back_populates="items")
    order_items = relationship("OrderItem", back_populates="menu_item")

    __table_args__ = (
        Index('idx_menu_item_menu_available', 'menu_id', 'is_available'),
    )
