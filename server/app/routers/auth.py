from fastapi import APIRouter, Depends, status, Request, HTTPException
from fastapi.responses import JSONResponse, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.models.user import User
from app.core.security import get_current_user
from app.core.dependencies import get_db
from app.schemas.refresh_token import AuthResponse
from app.schemas.user import UserCreate, UserRead
from app.services.auth_service import (register, login, refresh_access_token, logout, logout_all)

router = APIRouter(tags=["Authentication"])
 
@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    return register(user_data, db)


@router.post("/login", response_model=AuthResponse)
async def login_for_access_token(
    response: Response,
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    return await login(form_data, request, response, db)

#tokens
@router.post("/refresh-access-token", response_model=AuthResponse)
async def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        # Check for backwards compatibility or common mistakes
        refresh_token = request.cookies.get("refresh_access_token")
        
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    return await refresh_access_token(
        refresh_token=refresh_token,
        db=db,
        request=request,
        response=response
    )


@router.post("/logout")
async def logout_user(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return await logout(request, current_user, db)


@router.post("/logout-all")
async def logout_user_all(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return await logout_all(current_user, db)

@router.get("/me", response_model=UserRead)
def read_users_me(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return current_user


# ----------------------------
# FORGOT / RESET PASSWORD
# ----------------------------
from pydantic import BaseModel, EmailStr, Field  # noqa: E402

from app.services.auth_service import request_password_reset, reset_password  # noqa: E402


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    password: str = Field(min_length=8, max_length=200)


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Emails a reset link if the address belongs to an account. The answer is the
    same either way, so this cannot be used to find out who has an account.
    """
    request_password_reset(db, payload.email)
    return {"message": "If that email address has an account, we have sent a link to reset the password."}


@router.post("/reset-password")
def reset_password_route(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    reset_password(db, payload.token, payload.password)
    return {"message": "Your password has been changed. You can sign in now."}


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=200)


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Signed-in user changes their own password (the current one is required).
    Every OTHER device is signed out, as after a reset: if someone else knew the
    old password, changing it must lock them out. This device stays signed in.
    """
    import hashlib
    from datetime import datetime, timezone
    from app.core.security import hash_password, verify_password
    from app.models.refresh_tokens import RefreshToken

    user = db.query(User).filter(User.id == current_user.id).first()
    if not user or not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Your current password is not correct")
    if payload.new_password == payload.current_password:
        raise HTTPException(status_code=400, detail="Choose a password that is different from the current one")
    user.password_hash = hash_password(payload.new_password)
    others = db.query(RefreshToken).filter(RefreshToken.user_id == user.id, RefreshToken.is_revoked == False)  # noqa: E712
    this_device = request.cookies.get("refresh_token")
    if this_device:
        others = others.filter(RefreshToken.token_hash != hashlib.sha256(this_device.encode()).hexdigest())
    others.update({"is_revoked": True, "revoked_at": datetime.now(timezone.utc)}, synchronize_session=False)
    db.commit()
    from app.core.security import mark_password_changed
    mark_password_changed(user.id, keep_jti=getattr(request.state, "token_jti", None))
    return {"message": "Password changed. Other devices have been signed out."}
