from __future__ import annotations

import pytest
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text


EXPECTED_TABLES = {
    "users",
    "user_scopes",
    "identities",
    "local_credentials",
    "refresh_token_families",
    "refresh_tokens",
    "security_events",
    "conversations",
    "messages",
    "tool_executions",
    "python_session_states",
    "python_artifact_records",
    "agent_runtime_settings",
}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_alembic_upgrade_creates_phase_one_and_python_tables(db_session) -> None:
    table_result = await db_session.execute(
        text("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public'")
    )
    table_names = {row[0] for row in table_result}
    assert EXPECTED_TABLES.issubset(table_names)


@pytest.mark.integration
def test_alembic_head_matches_latest_python_revision(alembic_config) -> None:
    script = ScriptDirectory.from_config(alembic_config)
    assert script.get_current_head() == "0004_agent_runtime_settings"


@pytest.mark.integration
def test_alembic_can_downgrade_and_upgrade_with_python_contracts(alembic_config) -> None:
    command.downgrade(alembic_config, "0001_account_access")
    command.upgrade(alembic_config, "head")
