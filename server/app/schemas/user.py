from pydantic import BaseModel, EmailStr
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

# Fields for creating a user
class UserCreate(UserBase): 
    password: str

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
          
