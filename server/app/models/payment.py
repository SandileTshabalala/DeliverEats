import uuid
from sqlalchemy import Column, String, Numeric, ForeignKey, DateTime, JSON, Enum as SQLAEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.base import Base
from enum import Enum as PyEnum
from app.utils.PaymentStatus import PaymentStatus
class Payment(Base):
    __tablename__ = "payments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String, ForeignKey("orders.id")) 
    provider_id = Column(String, ForeignKey("payment_providers.id"), nullable=True)   
    status = Column(SQLAEnum(PaymentStatus), default=PaymentStatus.PENDING)
    amount = Column(Numeric(10, 2), nullable=False)
    reference = Column(String, nullable=True)
    checkout_url = Column(String, nullable=True)
    provider_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    # Relationships
    order = relationship("Order", back_populates="payments")
    provider = relationship("PaymentProvider", back_populates="payments")
