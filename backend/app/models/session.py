from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects import postgresql
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
    auth_binding_method: Mapped[str] = mapped_column(String(32), nullable=False, default="bearer", server_default="bearer")
    key_thumbprint: Mapped[str | None] = mapped_column(String(128), index=True)
    binding_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

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


class SecurityReplayRecord(Base):
    __tablename__ = "security_replay_records"
    __table_args__ = (
        UniqueConstraint("artifact_type", "audience", "jti", name="uq_security_replay_records_artifact_audience_jti"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    jti: Mapped[str] = mapped_column(String(128), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(128), index=True)
    audience: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    conversation_id: Mapped[UUID | None] = mapped_column(index=True)
    binding_key_thumbprint: Mapped[str | None] = mapped_column(String(128), index=True)
    first_correlation_id: Mapped[str | None] = mapped_column(String(64), index=True)
    last_replay_correlation_id: Mapped[str | None] = mapped_column(String(64), index=True)
    consumed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    replayed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replay_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    event_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        postgresql.JSONB(astext_type=Text()),
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
