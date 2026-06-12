from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0003_python_execution_contracts"
down_revision = "0003_chat_turn_state"
branch_labels = None
depends_on = None


TOOL_STATUS_CHECK = (
    "status in ('queued', 'running', 'succeeded', 'failed', 'denied', 'timed_out', "
    "'policy_error', 'limit_reached', 'infra_failure')"
)
PYTHON_PROFILE_CHECK = "profile_name in ('python-basic-v1', 'python-data-v1')"
PYTHON_ARTIFACT_TYPE_CHECK = "artifact_type in ('csv', 'json', 'txt', 'png')"
PYTHON_SNAPSHOT_SIZE_CHECK = "snapshot_size_bytes > 0 and snapshot_size_bytes <= 262144"
PYTHON_ARTIFACT_SIZE_CHECK = "size_bytes > 0 and size_bytes <= 524288"
SAFE_ARTIFACT_NAME_CHECK = r"name ~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$'"
SAFE_STORAGE_KEY_CHECK = r"storage_key ~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$'"
SAFE_SHA256_CHECK = r"sha256 ~ '^[0-9a-f]{64}$'"


def upgrade() -> None:
    op.drop_constraint(op.f("ck_tool_executions_tool_status_known"), "tool_executions", type_="check")
    op.create_check_constraint(
        op.f("ck_tool_executions_tool_status_known"),
        "tool_executions",
        TOOL_STATUS_CHECK,
    )

    op.create_table(
        "python_session_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("last_tool_execution_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("profile_name", sa.String(length=64), nullable=False),
        sa.Column("snapshot_blob", sa.LargeBinary(length=262144), nullable=False),
        sa.Column("snapshot_size_bytes", sa.Integer(), nullable=False),
        sa.Column("state_schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint(PYTHON_PROFILE_CHECK, name=op.f("ck_python_session_states_profile_name_known")),
        sa.CheckConstraint(PYTHON_SNAPSHOT_SIZE_CHECK, name=op.f("ck_python_session_states_snapshot_size_bounded")),
        sa.CheckConstraint("state_schema_version >= 1", name=op.f("ck_python_session_states_schema_version_positive")),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], name=op.f("fk_python_session_states_conversation_id_conversations"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["last_tool_execution_id"], ["tool_executions.id"], name=op.f("fk_python_session_states_last_tool_execution_id_tool_executions"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_python_session_states_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_python_session_states")),
        sa.UniqueConstraint("conversation_id", name="uq_python_session_states_conversation_id"),
    )
    op.create_index(op.f("ix_python_session_states_user_id"), "python_session_states", ["user_id"], unique=False)
    op.create_index(op.f("ix_python_session_states_conversation_id"), "python_session_states", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_python_session_states_last_tool_execution_id"), "python_session_states", ["last_tool_execution_id"], unique=False)
    op.create_index(op.f("ix_python_session_states_expires_at"), "python_session_states", ["expires_at"], unique=False)

    op.create_table(
        "python_artifact_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tool_execution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_type", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("storage_key", sa.String(length=128), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint(PYTHON_ARTIFACT_TYPE_CHECK, name=op.f("ck_python_artifact_records_artifact_type_known")),
        sa.CheckConstraint(PYTHON_ARTIFACT_SIZE_CHECK, name=op.f("ck_python_artifact_records_size_bounded")),
        sa.CheckConstraint(SAFE_ARTIFACT_NAME_CHECK, name=op.f("ck_python_artifact_records_name_safe")),
        sa.CheckConstraint(SAFE_STORAGE_KEY_CHECK, name=op.f("ck_python_artifact_records_storage_key_safe")),
        sa.CheckConstraint(SAFE_SHA256_CHECK, name=op.f("ck_python_artifact_records_sha256_known")),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], name=op.f("fk_python_artifact_records_conversation_id_conversations"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tool_execution_id"], ["tool_executions.id"], name=op.f("fk_python_artifact_records_tool_execution_id_tool_executions"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_python_artifact_records_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_python_artifact_records")),
        sa.UniqueConstraint("storage_key", name="uq_python_artifact_records_storage_key"),
    )
    op.create_index(op.f("ix_python_artifact_records_user_id"), "python_artifact_records", ["user_id"], unique=False)
    op.create_index(op.f("ix_python_artifact_records_conversation_id"), "python_artifact_records", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_python_artifact_records_tool_execution_id"), "python_artifact_records", ["tool_execution_id"], unique=False)
    op.create_index(op.f("ix_python_artifact_records_expires_at"), "python_artifact_records", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_python_artifact_records_expires_at"), table_name="python_artifact_records")
    op.drop_index(op.f("ix_python_artifact_records_tool_execution_id"), table_name="python_artifact_records")
    op.drop_index(op.f("ix_python_artifact_records_conversation_id"), table_name="python_artifact_records")
    op.drop_index(op.f("ix_python_artifact_records_user_id"), table_name="python_artifact_records")
    op.drop_table("python_artifact_records")

    op.drop_index(op.f("ix_python_session_states_expires_at"), table_name="python_session_states")
    op.drop_index(op.f("ix_python_session_states_last_tool_execution_id"), table_name="python_session_states")
    op.drop_index(op.f("ix_python_session_states_conversation_id"), table_name="python_session_states")
    op.drop_index(op.f("ix_python_session_states_user_id"), table_name="python_session_states")
    op.drop_table("python_session_states")

    op.drop_constraint(op.f("ck_tool_executions_tool_status_known"), "tool_executions", type_="check")
    op.create_check_constraint(
        op.f("ck_tool_executions_tool_status_known"),
        "tool_executions",
        "status in ('queued', 'running', 'succeeded', 'failed', 'denied', 'timed_out')",
    )
