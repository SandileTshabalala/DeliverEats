from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.roles import Role
from app.models.user import User
from app.core.cache import get_cache, set_cache


# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Database dependency
def get_db() -> Generator:
    """Dependency that provides a database session"""
    from app.db.session import SessionLocal # Import here to avoid circular imports
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Get current user from JWT token
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Dependency to get the current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # 1. Check Cache
    cache_key = f"user:{user_id}"
    cached_user = await get_cache(cache_key)
    if cached_user:
        # If we cached the ORM object or dict, we might need to attach it to session if needed for lazy loading
        # But for basic auth checks, the cached object is fine.
        # However, usually we cache a dict. If `set_cache` pickles, it might be an object detached from session.
        # If we need it attached, we merge. For performance, let's return the object.
        # If `User` has relationships accessed later, this might fail if detached.
        # But `set_cache` implementation (pickle) usually preserves state but detaches.
        # Safest is to `db.merge(cached_user)` if we need it in session, but that hits DB? No, merge is local if key exists?
        # Actually `merge` checks DB if not in identity map.
        # Let's assume for now we return the object. If we hit "detached instance" errors, we fix.
        return cached_user

    # 2. DB Fallback
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    # 3. Cache it (TTL Should match session heavily or be short, e.g. 5 mins)
    await set_cache(cache_key, user, ttl=300)
    
    return user

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def require_role(*allowed_roles: Role, use_db: bool = True):
    """
    Universal role checker.

    Parameters:
    - allowed_roles: Roles allowed to access the endpoint
    - use_db: True -> fetch User from DB via get_current_user
              False -> check role directly from JWT (stateless)
    """

    def checker_db(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles and current_user.role != Role.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user

    def checker_jwt(token: str = Depends(oauth2_scheme)):
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        except jwt.JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        role = payload.get("role")
        if role not in [r.value for r in allowed_roles] and role != Role.ADMIN.value:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

        return payload

    return checker_db if use_db else checker_jwt