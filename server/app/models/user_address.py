import uuid
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base

class UserAddress(Base):
    __tablename__ = "user_addresses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # __table_args__ = (
    #     Index(
    #         'idx_user_addresses_address_trgm',
    #         'address',
    #         postgresql_using='gin',
    #         postgresql_ops={'address': 'gin_trgm_ops'}
    #     ),
    # )

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    formatted_address = Column(String, nullable=False)
    suburb = Column(String, nullable=True)
    city = Column(String, nullable=True)

    instructions = Column(String, nullable=True)
    is_default = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="addresses")
