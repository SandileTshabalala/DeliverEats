from pydantic import BaseModel
from decimal import Decimal

class OrderItemBase(BaseModel):
    menu_item_id: str
    quantity: int
    price: Decimal

class OrderItemCreate(OrderItemBase):
    order_id: str

class OrderItemRead(OrderItemBase):
    id: str
    name: str

    class Config:
        from_attributes = True
