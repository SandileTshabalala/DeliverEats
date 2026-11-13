from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from app.core.config import settings
from app.core.roles import Role
from app.models.user import User


# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

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
    """
    Dependency to get the current authenticated user.

    Always loads the user from the database with the request's session, so the
    object is attached (relationships work) and a deactivated account or a role
    change takes effect immediately.
    """
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
    except JWTError:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None or payload.get("type") != "access":
        raise credentials_exception

    # Honour logout: access tokens are blacklisted in Redis until they expire.
    from app.core.security import is_token_blacklisted
    if await is_token_blacklisted(token):
        raise credentials_exception

    user = await run_in_threadpool(
        lambda: db.query(User).filter(User.id == user_id).first()
    )
    if user is None or not user.is_active:
        raise credentials_exception

    return user


# Roles that may use every role-protected endpoint.
PRIVILEGED_ROLES = (Role.SUPER_ADMIN, Role.ADMIN)


def require_role(*allowed_roles: Role, use_db: bool = True):
    """
    Universal role checker.

    Parameters:
    - allowed_roles: Roles allowed to access the endpoint
    - use_db: True -> fetch User from DB via get_current_user
              False -> check role directly from JWT (stateless)
    """

    def checker_db(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles and current_user.role not in PRIVILEGED_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user

    def checker_jwt(token: str = Depends(oauth2_scheme)):
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        role = payload.get("role")
        if role not in [r.value for r in allowed_roles] and role not in [r.value for r in PRIVILEGED_ROLES]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

        return payload

    return checker_db if use_db else checker_jwt