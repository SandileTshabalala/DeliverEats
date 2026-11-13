from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, Float, DateTime
from sqlalchemy.orm import relationship
from app.db.base import Base

class Driver(Base):
    __tablename__ = "drivers"

    id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    # name = Column(String, nullable=False)
    # surname = Column(String, nullable=False)
    # contact_number = Column(String, nullable=False)
    # user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    # The restaurant this driver delivers for. NULL = legacy shared driver
    # (created before drivers belonged to restaurants): used only as a fallback.
    restaurant_id = Column(String, ForeignKey("restaurants.id", ondelete="SET NULL"), nullable=True, index=True)
    vehicle_type = Column(String, nullable=False)
    vehicle_number = Column(String, nullable=True)
    is_available = Column(Boolean, default=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # driver_assigned_at = Column(DateTime)
    last_assigned_at = Column(DateTime, nullable=True)
    driver_delay_warning = Column(Boolean, default=False)

    # relationships
    user = relationship("User", back_populates="driver")
    orders = relationship("Order", back_populates="driver")

    # The person behind the driver profile (drivers share their id with their user)
    @property
    def name(self):
        return self.user.name if self.user else None

    @property
    def sur_name(self):
        return self.user.sur_name if self.user else None

    @property
    def contact_number(self):
        return self.user.contact_number if self.user else None