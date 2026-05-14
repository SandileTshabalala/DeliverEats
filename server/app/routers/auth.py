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
@router.post("/refresh-access-token")
async def refresh_token(
    request: Request,
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
        request=request
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