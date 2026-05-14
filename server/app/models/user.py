import uuid
from sqlalchemy import Column, Integer, String, Boolean, Enum
from app.db.base import Base
from app.core.roles import Role
from sqlalchemy.orm import relationship
class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    sur_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    contact_number = Column(String, nullable=False) 
    role = Column(Enum(Role, name="role_enum"), nullable=False)
    is_active = Column(Boolean, default=True)
    #relationships
    driver = relationship("Driver", back_populates="user", uselist=False)
    restaurants = relationship("Restaurant", back_populates="admin")
    orders = relationship("Order", back_populates="customer")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    addresses = relationship("UserAddress", back_populates="user", cascade="all, delete-orphan")


    
  