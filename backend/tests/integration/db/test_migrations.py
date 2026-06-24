from __future__ import annotations

from uuid import uuid4

import pytest
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


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
    assert script.get_current_head() == "0006_encrypt_message_content"


@pytest.mark.integration
def test_alembic_can_downgrade_and_upgrade_with_python_contracts(alembic_config) -> None:
    command.downgrade(alembic_config, "0001_account_access")
    command.upgrade(alembic_config, "head")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_message_content_migration_encrypts_plaintext_rows_and_restores_on_downgrade(
    alembic_config,
    postgres_url,
) -> None:
    user_id = uuid4()
    conversation_id = uuid4()
    message_id = uuid4()
    original_content = "Plaintext row created before message encryption rollout."

    async def _execute(statement: str, params: dict | None = None):
        engine = create_async_engine(postgres_url, future=True)
        try:
            async with engine.begin() as conn:
                result = await conn.execute(text(statement), params or {})
                return result
        finally:
            await engine.dispose()

    try:
        command.downgrade(alembic_config, "0004_agent_runtime_settings")

        await _execute(
            """
            INSERT INTO users (id, email, email_key, role, is_active, is_demo)
            VALUES (:id, :email, :email_key, 'user', true, false)
            """,
            {
                "id": user_id,
                "email": "migration-encryption@example.test",
                "email_key": "migration-encryption@example.test",
            },
        )
        await _execute(
            """
            INSERT INTO conversations (id, user_id, title)
            VALUES (:id, :user_id, :title)
            """,
            {
                "id": conversation_id,
                "user_id": user_id,
                "title": "Migration encryption regression",
            },
        )
        await _execute(
            """
            INSERT INTO messages (id, conversation_id, sequence_no, role, status, content)
            VALUES (:id, :conversation_id, 1, 'user', 'completed', :content)
            """,
            {
                "id": message_id,
                "conversation_id": conversation_id,
                "content": original_content,
            },
        )

        command.upgrade(alembic_config, "0006_encrypt_message_content")
        encrypted_content = (
            await _execute(
                "SELECT content FROM messages WHERE id = :id",
                {"id": message_id},
            )
        ).scalar_one()

        assert encrypted_content.startswith("enc-v1:")
        assert encrypted_content != original_content
        assert original_content not in encrypted_content

        command.downgrade(alembic_config, "0004_agent_runtime_settings")
        restored_content = (
            await _execute(
                "SELECT content FROM messages WHERE id = :id",
                {"id": message_id},
            )
        ).scalar_one()

        assert restored_content == original_content
    finally:
        command.upgrade(alembic_config, "head")
