"""
The platform's business details: printed on subscription invoices and on the
Privacy and Terms pages, and shown in the landing page footer.

Set by the platform owner in Admin > Settings. A value saved there wins; a field
left empty there falls back to the env file (BUSINESS_NAME, BUSINESS_VAT_NUMBER, ...),
so an existing env setup keeps working.
"""
import time
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.platform_setting import PlatformSetting

# field -> setting in the env file
FIELDS = {
    "business_name": "BUSINESS_NAME",
    "business_address": "BUSINESS_ADDRESS",
    "support_email": "SUPPORT_EMAIL",
    "support_phone": "SUPPORT_PHONE",
    "vat_number": "BUSINESS_VAT_NUMBER",
}

# Read on every invoice and landing page: keep the saved values in memory briefly.
# (The API runs as one process, and saving clears this immediately.)
_CACHE_SECONDS = 60
_cache: Dict[str, object] = {"at": 0.0, "values": None}


def _saved(db: Optional[Session] = None) -> Dict[str, Optional[str]]:
    if _cache["values"] is not None and time.monotonic() - _cache["at"] < _CACHE_SECONDS:
        return _cache["values"]  # type: ignore[return-value]
    own_session = db is None
    if own_session:
        from app.db.session import SessionLocal
        db = SessionLocal()
    try:
        rows = db.query(PlatformSetting).filter(PlatformSetting.key.in_(list(FIELDS))).all()
        values = {row.key: row.value for row in rows}
    finally:
        if own_session:
            db.close()
    _cache.update(at=time.monotonic(), values=values)
    return values


def current(db: Optional[Session] = None) -> Dict[str, Optional[str]]:
    """Effective details: saved in the app, else from the env file, else None."""
    saved = _saved(db)
    return {field: (saved.get(field) or getattr(settings, env_name) or None) for field, env_name in FIELDS.items()}


def save(db: Session, changes: Dict[str, Optional[str]]) -> Dict[str, Optional[str]]:
    """Store what the owner typed. An empty value clears the field (the env file applies again)."""
    for field, value in changes.items():
        if field not in FIELDS:
            continue
        value = (value or "").strip() or None
        row = db.query(PlatformSetting).filter(PlatformSetting.key == field).first()
        if row:
            row.value = value
        else:
            db.add(PlatformSetting(key=field, value=value))
    db.commit()
    _cache.update(at=0.0, values=None)
    return current(db)


def display_name(details: Optional[Dict[str, Optional[str]]] = None) -> str:
    details = details or current()
    return details["business_name"] or settings.APP_NAME
