from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class UserAddressCreate(BaseModel):
    latitude: float
    longitude: float
    instructions: Optional[str] = None
    is_default: bool = False

class UserAddressRead(BaseModel):
    id: UUID
    latitude: float
    longitude: float
    formatted_address: str
    suburb: Optional[str]
    city: Optional[str]
    instructions: Optional[str]
    is_default: bool

    class Config:
        from_attributes = True
