from decimal import Decimal

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
    category: str | None = None
    categories: List[str] = []
    is_open: bool = True
    accepting_orders: bool = True
    opens_at: str | None = None
    closes_at: str | None = None
    # order of the menu sections chosen by the restaurant
    menu_sections: List[str] | None = None
    rating: float | None = None
    review_count: int = 0
    delivery_fee_from: Decimal | None = None
    delivery_per_km: bool = False
    free_delivery_over: Decimal | None = None

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