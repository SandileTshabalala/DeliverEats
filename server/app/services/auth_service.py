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
from app.core.roles import Role
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
        secure=settings.is_production,  # HTTPS-only cookie in production
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
        role=Role.CUSTOMER,  # never trust a role sent by the client
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
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been deactivated")

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

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


async def refresh_access_token(
    refresh_token: str,
    db: Session,
    request: Request,
    response: Response
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

    if not db_token:
        # Unknown, expired or already-rotated token. If it matches a revoked
        # token it was probably replayed: end all of that user's sessions.
        def revoke_family():
            stale = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
            if stale:
                db.query(RefreshToken).filter(
                    RefreshToken.user_id == stale.user_id,
                    RefreshToken.is_revoked == False
                ).update({"is_revoked": True, "revoked_at": datetime.now(timezone.utc)})
                db.commit()

        await run_in_threadpool(revoke_family)
        raise HTTPException(status_code=401, detail="Session expired, please log in again")

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
    db.refresh(user)

    # The refresh token is rotated on every use, so the browser MUST receive the
    # new one. Without this the next refresh sends the revoked token and the
    # user is logged out. It stays in the httpOnly cookie, never in the body.
    set_refresh_token_cookie(response, new_refresh_token)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
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
    
    # Blacklist the access token so it cannot be used until it expires
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        from app.core.security import add_token_to_blacklist
        await add_token_to_blacklist(auth_header[7:].strip())

    # Clear the refresh token cookie
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=settings.is_production,
        samesite="lax"
    )
    
    # Invalidate user cache
    await delete_cache(f"user_profile:{current_user.id}")
    
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
    await delete_cache(f"user_profile:{current_user.id}")

    return {"message": "Logged out from all devices"}



# --------------------------------------------------------------------------
# Password reset
# --------------------------------------------------------------------------
def _reset_key(token: str) -> str:
    return "lvovo:password_reset:" + hashlib.sha256(token.encode()).hexdigest()


def request_password_reset(db: Session, email: str) -> None:
    """Email a single-use link. Silent when the account does not exist."""
    from app.core.redis import redis_client
    from app.services.notification_service import send_notification

    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        return

    token = secrets.token_urlsafe(48)
    # Only a hash of the token is stored, and it expires on its own
    redis_client.setex(_reset_key(token), settings.PASSWORD_RESET_MINUTES * 60, user.id)
    send_notification(
        user.id, "Reset your password",
        f"We received a request to reset your password. This link works once and expires in "
        f"{settings.PASSWORD_RESET_MINUTES} minutes.\nIf you did not ask for this, you can ignore this email.",
        sms=False, email=True,
        button_label="Choose a new password",
        button_url=f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?token={token}",
    )


def reset_password(db: Session, token: str, new_password: str) -> None:
    from app.core.redis import redis_client

    key = _reset_key(token)
    user_id = redis_client.get(key)
    if isinstance(user_id, bytes):
        user_id = user_id.decode()
    user = db.query(User).filter(User.id == user_id).first() if user_id else None
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired. Please request a new one.")

    user.password_hash = hash_password(new_password)
    # Whoever knew the old password is signed out everywhere
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id, RefreshToken.is_revoked == False
    ).update({"is_revoked": True, "revoked_at": datetime.now(timezone.utc)})
    db.commit()
    redis_client.delete(key)  # single use
    redis_client.delete(f"lvovo:user_profile:{user.id}")
