import uuid
from sqlalchemy import Column, String, Boolean, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import ForeignKey
from app.db.base import Base
 
class Restaurant(Base):
    __tablename__ = "restaurants"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(String)
    logo_img_url = Column(String, nullable=True)
    address = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

    #relationships
    admin_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    admin = relationship("User", back_populates="restaurants")
    menus = relationship("Menu", back_populates="restaurant")
    orders = relationship("Order", back_populates="restaurant")
 