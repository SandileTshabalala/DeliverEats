import decimal
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum
from app.schemas.order_item import OrderItemRead
from app.schemas.user import UserRead
from app.schemas.driver import DriverRead
from app.schemas.restaurant import RestaurantRead
from decimal import Decimal
from app.utils.OrderStatus import OrderStatus

class OrderBase(BaseModel):
    restaurant_id: str
    total_amount: Decimal
    status: OrderStatus = OrderStatus.PENDING

class OrderItemCreate(BaseModel):
    menu_item_id: str
    quantity: int

class OrderCreate(BaseModel):
    restaurant_id: str
    customer_id: str
    items: List[OrderItemCreate]
    total: Decimal
    address_id: Optional[str] = None

class OrderRead(BaseModel):
    id: str
    status: OrderStatus
    total_amount: Decimal
    total: Decimal
    created_at: datetime
    restaurant_name: str
    customer: UserRead
    driver: Optional[DriverRead]
    restaurant: RestaurantRead
    items: List[OrderItemRead]
    delivery_lat: Optional[float] = None
    delivery_lng: Optional[float] = None
    delivery_address: Optional[str] = None

    class Config:
        from_attributes = True
        

class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    driver_id: Optional[str] = None