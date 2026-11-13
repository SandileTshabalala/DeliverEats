import uuid
from sqlalchemy import Column, String, Numeric, Enum as SQLAEnum, Boolean, ForeignKey, DateTime, Integer, Float, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.base import Base
from enum import Enum as PyEnum
from app.utils.OrderStatus import OrderStatus
  
class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    driver_id = Column(String, ForeignKey("drivers.id"), nullable=True, index=True)
    restaurant_id = Column(String, ForeignKey("restaurants.id"), index=True)
    total_amount = Column(Numeric(10, 2), nullable=False)
    status = Column(SQLAEnum(OrderStatus, name="order_status_enum"), default=OrderStatus.PENDING)

    delivery_lat = Column(Float, nullable=True)
    delivery_lng = Column(Float, nullable=True)
    delivery_address = Column(String, nullable=True)
    
    delivery_fee = Column(Numeric(10,2))
    surge_applied = Column(Boolean, default=False)
    driver_wait_started_at = Column(DateTime)
    
    locked = Column(Boolean, default=False)
    locked_at = Column(DateTime)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    #relationships
    customer = relationship("User", back_populates="orders")
    driver = relationship("Driver", back_populates="orders")
    restaurant = relationship("Restaurant", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")
    payments = relationship("Payment", back_populates="order")
    
    @property
    def total(self):
        return self.total_amount

    @property
    def restaurant_name(self):
        return self.restaurant.name if self.restaurant else "N/A"

    # --- payment state, derived from the latest payment row (no extra column) ---
    @property
    def latest_payment(self):
        if not self.payments:
            return None
        return max(self.payments, key=lambda p: p.created_at or datetime.min)

    @property
    def payment_method(self):
        payment = self.latest_payment
        if payment and payment.provider:
            return payment.provider.provider_name
        return None

    @property
    def payment_status(self):
        """unpaid | pay_on_delivery | pending | completed | failed"""
        from app.utils.PaymentStatus import is_offline_provider
        payment = self.latest_payment
        if not payment:
            return "unpaid"
        status = payment.status.value if hasattr(payment.status, "value") else str(payment.status)
        if is_offline_provider(self.payment_method) and status != "completed":
            return "pay_on_delivery"
        return status

    @property
    def is_payment_cleared(self):
        """True when the restaurant may start working on the order."""
        return self.payment_status in ("pay_on_delivery", "completed")

    __table_args__ = (
        Index('idx_order_driver_status', 'driver_id', 'status'),
        Index('idx_order_restaurant_created', 'restaurant_id', 'created_at'),
        Index('idx_order_customer_created', 'customer_id', 'created_at'),
    )
