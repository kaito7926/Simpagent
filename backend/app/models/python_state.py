from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, LargeBinary, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.python_contract import PYTHON_ARTIFACT_MAX_BYTES, PYTHON_STATE_MAX_BYTES


PYTHON_PROFILE_CHECK = "profile_name in ('python-basic-v1', 'python-data-v1')"
PYTHON_ARTIFACT_TYPE_CHECK = "artifact_type in ('csv', 'json', 'txt', 'png')"
PYTHON_SNAPSHOT_SIZE_CHECK = f"snapshot_size_bytes > 0 and snapshot_size_bytes <= {PYTHON_STATE_MAX_BYTES}"
PYTHON_ARTIFACT_SIZE_CHECK = f"size_bytes > 0 and size_bytes <= {PYTHON_ARTIFACT_MAX_BYTES}"
SAFE_ARTIFACT_NAME_CHECK = r"name ~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$'"
SAFE_STORAGE_KEY_CHECK = r"storage_key ~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$'"
SAFE_SHA256_CHECK = r"sha256 ~ '^[0-9a-f]{64}$'"


class PythonSessionState(Base):
    __tablename__ = "python_session_states"
    __table_args__ = (
        UniqueConstraint("conversation_id", name="uq_python_session_states_conversation_id"),
        CheckConstraint(PYTHON_PROFILE_CHECK, name="ck_python_session_states_profile_name_known"),
        CheckConstraint(PYTHON_SNAPSHOT_SIZE_CHECK, name="ck_python_session_states_snapshot_size_bounded"),
        CheckConstraint("state_schema_version >= 1", name="ck_python_session_states_schema_version_positive"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id: Mapped[UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    last_tool_execution_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tool_executions.id", ondelete="SET NULL"),
        index=True,
    )
    profile_name: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot_blob: Mapped[bytes] = mapped_column(LargeBinary(length=PYTHON_STATE_MAX_BYTES), nullable=False)
    snapshot_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    state_schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class PythonArtifactRecord(Base):
    __tablename__ = "python_artifact_records"
    __table_args__ = (
        UniqueConstraint("storage_key", name="uq_python_artifact_records_storage_key"),
        CheckConstraint(PYTHON_ARTIFACT_TYPE_CHECK, name="ck_python_artifact_records_artifact_type_known"),
        CheckConstraint(PYTHON_ARTIFACT_SIZE_CHECK, name="ck_python_artifact_records_size_bounded"),
        CheckConstraint(SAFE_ARTIFACT_NAME_CHECK, name="ck_python_artifact_records_name_safe"),
        CheckConstraint(SAFE_STORAGE_KEY_CHECK, name="ck_python_artifact_records_storage_key_safe"),
        CheckConstraint(SAFE_SHA256_CHECK, name="ck_python_artifact_records_sha256_known"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id: Mapped[UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    tool_execution_id: Mapped[UUID] = mapped_column(ForeignKey("tool_executions.id", ondelete="CASCADE"), nullable=False, index=True)
    artifact_type: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(128), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
