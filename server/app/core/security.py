import bcrypt
import hashlib
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from fastapi import Request, BackgroundTasks
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.redis import redis_client
from app.core.dependencies import get_db
from app.models.user import User
from app.models.refresh_tokens import RefreshToken

# Password hashing
#
# Uses the `bcrypt` package directly. passlib (last released in 2020) crashes
# with current bcrypt versions ("password cannot be longer than 72 bytes"),
# which broke registration and login on any fresh install. Hashes are the same
# $2b$ format, so every existing password keeps working.
BCRYPT_ROUNDS = 12
# bcrypt only reads the first 72 bytes; cut explicitly so long passwords work
_BCRYPT_MAX_BYTES = 72
# Devices one account can stay signed in on at the same time
MAX_SESSIONS_PER_USER = 10

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)


def _password_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """Hash a password for storing."""
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("ascii")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a stored password against one provided by user."""
    try:
        return bcrypt.checkpw(_password_bytes(plain_password), hashed_password.encode("ascii"))
    except (ValueError, TypeError, AttributeError):
        return False  # malformed or missing hash: simply not a match


def generate_secure_token(length: int = 64) -> Tuple[str, str]:
    """Generate a secure random token and its hash."""
    alphabet = string.ascii_letters + string.digits
    token = ''.join(secrets.choice(alphabet) for _ in range(length))
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return token, token_hash

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a new access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Add standard claims
    to_encode.update({
        "exp": expire,
        "type": "access",
        "iat": datetime.now(timezone.utc),
        "jti": secrets.token_urlsafe(16)  # Unique identifier for the token
    })
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt

async def create_refresh_token(
    user_id: str,
    request: Optional[Request] = None,
    db: Optional[Session] = None
) -> str:
    """Create a new refresh token."""
    # Generate token
    token, token_hash = generate_secure_token()

    # Get client info for token binding
    user_agent = request.headers.get("user-agent", "") if request else ""
    ip_address = request.client.host if request and hasattr(request, 'client') else "0.0.0.0"

    # Create token record in database
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    if db is not None:
        # Each device keeps its own session: signing in on the phone must not
        # sign the restaurant's tablet out. (Refreshing revokes the one token it
        # used; a replayed old token still ends every session.) Only the oldest
        # sessions beyond MAX_SESSIONS_PER_USER are ended.
        def sync_db_ops():
            active = (
                db.query(RefreshToken.id)
                .filter(RefreshToken.user_id == user_id, RefreshToken.is_revoked == False)  # noqa: E712
                .order_by(RefreshToken.created_at.desc())
                .offset(MAX_SESSIONS_PER_USER - 1)
                .all()
            )
            if active:
                db.query(RefreshToken).filter(RefreshToken.id.in_([row.id for row in active])).update(
                    {"is_revoked": True, "revoked_at": datetime.now(timezone.utc)}, synchronize_session=False
                )

            db_token = RefreshToken(
                token_hash=token_hash,
                user_id=user_id,
                expires_at=expires_at,
                user_agent=user_agent[:512],
                ip_address=ip_address
            )
            db.add(db_token)
            db.commit()
            
        await run_in_threadpool(sync_db_ops)
    
    return token

def decode_token(token: str, secret_key: str) -> Dict[str, Any]:
    """Decode and verify a JWT token with enhanced validation."""
    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[settings.JWT_ALGORITHM],
            options={
                "require": ["exp", "iat", "jti"],  # Required claims
                "verify_aud": False,
                "verify_iss": False
            }
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get the current user from the token with enhanced security checks."""
    oauth2_scheme = OAuth2PasswordBearer(
        tokenUrl="/auth/login",
        auto_error=True
    )


    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Decode token
        payload = decode_token(token, settings.JWT_SECRET_KEY)
        
        # Check token type
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if token is blacklisted
        if await is_token_blacklisted(token) or issued_before_password_change(payload):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
        request.state.token_jti = payload.get("jti")

        # Get user ID from payload
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 🚀 PERFORMANCE: Try to get user from Redis cache first
        from app.core.cache import get_cache, set_cache
        
        cache_key = f"user_profile:{user_id}"
        cached_user = await get_cache(cache_key)
        
        if cached_user:
            # Reconstruct a detached User object from cached data
            # This avoids a DB query for the user on every request
            user = User(**cached_user)
            request.state.user = user
            return user

        # 🗄️ FALLBACK: Get user from DB if not in cache
        user = await run_in_threadpool(
            lambda: db.query(User).filter(User.id == user_id).first()
        )
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # 💾 CACHE: Store user profile data in Redis (TTL: 5 minutes)
        user_data = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "sur_name": user.sur_name,
            "contact_number": user.contact_number,
            "role": user.role,
            "is_active": user.is_active
        }
        await set_cache(cache_key, user_data, ttl=300)
            
        # Optional: update cache if needed (though PK lookup is already very fast)
            
        # Add user to request state for logging/monitoring
        request.state.user = user
        return user
        
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# ---------------------------------------------------------------- password changed
# After a password change or reset, sign-ins made BEFORE it stop working at once,
# not only when their access token runs out (up to an hour later). Kept in Redis
# just as long as an access token can live, so no database column is needed.
def _password_changed_key(user_id: str) -> str:
    return f"lvovo:password_changed:{user_id}"


