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

    # Copy of the main category name (app.services.categories keeps it in sync)
    category = Column(String, nullable=True)
    # The owner's own open / closed switch (separate from is_active, which is the platform's)
    accepting_orders = Column(Boolean, nullable=False, default=True, server_default="true")
    # Daily opening hours as "HH:MM" local time. Both empty = open whenever the switch is on.
    opens_at = Column(String(5), nullable=True)
    closes_at = Column(String(5), nullable=True)
    # When the restaurant is VAT registered: its order invoices become tax invoices
    vat_number = Column(String(20), nullable=True)

    @property
    def is_open(self):
        from app.services.restaurant_info import is_open_now
        return is_open_now(self)

    #relationships
    admin_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    admin = relationship("User", back_populates="restaurants")
    menus = relationship("Menu", back_populates="restaurant")
    orders = relationship("Order", back_populates="restaurant")
 