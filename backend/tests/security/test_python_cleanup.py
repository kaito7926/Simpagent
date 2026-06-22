from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import select

from app.db.repositories.accounts import AccountsRepository
from app.db.repositories.python_state import PythonStateRepository
from app.models.domain import Conversation, ToolExecution
from app.models.python_state import PythonArtifactRecord, PythonSessionState
from app.python_contract import PythonArtifactType, PythonExecutionProfile, PythonExecutionStatus
from app.schemas.python import PythonExecutionResult
from app.services.python_sessions import PythonSessionsService
from app.tools.python_client import PythonExecutionResponse


async def _create_owner_conversation_and_execution(db_session, *, email: str) -> tuple[UUID, UUID, UUID]:
    async with db_session.begin():
        accounts = AccountsRepository(db_session)
        bundle = await accounts.create_user_with_local_credentials(
            email=email,
            password_hash="not-used-in-python-tests",
        )
        conversation = Conversation(user_id=bundle.user.id, title="Cleanup")
        db_session.add(conversation)
        await db_session.flush()
        execution = ToolExecution(
            user_id=bundle.user.id,
            conversation_id=conversation.id,
            tool_name="python",
            input_summary="cleanup",
            output_summary="status=succeeded",
            status="succeeded",
            duration_ms=12,
        )
        db_session.add(execution)
        await db_session.flush()
        return bundle.user.id, conversation.id, execution.id


def _result(*, execution_id: UUID, profile_name: PythonExecutionProfile) -> PythonExecutionResult:
    return PythonExecutionResult(
        execution_id=execution_id,
        status=PythonExecutionStatus.succeeded,
        summary="Reviewed Python execution completed successfully.",
        duration_ms=33,
        profile_name=profile_name,
        stdout_excerpt="ok",
        stderr_excerpt=None,
        artifacts=[],
        limit_triggered=None,
        denial_reason=None,
        policy_error_code=None,
        infra_failure_reason=None,
        retryable=False,
        correlation_id="corr-cleanup",
    )


@pytest.mark.security
@pytest.mark.asyncio
async def test_get_active_session_cleans_expired_snapshot_and_payloads_but_preserves_410_record(
    db_session,
    settings,
    tmp_path: Path,
) -> None:
    now = datetime(2026, 6, 13, 3, 0, tzinfo=UTC)
    owner_id, conversation_id, execution_id = await _create_owner_conversation_and_execution(
        db_session,
        email="python-cleanup-expired@example.test",
    )
    repository = PythonStateRepository(db_session)
    await repository.upsert_session_state(
        conversation_id=conversation_id,
        user_id=owner_id,
        tool_execution_id=execution_id,
        snapshot_blob=b'{"version":1,"binding_names":["frame"],"pickle_b64":"gAR9lC4="}',
        expires_at=now - timedelta(seconds=1),
        profile_name=PythonExecutionProfile.basic,
    )
    artifact = await repository.create_artifact(
        user_id=owner_id,
        conversation_id=conversation_id,
        tool_execution_id=execution_id,
        artifact_type=PythonArtifactType.csv,
        name="report.csv",
        storage_key="expired-report.csv",
        size_bytes=20,
        sha256="a" * 64,
        expires_at=now - timedelta(seconds=1),
    )
    await db_session.commit()
    (tmp_path / artifact.storage_key).write_text("quarter,total\nQ1,10\n", encoding="utf-8")

    service = PythonSessionsService(
        db_session,
        settings=settings.model_copy(update={"python_artifact_storage_dir": str(tmp_path)}),
        clock=lambda: now,
    )

    active = await service.get_active_session(conversation_id=conversation_id, user_id=owner_id)

    assert active is None
    assert not (tmp_path / artifact.storage_key).exists()
    assert await db_session.scalar(
        select(PythonSessionState).where(PythonSessionState.conversation_id == conversation_id)
    ) is None

    record = await repository.get_artifact_for_owner(artifact_id=artifact.id, user_id=owner_id)
    assert record is not None

    candidate = await service.resolve_artifact_download(artifact_id=artifact.id, user_id=owner_id)
    assert candidate is not None
    assert candidate.expired is True
    assert candidate.path.exists() is False


@pytest.mark.security
@pytest.mark.asyncio
async def test_persist_execution_response_extends_active_artifacts_without_reactivating_expired_payloads(
    db_session,
    settings,
    tmp_path: Path,
) -> None:
    now = datetime(2026, 6, 13, 3, 30, tzinfo=UTC)
    owner_id, conversation_id, execution_id = await _create_owner_conversation_and_execution(
        db_session,
        email="python-cleanup-sliding@example.test",
    )
    repository = PythonStateRepository(db_session)
    active_artifact = await repository.create_artifact(
        user_id=owner_id,
        conversation_id=conversation_id,
        tool_execution_id=execution_id,
        artifact_type=PythonArtifactType.csv,
        name="active.csv",
        storage_key="active.csv",
        size_bytes=12,
        sha256="b" * 64,
        expires_at=now + timedelta(minutes=2),
    )
    expired_artifact = await repository.create_artifact(
        user_id=owner_id,
        conversation_id=conversation_id,
        tool_execution_id=execution_id,
        artifact_type=PythonArtifactType.csv,
        name="expired.csv",
        storage_key="expired.csv",
        size_bytes=12,
        sha256="c" * 64,
        expires_at=now - timedelta(seconds=1),
    )
    await db_session.commit()
    (tmp_path / active_artifact.storage_key).write_text("live\n", encoding="utf-8")
    (tmp_path / expired_artifact.storage_key).write_text("old\n", encoding="utf-8")

    service = PythonSessionsService(
        db_session,
        settings=settings.model_copy(update={"python_artifact_storage_dir": str(tmp_path)}),
        clock=lambda: now,
    )

    result = await service.persist_execution_response(
        conversation_id=conversation_id,
        user_id=owner_id,
        tool_execution_id=execution_id,
        profile_name=PythonExecutionProfile.basic,
        response=PythonExecutionResponse(
            result=_result(
                execution_id=UUID("00000000-0000-0000-0000-000000000111"),
                profile_name=PythonExecutionProfile.basic,
            ),
            snapshot_blob=b'{"version":1,"binding_names":[],"pickle_b64":"gAR9lC4="}',
        ),
    )
    await db_session.commit()

    assert result.status is PythonExecutionStatus.succeeded
    assert (tmp_path / active_artifact.storage_key).exists()
    assert not (tmp_path / expired_artifact.storage_key).exists()

    refreshed_active = await db_session.scalar(
        select(PythonArtifactRecord).where(PythonArtifactRecord.id == active_artifact.id)
    )
    refreshed_expired = await db_session.scalar(
        select(PythonArtifactRecord).where(PythonArtifactRecord.id == expired_artifact.id)
    )
    state_row = await db_session.scalar(
        select(PythonSessionState).where(PythonSessionState.conversation_id == conversation_id)
    )

    assert refreshed_active is not None
    assert refreshed_expired is not None
    assert state_row is not None
    assert refreshed_active.expires_at == now + timedelta(seconds=settings.python_session_ttl_seconds)
    assert refreshed_expired.expires_at < now
