"""
Encryption for secrets that belong to restaurants (their PayFast merchant key
and passphrase), so a database leak or backup does not expose them.

Set ENCRYPTION_KEY in the environment (any long random string). If it is not
set, a key is derived from JWT_SECRET_KEY so things work out of the box, but
then changing the JWT secret makes stored secrets unreadable and restaurants
would have to enter them again.
"""
import base64
import hashlib
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _fernet() -> Fernet:
    secret = settings.ENCRYPTION_KEY or f"restaurant-secrets:{settings.JWT_SECRET_KEY}"
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
    return Fernet(key)


def encrypt(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt(token: Optional[str]) -> Optional[str]:
    if not token:
        return None
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        return None  # key was changed: treat as "not configured"
