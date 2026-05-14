from datetime import timedelta
import secrets
import hashlib
from datetime import datetime, timezone
from jose import JWTError, jwt
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.refresh_tokens import RefreshToken
from app.core.security import (
    create_access_token,
    verify_password,
    hash_password,
    get_current_user,
    create_refresh_token
)
from app.core.config import settings
from app.core.dependencies import get_db
from starlette.concurrency import run_in_threadpool
from app.schemas.user import UserCreate
from app.core.cache import get_cache, set_cache, delete_cache


def authenticate_user(db: Session, email: str, password: str):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user

def set_refresh_token_cookie(response: Response, token_hash: str) -> None:
    """Set the refresh token as an HTTP-only cookie."""
    response.set_cookie(
        key="refresh_token",
        value=token_hash,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # days to seconds
        secure=not settings.DEBUG,  # Secure in production
        samesite="lax",
        # Removed path restriction to ensure the cookie is sent to /auth/refresh-access-token
        # path="/auth/refresh"  
    )

def clear_refresh_token_cookie(response: Response) -> None:
    """Clear the refresh token cookie."""
    response.delete_cookie(
        key="refresh_token",
        # path="/auth/refresh"
    )

def register(
    user_data: UserCreate, 
    db: Session = Depends(get_db)
):
    """Register a new user."""
    # Check if user already exists
    db_user = db.query(User).filter(User.email == user_data.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = hash_password(user_data.password)
    user = User(
        email=user_data.email,
        password_hash=hashed_password,
        name=user_data.name,
        sur_name=user_data.sur_name,
        contact_number=user_data.contact_number,
        role=user_data.role,
        is_active=True
    )
      
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


    #caching for user lookups
async def get_user_by_email(db: Session, email: str):
    cache_key = f"user:email:{email}"
    cached = await get_cache(cache_key)
    if cached:
        return cached
        
    user = db.query(User).filter(User.email == email).first()
    if user:
        await set_cache(cache_key, user, ttl=300)  # Cache for 5 minutes
    return user 

async def login(
    form_data: OAuth2PasswordRequestForm,
    request: Request,
    response: Response,
    db: Session
):
    user = await run_in_threadpool(authenticate_user, db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(
        data={"sub": user.id, "role": user.role.value}
    )

    refresh_token = await create_refresh_token(
        user_id=user.id,
        request=request,
        db=db
    )
    
    # Set cookie on the response object passed from router
    set_refresh_token_cookie(response, refresh_token)

    # Cache user for fast retrieval in get_current_user
    # CACHE KEY: user:{user_id}
    await set_cache(f"user:{user.id}", user, ttl=300) # 5 minutes

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


async def refresh_access_token(
    refresh_token: str,
    db: Session,
    request: Request
):
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

    def get_token_sync():
        return (
            db.query(RefreshToken)
            .filter(
                RefreshToken.token_hash == token_hash,
                RefreshToken.is_revoked == False,
                RefreshToken.expires_at > datetime.now(timezone.utc)
            )
            .first()
        )
    
    db_token = await run_in_threadpool(get_token_sync)

    # 🚨 Token reuse = breach
    if not db_token:
        try:
            payload = jwt.get_unverified_claims(refresh_token)
            user_id = payload.get("sub")
        except JWTError:
            user_id = None

        if user_id:
            await run_in_threadpool(
                lambda: db.query(RefreshToken).filter(
                    RefreshToken.user_id == user_id,
                    RefreshToken.is_revoked == False
                ).update({"is_revoked": True})
            )
            await run_in_threadpool(db.commit)

        raise HTTPException(
            status_code=401,
            detail="Refresh token reuse detected"
        )

    user = db.query(User).filter(User.id == db_token.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User inactive")

    # 🔁 Rotate refresh token
    db_token.revoke()

    new_refresh_token = await create_refresh_token(
        user_id=user.id,
        request=request,
        db=db
    )

    access_token = create_access_token(
        data={"sub": user.id, "role": user.role.value}
    )
    db_token.last_used_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Log out user by invalidating the refresh token."""
    # Get the refresh token from the request (e.g., from cookies)
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        # Mark the refresh token as inactive in threadpool
        def sync_revoke():
            db.query(RefreshToken).filter(
                RefreshToken.token_hash == token_hash,
                RefreshToken.user_id == current_user.id,
                RefreshToken.is_revoked == False
            ).update({"is_revoked": True})
            db.commit()
            
        await run_in_threadpool(sync_revoke)
    
    # Clear the refresh token cookie
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax"
    )
    
    # Invalidate user cache
    await delete_cache(f"user:{current_user.id}")
    
    return response

#logout from all devices
async def logout_all(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Log out user from all devices by revoking all refresh tokens."""
    # Revoke all user's refresh tokens
    # Revoke all user's refresh tokens
    def revoke_all_sync():
        db.query(RefreshToken).filter(
            RefreshToken.user_id == current_user.id,
            RefreshToken.is_revoked == False
        ).update({"is_revoked": True, "revoked_at": datetime.now(timezone.utc)})
        db.commit()

    await run_in_threadpool(revoke_all_sync)
    
    # Invalidate user cache
    await delete_cache(f"user:{current_user.id}")

    return {"message": "Logged out from all devices"}
