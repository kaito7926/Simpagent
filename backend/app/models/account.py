from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email_key", name="uq_users_email_key"),
        CheckConstraint("role in ('user', 'admin')", name="users_role_known"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    email_key: Mapped[str] = mapped_column(String(320), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="user", nullable=False, server_default=text("'user'"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, server_default=text("true"))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    scopes: Mapped[list["UserScope"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    identities: Mapped[list["Identity"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    local_credential: Mapped["LocalCredential | None"] = relationship(back_populates="user", cascade="all, delete-orphan")


class UserScope(Base):
    __tablename__ = "user_scopes"
    __table_args__ = (
        CheckConstraint(
            "scope in ('chat:read', 'chat:write', 'tool:websearch', 'tool:python', 'admin:read', 'admin:write')",
            name="user_scopes_scope_known",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    scope: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped[User] = relationship(back_populates="scopes")


class Identity(Base):
    __tablename__ = "identities"
    __table_args__ = (UniqueConstraint("issuer", "subject", name="uq_identities_issuer_subject"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    issuer: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    email_at_provider: Mapped[str | None] = mapped_column(String(320))
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped[User] = relationship(back_populates="identities")


class LocalCredential(Base):
    __tablename__ = "local_credentials"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    password_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped[User] = relationship(back_populates="local_credential")
