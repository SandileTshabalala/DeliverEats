from pydantic import BaseModel
from typing import Optional

class DriverBase(BaseModel):
    name: Optional[str]
    sur_name: Optional[str]
    contact_number: Optional[str]
    vehicle_number: Optional[int] = None
    vehicle_type: Optional[str]
    is_active: Optional[bool] = True

class DriverProfileCreate(BaseModel):
    vehicle_type: str
    vehicle_number: Optional[str] = None

class DriverRead(BaseModel):
    id: str
    vehicle_type: str
    vehicle_number: Optional[str]
    is_available: bool

    class Config:
        from_attributes = True

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
