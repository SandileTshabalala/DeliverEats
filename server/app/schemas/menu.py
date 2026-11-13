from pydantic import BaseModel, Field
from decimal import Decimal
from typing import List, Optional   
from app.schemas.menu_item import MenuItemRead

class MenuBase(BaseModel):
    name: str

class MenuCreate(BaseModel):
    restaurant_id: str

class MenuItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    price: Decimal = Field(gt=0)
    image_url: Optional[str] = None


class MenuItemUpdate(BaseModel):
    """Only these fields can be edited (the old endpoint accepted any column)."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(default=None, gt=0)
    image_url: Optional[str] = None
    is_available: Optional[bool] = None

    class Config:
        extra = "forbid"

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