def mark_password_changed(user_id: str, keep_jti: Optional[str] = None) -> None:
    """Reject this user's older access tokens. `keep_jti` = the device that made the change stays in."""
    import json
    import time
    try:
        redis_client.setex(
            _password_changed_key(user_id),
            (settings.ACCESS_TOKEN_EXPIRE_MINUTES + 5) * 60,
            json.dumps({"at": int(time.time()), "keep": keep_jti}),
        )
    except Exception as e:
        import logging
        logging.error(f"Could not record password change: {e}")


def issued_before_password_change(payload: Dict[str, Any]) -> bool:
    import json
    try:
        raw = redis_client.get(_password_changed_key(str(payload.get("sub"))))
    except Exception:
        return False  # Redis down: same as the blacklist, do not lock everyone out
    if not raw:
        return False
    changed = json.loads(raw)
    if changed.get("keep") and payload.get("jti") == changed["keep"]:
        return False
    return int(payload.get("iat") or 0) < int(changed["at"])


async def is_token_blacklisted(token: str) -> bool:
    """Check if a token is blacklisted in Redis."""
    try:
        from app.core.redis import get_async_redis
        redis = await get_async_redis()
        
        # Create a hash of the token to use as the key
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        key = f"blacklist:{token_hash}"
        
        # Check if the token is in the blacklist
        exists = await redis.exists(key)
        return bool(exists)
    except Exception as e:
        # If Redis is down, fail securely by considering the token as NOT blacklisted
        # to prevent app-wide denial of service if Redis is down.
        import logging
        logging.error(f"Redis error in is_token_blacklisted: {e}")
        return False

async def add_token_to_blacklist(token: str, expire_in_seconds: Optional[int] = None) -> None:
    """Add a token to the blacklist with an optional expiration time."""
    try:
        # Create a hash of the token to use as the key
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        key = f"blacklist:{token_hash}"
        
        # If no expiration is provided, use the token's expiration
        if expire_in_seconds is None:
            try:
                # Extract expiration from token
                payload = jwt.get_unverified_claims(token)
                expire_in_seconds = int(payload["exp"] - datetime.now(timezone.utc).timestamp())
                if expire_in_seconds < 0:
                    return  # Token already expired
            except (JWTError, KeyError):
                expire_in_seconds = 3600  # Default to 1 hour if can't determine
        
        # Add to Redis with expiration
        from app.core.redis import get_async_redis
        redis = await get_async_redis()
        await redis.setex(key, expire_in_seconds, "1")
    except Exception as e:
        # Log the error but don't fail the request
        import logging
        logging.error(f"Failed to blacklist token: {e}")
def revoke_refresh_token(token: str, db: Session) -> bool:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    updated = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == token_hash, RefreshToken.is_revoked == False)
        .update(
            {
                "is_revoked": True,
                "revoked_at": datetime.now(timezone.utc),
            }
        )
    )
    db.commit()
    return updated > 0
 