from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.orm import Session
from app.schemas.user_address import UserAddressCreate, UserAddressRead
from app.services.user_address_service import create_user_address, update_user_address, delete_user_address
from app.services.geocoding_service import forward_geocode, reverse_geocode
from app.core.dependencies import get_db, get_current_user

router = APIRouter(prefix="/addresses", tags=["Addresses"])

from app.core.rate_limit import rate_limit

@router.post("", response_model=UserAddressRead, status_code=status.HTTP_201_CREATED)
@rate_limit("addresses", limit=10, window=60)
def add_address(
    request: Request,
    payload: UserAddressCreate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    return create_user_address(db, user.id, payload)

@router.put("/{address_id}", response_model=UserAddressRead)
def update_address(
    address_id: str,
    payload: UserAddressCreate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    return update_user_address(db, user.id, address_id, payload)

@router.delete("/{address_id}")
def delete_address(
    address_id: str,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    delete_user_address(db, user.id, address_id)
    return {"message": "Address deleted"}

@router.get("/geocode")
def geocode_address(
    request: Request,
    q: str,
    user = Depends(get_current_user)
):
    return forward_geocode(q)

@router.get("/reverse-geocode")
def reverse_geocode_address(
    request: Request,
    lat: float,
    lng: float,
    user = Depends(get_current_user)
):
    return reverse_geocode(lat, lng)
