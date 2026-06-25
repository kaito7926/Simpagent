from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0007_sender_constrained_replay"
down_revision = "0006_encrypt_message_content"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "refresh_token_families",
        sa.Column("auth_binding_method", sa.String(length=32), server_default="bearer", nullable=False),
    )
    op.add_column("refresh_token_families", sa.Column("key_thumbprint", sa.String(length=128), nullable=True))
    op.add_column("refresh_token_families", sa.Column("binding_created_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_refresh_token_families_key_thumbprint"), "refresh_token_families", ["key_thumbprint"], unique=False)

    op.create_table(
        "security_replay_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("jti", sa.String(length=128), nullable=False),
        sa.Column("subject", sa.String(length=128), nullable=True),
        sa.Column("audience", sa.String(length=128), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("binding_key_thumbprint", sa.String(length=128), nullable=True),
        sa.Column("first_correlation_id", sa.String(length=64), nullable=True),
        sa.Column("last_replay_correlation_id", sa.String(length=64), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("replayed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replay_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_security_replay_records")),
        sa.UniqueConstraint("artifact_type", "audience", "jti", name="uq_security_replay_records_artifact_audience_jti"),
    )
    op.create_index(op.f("ix_security_replay_records_artifact_type"), "security_replay_records", ["artifact_type"], unique=False)
    op.create_index(op.f("ix_security_replay_records_subject"), "security_replay_records", ["subject"], unique=False)
    op.create_index(op.f("ix_security_replay_records_audience"), "security_replay_records", ["audience"], unique=False)
    op.create_index(op.f("ix_security_replay_records_conversation_id"), "security_replay_records", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_security_replay_records_binding_key_thumbprint"), "security_replay_records", ["binding_key_thumbprint"], unique=False)
    op.create_index(op.f("ix_security_replay_records_first_correlation_id"), "security_replay_records", ["first_correlation_id"], unique=False)
    op.create_index(op.f("ix_security_replay_records_last_replay_correlation_id"), "security_replay_records", ["last_replay_correlation_id"], unique=False)
    op.create_index(op.f("ix_security_replay_records_expires_at"), "security_replay_records", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_security_replay_records_expires_at"), table_name="security_replay_records")
    op.drop_index(op.f("ix_security_replay_records_last_replay_correlation_id"), table_name="security_replay_records")
    op.drop_index(op.f("ix_security_replay_records_first_correlation_id"), table_name="security_replay_records")
    op.drop_index(op.f("ix_security_replay_records_binding_key_thumbprint"), table_name="security_replay_records")
    op.drop_index(op.f("ix_security_replay_records_conversation_id"), table_name="security_replay_records")
    op.drop_index(op.f("ix_security_replay_records_audience"), table_name="security_replay_records")
    op.drop_index(op.f("ix_security_replay_records_subject"), table_name="security_replay_records")
    op.drop_index(op.f("ix_security_replay_records_artifact_type"), table_name="security_replay_records")
    op.drop_table("security_replay_records")

    op.drop_index(op.f("ix_refresh_token_families_key_thumbprint"), table_name="refresh_token_families")
    op.drop_column("refresh_token_families", "binding_created_at")
    op.drop_column("refresh_token_families", "key_thumbprint")
    op.drop_column("refresh_token_families", "auth_binding_method")
