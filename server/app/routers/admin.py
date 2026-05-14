from app.core.roles import Role
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.dependencies import get_db, require_role
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.admin import (
    AdminUserRead,
    AdminUserUpdate,
    AdminCreateUser,
    AdminDriverCreate,
    AdminRestaurantCreate,
    RefreshTokenAdminRead
)
from app.schemas.restaurant import RestaurantResponse
from app.models.refresh_tokens import RefreshToken
from app.services.admin_service import AdminService

router = APIRouter(
    tags=["Admin"]
)

@router.get("/dashboard")
def admin_dashboard(
    user = Depends(require_role(Role.SUPER_ADMIN))
):
    return {"message": "Admin access"}

@router.get("/users", response_model=List[AdminUserRead])
def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    AdminService.ensure_admin(current_user)
    return AdminService.get_all_users(db)


#user sessions
#get method
@router.get(
    "/users/{user_id}/sessions",
    response_model=List[RefreshTokenAdminRead]
)
def list_user_sessions(
    user_id: str,
    db: Session = Depends(get_db),
    admin=Depends(require_role(Role.SUPER_ADMIN))
):
    return db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id
    ).all()

#post 
@router.post(
    "/sessions/{token_id}/revoke"
)
def revoke_session(
    token_id: str,
    db: Session = Depends(get_db),
    admin=Depends(require_role(Role.SUPER_ADMIN))
):
    token = db.query(RefreshToken).filter(
        RefreshToken.id == token_id
    ).first()

    if not token:
        raise HTTPException(404, "Session not found")

    token.revoke()
    db.commit()

    return {"message": "Session revoked"}



@router.get("/users/{user_id}", response_model=AdminUserRead)
def get_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    AdminService.ensure_admin(current_user)
    return AdminService.get_user_by_id(user_id, db)


@router.patch("/users/{user_id}", response_model=AdminUserRead)
def update_user(
    user_id: str,
    payload: AdminUserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    AdminService.ensure_admin(current_user)
    return AdminService.update_user(user_id, payload, db)


@router.post("/users", response_model=AdminUserRead)
def create_admin(
    payload: AdminCreateUser,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    AdminService.ensure_admin(current_user)
    return AdminService.create_admin_user(payload, db)


@router.post("/drivers", response_model=AdminUserRead)
def create_driver(
    payload: AdminDriverCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    AdminService.ensure_admin(current_user)
    return AdminService.create_driver_user(payload, db)


@router.post("/restaurants", response_model=RestaurantResponse)
def create_restaurant(
    payload: AdminRestaurantCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    AdminService.ensure_admin(current_user)
    return AdminService.create_restaurant_with_admin(payload, db)


@router.delete("/users/{user_id}")
def deactivate_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    AdminService.ensure_admin(current_user)
    return AdminService.deactivate_user(user_id, db)

@router.post("/users/{user_id}/logout-all")
def force_logout_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin=Depends(require_role(Role.SUPER_ADMIN))
):
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.is_revoked == False
    ).update({"is_revoked": True})

    db.commit()
    return {"message": "User logged out everywhere"}
