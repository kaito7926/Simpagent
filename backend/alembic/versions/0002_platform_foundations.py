from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0002_platform_foundations"
down_revision = "0001_account_access"
branch_labels = None
depends_on = None


MESSAGE_ROLE_CHECK = "role in ('system', 'user', 'assistant', 'tool')"
TOOL_STATUS_CHECK = "status in ('queued', 'running', 'succeeded', 'failed', 'denied', 'timed_out')"


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_conversations_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_conversations")),
    )
    op.create_index(op.f("ix_conversations_user_id"), "conversations", ["user_id"], unique=False)

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint(MESSAGE_ROLE_CHECK, name=op.f("ck_messages_message_role_known")),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], name=op.f("fk_messages_conversation_id_conversations"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_messages")),
        sa.UniqueConstraint("conversation_id", "sequence_no", name="uq_messages_conversation_id_sequence_no"),
    )
    op.create_index(op.f("ix_messages_conversation_id"), "messages", ["conversation_id"], unique=False)

    op.create_table(
        "tool_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tool_name", sa.String(length=64), nullable=False),
        sa.Column("input_summary", sa.Text(), nullable=False),
        sa.Column("output_summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint(TOOL_STATUS_CHECK, name=op.f("ck_tool_executions_tool_status_known")),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], name=op.f("fk_tool_executions_conversation_id_conversations"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_tool_executions_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tool_executions")),
    )
    op.create_index(op.f("ix_tool_executions_user_id"), "tool_executions", ["user_id"], unique=False)
    op.create_index(op.f("ix_tool_executions_conversation_id"), "tool_executions", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_tool_executions_correlation_id"), "tool_executions", ["correlation_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_tool_executions_correlation_id"), table_name="tool_executions")
    op.drop_index(op.f("ix_tool_executions_conversation_id"), table_name="tool_executions")
    op.drop_index(op.f("ix_tool_executions_user_id"), table_name="tool_executions")
    op.drop_table("tool_executions")
    op.drop_index(op.f("ix_messages_conversation_id"), table_name="messages")
    op.drop_table("messages")
    op.drop_index(op.f("ix_conversations_user_id"), table_name="conversations")
    op.drop_table("conversations")
