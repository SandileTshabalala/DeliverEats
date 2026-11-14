from sqlalchemy import Column, DateTime, String

from app.db.base import Base
from app.models.subscription import utcnow


class PlatformSetting(Base):
    """Settings the platform owner changes in the admin screen (key -> text value)."""
    __tablename__ = "platform_settings"

    key = Column(String(64), primary_key=True)
    value = Column(String(500), nullable=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
