from pydantic import BaseModel, EmailStr
from typing import Optional
from app.core.roles import Role
from datetime import datetime


class AdminUserRead(BaseModel):
    id: str
    email: EmailStr
    name: str
    sur_name: str
    role: Role
    is_active: bool

    class Config:
        from_attributes = True

class RefreshTokenAdminRead(BaseModel):
    id: str
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: datetime
    user_agent: Optional[str]
    ip_address: Optional[str]
    is_revoked: bool

    class Config:
        from_attributes = True


class AdminUserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    role: Optional[Role] = None

    class Config:
        extra = "forbid"  #prevent mass assignment


class AdminCreateUser(BaseModel):
    email: EmailStr
    password: str
    name: str
    sur_name: str
    contact_number: str
    role: Role = Role.SUPER_ADMIN

class AdminDriverCreate(AdminCreateUser):
    vehicle_type: str
    vehicle_number: Optional[str] = None
    restaurant_id: Optional[str] = None
    role: Role = Role.DRIVER

class AdminRestaurantCreate(BaseModel):
    name: str
    address: str
    description: Optional[str] = None
    admin_email: EmailStr
    admin_password: str
    admin_name: str
    admin_sur_name: str
    admin_contact_number: str
