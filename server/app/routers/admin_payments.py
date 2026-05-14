from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import List
from app.core.dependencies import get_db, require_role
from app.core.roles import Role
from app.models.payment_provider import PaymentProvider
from app.schemas.payment_provider import (
    PaymentProviderCreate,
    PaymentProviderAdminRead,
    PaymentProviderUpdate
)

router = APIRouter(prefix="/admin/payments", tags=["Admin Payments"])

@router.get("/providers", response_model=List[PaymentProviderAdminRead])
def list_providers(
    db: Session = Depends(get_db),
    admin=Depends(require_role(Role.SUPER_ADMIN, Role.ADMIN))
):
    return db.query(PaymentProvider).filter(PaymentProvider.is_active == True).all()

@router.post("/providers", response_model=PaymentProviderAdminRead)
def create_provider(
    payload: PaymentProviderCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_role(Role.SUPER_ADMIN, Role.ADMIN))
):
    db_provider = db.query(PaymentProvider).filter(
        PaymentProvider.provider_name == payload.provider_name
    ).first()
    if db_provider:
        raise HTTPException(status_code=400, detail="Provider already exists")
    
    provider = PaymentProvider(**payload.dict())
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider

@router.patch("/providers/{provider_id}", response_model=PaymentProviderAdminRead)
def update_provider(
    provider_id: str,
    payload: PaymentProviderUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_role(Role.SUPER_ADMIN, Role.ADMIN))
):
    provider = db.query(PaymentProvider).filter(PaymentProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(provider, key, value)
    
    db.commit()
    db.refresh(provider)
    return provider

@router.delete("/providers/{provider_id}")
def delete_provider(
    provider_id: str,
    db: Session = Depends(get_db),
    admin=Depends(require_role(Role.SUPER_ADMIN, Role.ADMIN))
):
    provider = db.query(PaymentProvider).filter(PaymentProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    try:
        db.delete(provider)
        db.commit()
    except IntegrityError:
        db.rollback()
        provider.is_active = False
        provider.enabled = False
        db.commit()
        
    return {"message": "Provider deleted"}
