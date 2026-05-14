from pydantic import BaseModel
from typing import List, Optional
from app.schemas.user import UserRead

class RestaurantBase(BaseModel):
    name: str
    address: str
    description: Optional[str] = None
    logo_img_url: Optional[str] = None

class RestaurantCreate(RestaurantBase):
    admin_id: str

class RestaurantResponse(BaseModel):
    id: str
    name: str
    address: str
    description: str | None
    is_active: bool
    logo_img_url: str | None = None

    class Config:
        from_attributes = True

class RestaurantRead(RestaurantBase):
    id: str
    admin: UserRead

    class Config:
        from_attributes = True

class RestaurantUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    logo_img_url: Optional[str] = None