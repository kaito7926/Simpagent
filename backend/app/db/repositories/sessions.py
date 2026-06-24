from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence import SecurityEvent
from app.models.session import RefreshToken, RefreshTokenFamily, SecurityReplayRecord


@dataclass(frozen=True)
class ReplayConsumeResult:
    accepted: bool
    record: SecurityReplayRecord | None
    event: SecurityEvent | None = None


class SessionsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_family(self, *, user_id: UUID, absolute_expires_at: datetime) -> RefreshTokenFamily:
        family = RefreshTokenFamily(user_id=user_id, absolute_expires_at=absolute_expires_at)
        self.session.add(family)
        await self.session.flush()
        return family

    async def create_token(self, *, family_id: UUID, jti: str, token_hash: bytes, expires_at: datetime, parent_token_id: UUID | None = None) -> RefreshToken:
        token = RefreshToken(
            family_id=family_id,
            jti=jti,
            token_hash=token_hash,
            expires_at=expires_at,
            parent_token_id=parent_token_id,
        )
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_token_by_hash_for_update(self, token_hash: bytes) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash).with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_family_for_update(self, family_id: UUID) -> RefreshTokenFamily | None:
        stmt = select(RefreshTokenFamily).where(RefreshTokenFamily.id == family_id).with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_family(self, family: RefreshTokenFamily, *, now: datetime, reason: str) -> None:
        family.revoked_at = now
        family.revoke_reason = reason
        await self.session.flush()

    async def mark_token_used(self, token: RefreshToken, *, now: datetime, replacement: RefreshToken) -> None:
        token.used_at = now
        token.replaced_by_id = replacement.id
        await self.session.flush()

    async def consume_security_artifact_once(
        self,
        *,
        artifact_type: str,
        jti: str,
        subject: str | None,
        audience: str,
        conversation_id: str | UUID | None,
        binding_key_thumbprint: str | None,
        expires_at: datetime,
        now: datetime,
        correlation_id: str | None,
        replay_event_type: str,
    ) -> ReplayConsumeResult:
        normalized_conversation_id = UUID(str(conversation_id)) if conversation_id else None
        stmt = (
            select(SecurityReplayRecord)
            .where(
                SecurityReplayRecord.artifact_type == artifact_type,
                SecurityReplayRecord.audience == audience,
                SecurityReplayRecord.jti == jti,
            )
            .with_for_update()
        )
        existing = await self.session.scalar(stmt)
        if existing is None:
            record = SecurityReplayRecord(
                artifact_type=artifact_type,
                jti=jti,
                subject=subject,
                audience=audience,
                conversation_id=normalized_conversation_id,
                binding_key_thumbprint=binding_key_thumbprint,
                first_correlation_id=correlation_id,
                consumed_at=now,
                expires_at=expires_at,
                event_metadata={
                    "artifact_type": artifact_type,
                    "jti": jti,
                    "subject": subject,
                    "audience": audience,
                    "conversation_id": str(normalized_conversation_id) if normalized_conversation_id else None,
                    "binding_key_thumbprint": binding_key_thumbprint,
                },
            )
            self.session.add(record)
            await self.session.flush()
            return ReplayConsumeResult(accepted=True, record=record)

        existing.replay_count += 1
        existing.replayed_at = now
        existing.last_replay_correlation_id = correlation_id
        event = await self.add_security_event(
            event_type=replay_event_type,
            severity="high",
            user_id=None,
            description=f"Replay detected for {artifact_type} security artifact.",
            correlation_id=correlation_id,
            metadata={
                "artifact_type": artifact_type,
                "jti": jti,
                "subject": subject,
                "audience": audience,
                "conversation_id": str(normalized_conversation_id) if normalized_conversation_id else None,
                "binding_key_thumbprint": binding_key_thumbprint,
                "first_correlation_id": existing.first_correlation_id,
                "replay_count": existing.replay_count,
            },
        )
        await self.session.flush()
        return ReplayConsumeResult(accepted=False, record=existing, event=event)

    async def add_security_event(self, *, event_type: str, severity: str, user_id: UUID | None, description: str, correlation_id: str | None, metadata: dict | None = None) -> SecurityEvent:
        event = SecurityEvent(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            description=description,
            correlation_id=correlation_id,
            event_metadata=metadata or {},
        )
        self.session.add(event)
        await self.session.flush()
        logging.getLogger("simpagent.security").info(
            "security_event_recorded",
            extra={
                "event": "security_event",
                "event_type": event_type,
                "severity": severity,
                "user_id": str(user_id) if user_id else None,
                "correlation_id": correlation_id,
                "description": description,
                "metadata": metadata or {},
            },
        )
        return event
