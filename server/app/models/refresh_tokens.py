from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.db.base import Base

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    __table_args__ = (
        Index("idx_refresh_token_user", "user_id"),
        Index("idx_refresh_token_lookup", "token_hash", "is_revoked", "expires_at"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    token_hash = Column(String(64), nullable=False, unique=True)

    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    user_agent = Column(String(512), nullable=True)
    ip_address = Column(String(45), nullable=True)

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")

    @property
    def is_active(self) -> bool:
        return not self.is_revoked and self.expires_at > datetime.now(timezone.utc)

    def revoke(self) -> None:
        self.is_revoked = True
        self.revoked_at = datetime.now(timezone.utc)

    def mark_used(self) -> None:
        self.last_used_at = datetime.now(timezone.utc)
 