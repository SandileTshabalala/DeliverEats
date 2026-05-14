from pydantic import BaseModel
from typing import Optional, Any

class PaymentProviderBase(BaseModel):
    provider_name: str
    display_name: str
    enabled: bool = True
    is_active: bool = True

class PaymentProviderCreate(PaymentProviderBase):
    public_key: Optional[str] = None
    secret_key: Optional[str] = None
    config: Optional[dict] = None

class PaymentProviderRead(PaymentProviderBase):
    id: str
    public_key: Optional[str] = None
    config: Optional[dict] = None

    class Config:
        from_attributes = True

class PaymentProviderAdminRead(PaymentProviderRead):
    secret_key: Optional[str] = None

class PaymentProviderUpdate(BaseModel):
    display_name: Optional[str] = None
    enabled: Optional[bool] = None
    public_key: Optional[str] = None
    secret_key: Optional[str] = None
    config: Optional[dict] = None
    is_active: Optional[bool] = None

class PublicPaymentConfig(BaseModel):
    provider_name: str
    display_name: str
    public_key: Optional[str] = None
    enabled: bool
