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

SECRET_MASK = "********"


def serialize(provider: PaymentProvider) -> dict:
    """Admin view of a provider. The secret key is write-only: only a mask is returned."""
    config = dict(provider.config or {})
    if config.get("passphrase"):
        config["passphrase"] = SECRET_MASK
    return {
        "id": provider.id,
        "provider_name": provider.provider_name,
        "display_name": provider.display_name,
        "enabled": provider.enabled,
        "is_active": provider.is_active,
        "public_key": provider.public_key,
        "secret_key": SECRET_MASK if provider.secret_key else None,
        "config": config,
    }

@router.get("/providers", response_model=List[PaymentProviderAdminRead])
def list_providers(
    db: Session = Depends(get_db),
    admin=Depends(require_role(Role.SUPER_ADMIN, Role.ADMIN))
):
    return [serialize(p) for p in db.query(PaymentProvider).filter(PaymentProvider.is_active == True).all()]

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
    
    provider = PaymentProvider(**payload.model_dump())
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return serialize(provider)

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
    
    update_data = payload.model_dump(exclude_unset=True)

    # The UI only ever sees the mask: sending it (or nothing) back keeps the stored secret
    if update_data.get("secret_key") in (None, "", SECRET_MASK):
        update_data.pop("secret_key", None)
    if "config" in update_data:
        new_config = dict(update_data["config"] or {})
        if new_config.get("passphrase") == SECRET_MASK:
            new_config["passphrase"] = (provider.config or {}).get("passphrase")
        update_data["config"] = new_config

    for key, value in update_data.items():
        setattr(provider, key, value)

    db.commit()
    db.refresh(provider)
    return serialize(provider)

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
