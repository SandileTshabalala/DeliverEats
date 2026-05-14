from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.schemas.payment import PaymentCreate, PaymentResponse
from app.schemas.payment_provider import PublicPaymentConfig
from app.models.payment_provider import PaymentProvider
from app.services.payment_service import create_payment
from app.core.dependencies import require_role
from app.core.roles import Role
from app.core.dependencies import get_db

router = APIRouter(prefix="/payments", tags=["Payments"])

@router.get("/config", response_model=List[PublicPaymentConfig])
def get_payment_config(db: Session = Depends(get_db)):
    """Returns enabled payment providers with public keys only."""
    return db.query(PaymentProvider).filter(
        PaymentProvider.enabled == True,
        PaymentProvider.is_active == True
    ).all()

@router.post("/", response_model=PaymentResponse)
def new_payment(payload: PaymentCreate, db: Session = Depends(get_db), user=Depends(require_role(Role.CUSTOMER))):
    return create_payment(db, payload.order_id, payload.amount, payload.provider_name, reference="auto_"+payload.order_id)
