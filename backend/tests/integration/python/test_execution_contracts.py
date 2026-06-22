from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.repositories.accounts import AccountsRepository
from app.db.repositories.python_state import PythonStateRepository
from app.models.domain import Conversation, ToolExecution
from app.models.python_state import PythonArtifactRecord, PythonSessionState
from app.schemas.python import PythonArtifactType


@pytest.mark.integration
@pytest.mark.asyncio
async def test_python_state_repository_persists_owned_expiring_session_state(db_session) -> None:
    accounts = AccountsRepository(db_session)
    bundle = await accounts.create_user_with_local_credentials(
        email="python-user@example.test",
        password_hash="argon2-placeholder",
    )
    conversation = Conversation(user_id=bundle.user.id, title="Data cleanup")
    db_session.add(conversation)
    await db_session.flush()

    execution = ToolExecution(
        user_id=bundle.user.id,
        conversation_id=conversation.id,
        tool_name="python",
        input_summary="clean the uploaded rows",
        status="queued",
    )
    db_session.add(execution)
    await db_session.flush()

    repository = PythonStateRepository(db_session)
    expires_at = datetime.now(UTC) + timedelta(minutes=15)
    snapshot = await repository.upsert_session_state(
        conversation_id=conversation.id,
        user_id=bundle.user.id,
        tool_execution_id=execution.id,
        snapshot_blob=b"state-v1",
        expires_at=expires_at,
    )
    await db_session.commit()

    assert snapshot.user_id == bundle.user.id
    assert snapshot.conversation_id == conversation.id
    assert snapshot.last_tool_execution_id == execution.id
    assert snapshot.profile_name == "python-basic-v1"
    assert snapshot.snapshot_size_bytes == len(b"state-v1")
    assert snapshot.expires_at == expires_at


@pytest.mark.integration
@pytest.mark.asyncio
async def test_python_state_repository_hides_expired_state_from_active_reads(db_session) -> None:
    accounts = AccountsRepository(db_session)
    bundle = await accounts.create_user_with_local_credentials(
        email="python-expired@example.test",
        password_hash="argon2-placeholder",
    )
    conversation = Conversation(user_id=bundle.user.id, title="Expired state")
    db_session.add(conversation)
    await db_session.flush()

    execution = ToolExecution(
        user_id=bundle.user.id,
        conversation_id=conversation.id,
        tool_name="python",
        input_summary="build a dataframe",
        status="queued",
    )
    db_session.add(execution)
    await db_session.flush()

    repository = PythonStateRepository(db_session)
    await repository.upsert_session_state(
        conversation_id=conversation.id,
        user_id=bundle.user.id,
        tool_execution_id=execution.id,
        snapshot_blob=b"expired-state",
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    await db_session.commit()

    active_state = await repository.get_active_session_state(
        conversation_id=conversation.id,
        user_id=bundle.user.id,
        now=datetime.now(UTC),
    )

    assert active_state is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_python_artifact_records_use_reviewed_metadata_only(db_session) -> None:
    accounts = AccountsRepository(db_session)
    bundle = await accounts.create_user_with_local_credentials(
        email="python-artifacts@example.test",
        password_hash="argon2-placeholder",
    )
    conversation = Conversation(user_id=bundle.user.id, title="Artifacts")
    db_session.add(conversation)
    await db_session.flush()

    execution = ToolExecution(
        user_id=bundle.user.id,
        conversation_id=conversation.id,
        tool_name="python",
        input_summary="export the grouped totals",
        status="succeeded",
    )
    db_session.add(execution)
    await db_session.flush()

    repository = PythonStateRepository(db_session)
    expires_at = datetime.now(UTC) + timedelta(minutes=15)
    artifact = await repository.create_artifact(
        user_id=bundle.user.id,
        conversation_id=conversation.id,
        tool_execution_id=execution.id,
        artifact_type=PythonArtifactType.csv,
        name="totals.csv",
        storage_key=f"artifact-{uuid4()}",
        size_bytes=512,
        sha256="0" * 64,
        expires_at=expires_at,
    )
    await db_session.commit()

    rows = (
        await db_session.execute(
            select(PythonArtifactRecord).where(PythonArtifactRecord.tool_execution_id == execution.id)
        )
    ).scalars().all()

    assert artifact.user_id == bundle.user.id
    assert artifact.conversation_id == conversation.id
    assert artifact.expires_at == expires_at
    assert rows[0].artifact_type == PythonArtifactType.csv.value
    assert rows[0].sha256 == "0" * 64
    assert rows[0].storage_key.startswith("artifact-")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_python_contract_tables_are_registered_in_sqlalchemy_metadata() -> None:
    table_names = {table.name for table in PythonSessionState.metadata.sorted_tables}

    assert "python_session_states" in table_names
    assert "python_artifact_records" in table_names
