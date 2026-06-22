from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.python_state import PythonArtifactRecord, PythonSessionState
from app.python_contract import PythonArtifactType, PythonExecutionProfile, PYTHON_STATE_SCHEMA_VERSION


class PythonStateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_session_state_for_update(self, *, conversation_id: UUID, user_id: UUID) -> PythonSessionState | None:
        stmt = (
            select(PythonSessionState)
            .where(
                PythonSessionState.conversation_id == conversation_id,
                PythonSessionState.user_id == user_id,
            )
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_session_state(self, *, conversation_id: UUID, user_id: UUID, now: datetime) -> PythonSessionState | None:
        stmt = select(PythonSessionState).where(
            PythonSessionState.conversation_id == conversation_id,
            PythonSessionState.user_id == user_id,
            PythonSessionState.expires_at > now,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_session_state(
        self,
        *,
        conversation_id: UUID,
        user_id: UUID,
        tool_execution_id: UUID | None,
        snapshot_blob: bytes,
        expires_at: datetime,
        profile_name: PythonExecutionProfile = PythonExecutionProfile.basic,
        state_schema_version: int = PYTHON_STATE_SCHEMA_VERSION,
    ) -> PythonSessionState:
        state = await self.get_session_state_for_update(conversation_id=conversation_id, user_id=user_id)
        if state is None:
            state = PythonSessionState(
                conversation_id=conversation_id,
                user_id=user_id,
                last_tool_execution_id=tool_execution_id,
                profile_name=profile_name.value,
                snapshot_blob=snapshot_blob,
                snapshot_size_bytes=len(snapshot_blob),
                state_schema_version=state_schema_version,
                expires_at=expires_at,
            )
            self.session.add(state)
        else:
            state.last_tool_execution_id = tool_execution_id
            state.profile_name = profile_name.value
            state.snapshot_blob = snapshot_blob
            state.snapshot_size_bytes = len(snapshot_blob)
            state.state_schema_version = state_schema_version
            state.expires_at = expires_at
        await self.session.flush()
        return state

    async def clear_session_state(self, *, conversation_id: UUID, user_id: UUID) -> None:
        await self.session.execute(
            delete(PythonSessionState).where(
                PythonSessionState.conversation_id == conversation_id,
                PythonSessionState.user_id == user_id,
            )
        )

    async def create_artifact(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        tool_execution_id: UUID,
        artifact_type: PythonArtifactType,
        name: str,
        storage_key: str,
        size_bytes: int,
        sha256: str,
        expires_at: datetime,
    ) -> PythonArtifactRecord:
        artifact = PythonArtifactRecord(
            user_id=user_id,
            conversation_id=conversation_id,
            tool_execution_id=tool_execution_id,
            artifact_type=artifact_type.value,
            name=name,
            storage_key=storage_key,
            size_bytes=size_bytes,
            sha256=sha256,
            expires_at=expires_at,
        )
        self.session.add(artifact)
        await self.session.flush()
        return artifact

    async def list_artifacts_for_execution(self, *, tool_execution_id: UUID, user_id: UUID) -> list[PythonArtifactRecord]:
        stmt = (
            select(PythonArtifactRecord)
            .where(
                PythonArtifactRecord.tool_execution_id == tool_execution_id,
                PythonArtifactRecord.user_id == user_id,
            )
            .order_by(PythonArtifactRecord.created_at.asc(), PythonArtifactRecord.id.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def extend_active_artifact_expiry(
        self,
        *,
        conversation_id: UUID,
        user_id: UUID,
        now: datetime,
        expires_at: datetime,
    ) -> int:
        result = await self.session.execute(
            update(PythonArtifactRecord)
            .where(
                PythonArtifactRecord.conversation_id == conversation_id,
                PythonArtifactRecord.user_id == user_id,
                PythonArtifactRecord.expires_at > now,
            )
            .values(expires_at=expires_at)
        )
        await self.session.flush()
        return result.rowcount or 0

    async def list_expired_artifacts(self, *, now: datetime) -> list[PythonArtifactRecord]:
        stmt = (
            select(PythonArtifactRecord)
            .where(PythonArtifactRecord.expires_at <= now)
            .order_by(PythonArtifactRecord.created_at.asc(), PythonArtifactRecord.id.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_expired_session_states(self, *, now: datetime) -> int:
        result = await self.session.execute(delete(PythonSessionState).where(PythonSessionState.expires_at <= now))
        await self.session.flush()
        return result.rowcount or 0

    async def get_artifact_for_owner(
        self,
        *,
        artifact_id: UUID,
        user_id: UUID,
        now: datetime | None = None,
    ) -> PythonArtifactRecord | None:
        conditions = [
            PythonArtifactRecord.id == artifact_id,
            PythonArtifactRecord.user_id == user_id,
        ]
        if now is not None:
            conditions.append(PythonArtifactRecord.expires_at > now)
        stmt = select(PythonArtifactRecord).where(*conditions)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def purge_expired_records(self, *, now: datetime) -> dict[str, int]:
        session_states = await self.session.execute(delete(PythonSessionState).where(PythonSessionState.expires_at <= now))
        artifacts = await self.session.execute(delete(PythonArtifactRecord).where(PythonArtifactRecord.expires_at <= now))
        return {
            "session_states": session_states.rowcount or 0,
            "artifacts": artifacts.rowcount or 0,
        }
