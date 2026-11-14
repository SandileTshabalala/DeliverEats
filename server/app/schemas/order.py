from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.order_item import OrderItemRead
from app.schemas.driver import DriverRead
from app.utils.OrderStatus import OrderStatus


class OrderBase(BaseModel):
    restaurant_id: str
    total_amount: Decimal
    status: OrderStatus = OrderStatus.PENDING


class OrderItemCreate(BaseModel):
    menu_item_id: str
    quantity: int = Field(gt=0, le=50)


class OrderCreate(BaseModel):
    restaurant_id: str
    items: List[OrderItemCreate] = Field(min_length=1)
    address_id: Optional[str] = None
    # Accepted for backwards compatibility but IGNORED: the customer comes from
    # the token and the total is always recalculated from menu prices.
    customer_id: Optional[str] = None
    total: Optional[Decimal] = None


class OrderQuote(BaseModel):
    subtotal: Decimal
    delivery_fee: Decimal
    total: Decimal
    # Approximate driving distance; None when the shop or the address has no location
    distance_km: Optional[float] = None
    free_delivery: bool = False
    free_delivery_over: Optional[Decimal] = None


class OrderCustomer(BaseModel):
    """Only what a restaurant / driver needs to fulfil the order."""
    id: str
    name: Optional[str] = None
    sur_name: Optional[str] = None
    contact_number: Optional[str] = None

    class Config:
        from_attributes = True


class OrderRestaurant(BaseModel):
    id: str
    name: str
    address: str
    logo_img_url: Optional[str] = None

    class Config:
        from_attributes = True


class OrderRead(BaseModel):
    id: str
    status: OrderStatus
    total_amount: Decimal
    total: Decimal
    delivery_fee: Optional[Decimal] = None
    created_at: datetime
    customer_id: str
    restaurant_id: Optional[str] = None
    driver_id: Optional[str] = None
    restaurant_name: str
    customer: OrderCustomer
    driver: Optional[DriverRead] = None
    restaurant: Optional[OrderRestaurant] = None
    items: List[OrderItemRead]
    delivery_lat: Optional[float] = None
    delivery_lng: Optional[float] = None
    delivery_address: Optional[str] = None
    payment_status: str = "unpaid"
    payment_method: Optional[str] = None
    # The customer's own 1-5 rating of this order, once given
    my_rating: Optional[int] = None

    class Config:
        from_attributes = True


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=500)


class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    driver_id: Optional[str] = None
