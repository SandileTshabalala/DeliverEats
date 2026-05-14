from pydantic import BaseModel
from typing import Optional
from decimal import Decimal

class MenuItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: Decimal
    is_available: Optional[bool] = True

class MenuItemCreate(MenuItemBase):
    menu_id: str

class MenuItemRead(MenuItemBase):
    id: str

    class Config:
        from_attributes = True

class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    is_available: Optional[bool] = None