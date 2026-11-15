from pydantic import BaseModel
from decimal import Decimal
from typing import List, Optional


class PickedOption(BaseModel):
    group: str
    name: str
    price: Decimal

class OrderItemBase(BaseModel):
    menu_item_id: str
    quantity: int
    price: Decimal

class OrderItemCreate(OrderItemBase):
    order_id: str

class OrderItemRead(OrderItemBase):
    id: str
    name: str
    # what the customer picked ("Spice level: Hot", "Extras: Chips +R10")
    options: Optional[List[PickedOption]] = None

    class Config:
        from_attributes = True
