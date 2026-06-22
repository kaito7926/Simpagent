from __future__ import annotations

import base64
import json
import pickle
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.python_state import PythonStateRepository
from app.models.python_state import PythonArtifactRecord
from app.python_contract import PythonExecutionProfile, PythonExecutionStatus
from app.schemas.python import PythonExecutionArtifact, PythonExecutionResult
from app.tools.python_client import PythonExecutionResponse


SAFE_BINDING_NAME_MAX = 64


@dataclass(frozen=True, slots=True)
class ActivePythonSession:
    snapshot_blob: bytes
    binding_names: tuple[str, ...]
    profile_name: PythonExecutionProfile


@dataclass(frozen=True, slots=True)
class ArtifactDownloadCandidate:
    record: PythonArtifactRecord
    path: Path
    expired: bool


class PythonSessionsService:
    def __init__(self, session: AsyncSession, *, settings, clock) -> None:
        self.session = session
        self.settings = settings
        self.clock = clock
        self.repository = PythonStateRepository(session)

    async def cleanup_expired_data(self) -> dict[str, int]:
        now = self.clock()
        artifact_root = self._artifact_storage_root()
        removed_payloads = 0

        for record in await self.repository.list_expired_artifacts(now=now):
            payload_path = artifact_root / record.storage_key
            if payload_path.exists():
                payload_path.unlink()
                removed_payloads += 1

        removed_sessions = await self.repository.delete_expired_session_states(now=now)
        return {
            "session_states": removed_sessions,
            "artifact_payloads": removed_payloads,
        }

    async def get_active_session(
        self,
        *,
        conversation_id: UUID,
        user_id: UUID,
    ) -> ActivePythonSession | None:
        await self.cleanup_expired_data()
        state = await self.repository.get_active_session_state(
            conversation_id=conversation_id,
            user_id=user_id,
            now=self.clock(),
        )
        if state is None:
            return None

        return ActivePythonSession(
            snapshot_blob=state.snapshot_blob,
            binding_names=_binding_names_from_snapshot(state.snapshot_blob),
            profile_name=PythonExecutionProfile(state.profile_name),
        )

    async def persist_execution_response(
        self,
        *,
        conversation_id: UUID,
        user_id: UUID,
        tool_execution_id: UUID,
        profile_name: PythonExecutionProfile,
        response: PythonExecutionResponse,
    ) -> PythonExecutionResult:
        await self.cleanup_expired_data()
        result = response.result
        if result.status not in {PythonExecutionStatus.succeeded, PythonExecutionStatus.limit_reached}:
            return result

        now = self.clock()
        expires_at = now + timedelta(seconds=self.settings.python_session_ttl_seconds)
        snapshot_blob = response.snapshot_blob or _empty_snapshot_blob()

        await self.repository.upsert_session_state(
            conversation_id=conversation_id,
            user_id=user_id,
            tool_execution_id=tool_execution_id,
            snapshot_blob=snapshot_blob,
            expires_at=expires_at,
            profile_name=profile_name,
        )
        await self.repository.extend_active_artifact_expiry(
            conversation_id=conversation_id,
            user_id=user_id,
            now=now,
            expires_at=expires_at,
        )

        stored_artifacts: list[PythonExecutionArtifact] = []
        for artifact in response.artifacts:
            storage_key = f"python-artifact-{uuid4().hex}.{artifact.artifact_type.value}"
            artifact_path = self._artifact_storage_root() / storage_key
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_bytes(artifact.content)

            record = await self.repository.create_artifact(
                user_id=user_id,
                conversation_id=conversation_id,
                tool_execution_id=tool_execution_id,
                artifact_type=artifact.artifact_type,
                name=artifact.name,
                storage_key=storage_key,
                size_bytes=artifact.size_bytes,
                sha256=artifact.sha256,
                expires_at=expires_at,
            )
            stored_artifacts.append(
                PythonExecutionArtifact(
                    artifact_id=record.id,
                    name=record.name,
                    artifact_type=artifact.artifact_type,
                    size_bytes=artifact.size_bytes,
                    download_path=f"/api/python/artifacts/{record.id}",
                )
            )

        return result.model_copy(update={"artifacts": stored_artifacts, "profile_name": profile_name})

    async def resolve_artifact_download(
        self,
        *,
        artifact_id: UUID,
        user_id: UUID,
    ) -> ArtifactDownloadCandidate | None:
        await self.cleanup_expired_data()
        record = await self.repository.get_artifact_for_owner(
            artifact_id=artifact_id,
            user_id=user_id,
        )
        if record is None:
            return None

        path = self._artifact_storage_root() / record.storage_key
        expired = record.expires_at <= self.clock()
        if expired and path.exists():
            path.unlink()
        return ArtifactDownloadCandidate(record=record, path=path, expired=expired)

    def _artifact_storage_root(self) -> Path:
        return Path(self.settings.python_artifact_storage_dir).resolve()


def _empty_snapshot_blob() -> bytes:
    payload = {
        "version": 1,
        "binding_names": [],
        "pickle_b64": base64.b64encode(pickle.dumps({}, protocol=pickle.HIGHEST_PROTOCOL)).decode("ascii"),
    }
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _binding_names_from_snapshot(snapshot_blob: bytes) -> tuple[str, ...]:
    try:
        payload = json.loads(snapshot_blob.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ()
    raw_names = payload.get("binding_names")
    if not isinstance(raw_names, list):
        return ()

    safe_names: list[str] = []
    for value in raw_names:
        if not isinstance(value, str):
            continue
        if len(value) > SAFE_BINDING_NAME_MAX or not value.isidentifier() or value.startswith("_"):
            continue
        if value not in safe_names:
            safe_names.append(value)
    return tuple(safe_names)
