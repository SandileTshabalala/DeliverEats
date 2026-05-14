from pydantic import BaseModel
from decimal import Decimal
from typing import List, Optional   
from app.schemas.menu_item import MenuItemRead

class MenuBase(BaseModel):
    name: str

class MenuCreate(BaseModel):
    restaurant_id: str

class MenuItemCreate(BaseModel):
    name: str
    description: str | None
    price: Decimal
    image_url: Optional[str] = None

class MenuItemResponse(MenuItemCreate):
    id: str
    is_available: bool

    class Config:
        from_attributes = True

class MenuRead(MenuBase):
    id: str
    items: List[MenuItemRead] = []

    class Config:
        from_attributes = True

class MenuUpdate(BaseModel):
    name: Optional[str] = None