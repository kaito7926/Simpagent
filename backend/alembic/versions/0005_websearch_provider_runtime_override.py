from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0005_websearch_override"
down_revision = "0004_agent_runtime_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agent_runtime_settings", sa.Column("value", sa.String(length=64), nullable=True))
    op.create_check_constraint(
        "ck_agent_runtime_settings_value_websearch_provider",
        "agent_runtime_settings",
        "value IS NULL OR value IN ('gemini', 'firecrawl')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_agent_runtime_settings_value_websearch_provider",
        "agent_runtime_settings",
        type_="check",
    )
    op.drop_column("agent_runtime_settings", "value")
