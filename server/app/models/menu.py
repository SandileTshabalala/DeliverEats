import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.db.base import Base

class Menu(Base):
    __tablename__ = "menus"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    restaurant_id = Column(String, ForeignKey("restaurants.id", ondelete="CASCADE"), index=True)
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

    #relationships
    restaurant = relationship("Restaurant", back_populates="menus")
    items = relationship("MenuItem", back_populates="menu")

    __table_args__ = (
        Index('idx_menu_restaurant_active', 'restaurant_id', 'is_active'),
    )