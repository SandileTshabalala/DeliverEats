import uuid
from sqlalchemy.orm import relationship
from sqlalchemy import Column, String, Boolean, JSON
from app.db.base import Base
 
class PaymentProvider(Base):
    __tablename__ = "payment_providers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_name = Column(String, unique=True)
    display_name = Column(String, nullable=False)  # "PayFast", "Stripe"
    public_key = Column(String, nullable=True)     # SAFE to expose
    secret_key = Column(String, nullable=True)     # NEVER expose
    enabled = Column(Boolean, default=True)
    config = Column(JSON, nullable=True)  # webhook_url, merchant_id, etc Encrypted API keys
    is_active = Column(Boolean, default=True)

        # Relationships
        # ✅ one-to-many
    payments = relationship("Payment", back_populates="provider")
    
