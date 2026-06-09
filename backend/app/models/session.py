from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RefreshTokenFamily(Base):
    __tablename__ = "refresh_token_families"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    absolute_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoke_reason: Mapped[str | None] = mapped_column(String(64))

    tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="family")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
        UniqueConstraint("jti", name="uq_refresh_tokens_jti"),
        UniqueConstraint("parent_token_id", name="uq_refresh_tokens_parent_token_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    family_id: Mapped[UUID] = mapped_column(ForeignKey("refresh_token_families.id", ondelete="CASCADE"), nullable=False, index=True)
    jti: Mapped[str] = mapped_column(String(36), nullable=False)
    token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    parent_token_id: Mapped[UUID | None] = mapped_column(ForeignKey("refresh_tokens.id", ondelete="SET NULL"))
    replaced_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("refresh_tokens.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    family: Mapped[RefreshTokenFamily] = relationship(back_populates="tokens", foreign_keys=[family_id])
