from pydantic import BaseModel, EmailStr, Field
from app.core.roles import Role
from typing import Optional, List
from app.schemas.user_address import UserAddressRead
 
# Base user fields
class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    sur_name: Optional[str] = None
    contact_number: Optional[str] = None
    is_active: bool = True
    role: Role = Role.CUSTOMER

# Fields for public self-registration. Deliberately has NO role / is_active:
# everyone who signs up is a customer. Staff accounts are created by an admin.
class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1)
    sur_name: str = Field(min_length=1)
    contact_number: str = Field(min_length=5)
    password: str = Field(min_length=8)

# Fields for reading a user (no password)
class UserRead(UserBase):
    id: str
    addresses: List[UserAddressRead] = []

    class Config:
        from_attributes = True

# Fields for updating a user
class UserUpdate(BaseModel):
    name: Optional[str] = None
    sur_name: Optional[str] = None
    contact_number: Optional[str] = None
    email: Optional[EmailStr] = None
          
