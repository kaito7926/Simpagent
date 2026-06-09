from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_account_access"
down_revision = None
branch_labels = None
depends_on = None


KNOWN_SCOPE_CHECK = "scope in ('chat:read', 'chat:write', 'tool:websearch', 'tool:python', 'admin:read', 'admin:write')"
KNOWN_ROLE_CHECK = "role in ('user', 'admin')"


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("email_key", sa.String(length=320), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint(KNOWN_ROLE_CHECK, name=op.f("ck_users_users_role_known")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email_key", name="uq_users_email_key"),
    )

    op.create_table(
        "user_scopes",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint(KNOWN_SCOPE_CHECK, name=op.f("ck_user_scopes_user_scopes_scope_known")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_user_scopes_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "scope", name=op.f("pk_user_scopes")),
    )

    op.create_table(
        "identities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("issuer", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("email_at_provider", sa.String(length=320), nullable=True),
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_identities_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_identities")),
        sa.UniqueConstraint("issuer", "subject", name="uq_identities_issuer_subject"),
    )
    op.create_index(op.f("ix_identities_user_id"), "identities", ["user_id"], unique=False)

    op.create_table(
        "local_credentials",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("password_updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_local_credentials_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_local_credentials")),
    )

    op.create_table(
        "refresh_token_families",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("last_rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("absolute_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoke_reason", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_refresh_token_families_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_token_families")),
    )
    op.create_index(op.f("ix_refresh_token_families_user_id"), "refresh_token_families", ["user_id"], unique=False)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("jti", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.LargeBinary(length=32), nullable=False),
        sa.Column("parent_token_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("replaced_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["family_id"], ["refresh_token_families.id"], name=op.f("fk_refresh_tokens_family_id_refresh_token_families"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_token_id"], ["refresh_tokens.id"], name=op.f("fk_refresh_tokens_parent_token_id_refresh_tokens"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["replaced_by_id"], ["refresh_tokens.id"], name=op.f("fk_refresh_tokens_replaced_by_id_refresh_tokens"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_tokens")),
        sa.UniqueConstraint("jti", name="uq_refresh_tokens_jti"),
        sa.UniqueConstraint("parent_token_id", name="uq_refresh_tokens_parent_token_id"),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
    )
    op.create_index(op.f("ix_refresh_tokens_family_id"), "refresh_tokens", ["family_id"], unique=False)

    op.create_table(
        "security_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_security_events_user_id_users"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_security_events")),
    )
    op.create_index(op.f("ix_security_events_event_type"), "security_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_security_events_user_id"), "security_events", ["user_id"], unique=False)
    op.create_index(op.f("ix_security_events_correlation_id"), "security_events", ["correlation_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_security_events_correlation_id"), table_name="security_events")
    op.drop_index(op.f("ix_security_events_user_id"), table_name="security_events")
    op.drop_index(op.f("ix_security_events_event_type"), table_name="security_events")
    op.drop_table("security_events")
    op.drop_index(op.f("ix_refresh_tokens_family_id"), table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_index(op.f("ix_refresh_token_families_user_id"), table_name="refresh_token_families")
    op.drop_table("refresh_token_families")
    op.drop_table("local_credentials")
    op.drop_index(op.f("ix_identities_user_id"), table_name="identities")
    op.drop_table("identities")
    op.drop_table("user_scopes")
    op.drop_table("users")
