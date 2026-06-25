from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from sqlalchemy import select

from app.ai.search_worker.service import GoogleSearchWorkerService
from app.db.repositories.sessions import SessionsRepository
from app.models.evidence import SecurityEvent
from app.schemas.auth import STANDARD_USER_SCOPES
from app.schemas.search import SEARCH_UNAVAILABLE_COPY
from app.security.access_tokens import issue_access_token
from app.security.search_capability import (
    SEARCH_CAPABILITY_ALGORITHM,
    SEARCH_CAPABILITY_TYPE,
    SearchCapabilityError,
    validate_search_capability,
)
from tests.integration.search._worker_fakes import FakeRunner, make_search_settings, mint_capability_token, text_event


def test_search_capability_round_trips_with_expected_bindings(settings) -> None:
    search_settings = make_search_settings(settings)
    now = search_settings.now_utc()
    token, user_id, conversation_id = mint_capability_token(
        search_settings,
        correlation_id="corr-capability",
    )

    claims = validate_search_capability(
        token,
        settings=search_settings,
        now=now,
    )

    assert claims.sub == user_id
    assert claims.conversation_id == conversation_id
    assert claims.correlation_id == "corr-capability"
    assert claims.tool == "google_search"


def test_user_access_token_is_not_a_worker_capability(settings) -> None:
    now = settings.now_utc()
    token = issue_access_token(
        user_id=uuid4(),
        role="user",
        scopes=STANDARD_USER_SCOPES,
        settings=settings,
        now=now,
    )

    with pytest.raises(SearchCapabilityError):
        validate_search_capability(token, settings=settings, now=now)


def test_capability_token_fails_when_tool_binding_is_tampered(settings) -> None:
    search_settings = make_search_settings(settings)
    now = search_settings.now_utc()
    payload = {
        "iss": search_settings.jwt_issuer,
        "aud": search_settings.search_capability_audience,
        "sub": str(uuid4()),
        "tool": "python",
        "conversation_id": str(uuid4()),
        "correlation_id": "corr-capability",
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=search_settings.search_capability_ttl_seconds)).timestamp()),
        "jti": str(uuid4()),
    }
    token = jwt.encode(
        payload,
        search_settings.jwt_private_key_value,
        algorithm=SEARCH_CAPABILITY_ALGORITHM,
        headers={
            "typ": SEARCH_CAPABILITY_TYPE,
            "kid": search_settings.jwt_active_kid,
            "alg": SEARCH_CAPABILITY_ALGORITHM,
        },
    )

    with pytest.raises(SearchCapabilityError):
        validate_search_capability(token, settings=search_settings, now=now)


@pytest.mark.asyncio
async def test_search_capability_replay_is_rejected_by_persistent_consume_path(settings, db_session) -> None:
    search_settings = make_search_settings(settings)
    now = search_settings.now_utc()
    token, user_id, conversation_id = mint_capability_token(
        search_settings,
        correlation_id="corr-capability-replay",
    )
    claims = validate_search_capability(token, settings=search_settings, now=now)
    repository = SessionsRepository(db_session)

    first_use = await repository.consume_security_artifact_once(
        artifact_type="search_capability",
        jti=str(claims.jti),
        subject=str(user_id),
        audience=claims.aud,
        conversation_id=str(conversation_id),
        binding_key_thumbprint=None,
        expires_at=datetime.fromtimestamp(claims.exp, UTC),
        now=now,
        correlation_id=claims.correlation_id,
        replay_event_type="search_capability_replay",
    )
    second_use = await repository.consume_security_artifact_once(
        artifact_type="search_capability",
        jti=str(claims.jti),
        subject=str(user_id),
        audience=claims.aud,
        conversation_id=str(conversation_id),
        binding_key_thumbprint=None,
        expires_at=datetime.fromtimestamp(claims.exp, UTC),
        now=now,
        correlation_id=claims.correlation_id,
        replay_event_type="search_capability_replay",
    )

    assert first_use.accepted is True
    assert first_use.record is not None
    assert first_use.record.conversation_id == conversation_id
    assert second_use.accepted is False
    assert second_use.event is not None
    assert second_use.event.event_type == "search_capability_replay"

    event = await db_session.scalar(
        select(SecurityEvent).where(SecurityEvent.correlation_id == "corr-capability-replay")
    )
    assert event is not None
    assert event.event_metadata["artifact_type"] == "search_capability"
    assert event.event_metadata["jti"] == str(claims.jti)


@pytest.mark.asyncio
async def test_search_worker_rejects_replayed_capability_before_live_execution(
    settings,
    session_factory,
) -> None:
    search_settings = make_search_settings(settings)
    token, user_id, conversation_id = mint_capability_token(
        search_settings,
        correlation_id="corr-search-worker-replay",
    )
    runner = FakeRunner(
        events=[
            text_event(
                text='{"answer_markdown":"Kết quả kiểm thử [1].","query_used":"tin tức"}',
                grounding_metadata={
                    "grounding_chunks": [
                        {
                            "web": {
                                "title": "Nguồn kiểm thử",
                                "domain": "example.test",
                                "uri": "https://example.test/source",
                            }
                        }
                    ],
                    "grounding_supports": [
                        {
                            "grounding_chunk_indices": [0],
                            "segment": {"start_index": 17, "end_index": 20},
                        }
                    ],
                },
            )
        ]
    )
    service = GoogleSearchWorkerService(
        settings=search_settings,
        runner_factory=lambda agent: runner,
        session_factory=session_factory,
    )

    first = await service.run(
        user_id=str(user_id),
        conversation_id=str(conversation_id),
        prompt="tin tức",
        correlation_id="corr-search-worker-replay",
        capability_token=token,
    )
    second = await service.run(
        user_id=str(user_id),
        conversation_id=str(conversation_id),
        prompt="tin tức",
        correlation_id="corr-search-worker-replay",
        capability_token=token,
    )

    assert first.state in {"grounded", "missing_grounding"}
    assert second.state == "search_unavailable"
    assert second.answer_markdown == SEARCH_UNAVAILABLE_COPY
    assert runner.calls == 1
