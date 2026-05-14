from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app.models.user import User
from app.schemas.user import UserRead, UserUpdate
from app.services.user_service import get_user_by_id, update_user
from app.core.dependencies import get_db, require_role
from app.core.security import get_current_user
from app.core.roles import Role

router = APIRouter(tags=["Users"])

@router.get("/me", response_model=UserRead)
def current_user(
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    # Eagerly load addresses to ensure they are returned
    user_with_addresses = db.query(User).options(joinedload(User.addresses)).filter(User.id == user.id).first()
    return user_with_addresses

@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: str, current_user=Depends(require_role(Role.SUPER_ADMIN)), db: Session = Depends(get_db)):
    user = get_user_by_id(db, user_id)
    return user

@router.patch("/me", response_model=UserRead)
async def update_my_profile(
    payload: UserUpdate,
    user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the current user's profile.
    """
    updated_user = await update_user(db, user.id, payload.model_dump(exclude_unset=True))
    return updated_user
