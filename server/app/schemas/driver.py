from pydantic import BaseModel, Field
from typing import Optional

class DriverBase(BaseModel):
    name: Optional[str]
    sur_name: Optional[str]
    contact_number: Optional[str]
    vehicle_number: Optional[int] = None
    vehicle_type: Optional[str]
    is_active: Optional[bool] = True

class DriverProfileCreate(BaseModel):
    vehicle_type: str = Field(min_length=1, max_length=40)
    vehicle_number: Optional[str] = None

class DriverRead(BaseModel):
    id: str
    vehicle_type: str
    vehicle_number: Optional[str] = None
    is_available: bool
    # Who the driver is, so the restaurant and the customer can call them
    name: Optional[str] = None
    sur_name: Optional[str] = None
    contact_number: Optional[str] = None

    class Config:
        from_attributes = True

class DriverProfileRead(DriverRead):
    """The driver's own profile. (Not used inside orders, to avoid an extra lookup per order.)"""
    restaurant_id: Optional[str] = None
    restaurant_name: Optional[str] = None


class DriverUpdate(BaseModel):
    name: Optional[str] = None
    sur_name: Optional[str] = None
    contact_number: Optional[str] = None
    vehicle_number: Optional[str] = None
    is_active: Optional[bool] = None

class DriverStats(BaseModel):
    today_deliveries: int
    completed_deliveries: int
    total_earnings: float
    reliability_score: int
