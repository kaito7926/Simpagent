from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003_chat_turn_state"
down_revision = "0002_platform_foundations"
branch_labels = None
depends_on = None


MESSAGE_STATUS_CHECK = "status in ('pending', 'completed', 'failed')"


def upgrade() -> None:
    op.add_column("messages", sa.Column("client_message_id", sa.String(length=128), nullable=True))
    op.add_column(
        "messages",
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'completed'")),
    )
    op.create_check_constraint(
        op.f("ck_messages_message_status_known"),
        "messages",
        MESSAGE_STATUS_CHECK,
    )
    op.create_index(
        "ix_messages_conversation_client_message_id_unique",
        "messages",
        ["conversation_id", "client_message_id"],
        unique=True,
        postgresql_where=sa.text("client_message_id IS NOT NULL"),
    )
    op.create_index(
        op.f("ix_messages_conversation_id_status"),
        "messages",
        ["conversation_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_messages_conversation_id_status"), table_name="messages")
    op.drop_index("ix_messages_conversation_client_message_id_unique", table_name="messages")
    op.drop_constraint(op.f("ck_messages_message_status_known"), "messages", type_="check")
    op.drop_column("messages", "status")
    op.drop_column("messages", "client_message_id")
