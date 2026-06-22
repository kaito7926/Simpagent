from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.chat_adapter import ChatProviderError
from app.ai.schemas import ChatCompletionResult
from app.db.repositories.accounts import AccountsRepository
from app.models.domain import Message
from app.schemas.auth import STANDARD_USER_SCOPES
from app.security.access_tokens import issue_access_token


class ScriptedChatAdapter:
    def __init__(self, outcomes: list[ChatCompletionResult | ChatProviderError]) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[list[Any]] = []

    async def complete(self, *, messages: list[Any]) -> ChatCompletionResult:
        self.calls.append(list(messages))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, ChatProviderError):
            raise outcome
        return outcome


async def _create_user_token(
    db_session: AsyncSession,
    settings,
    *,
    email: str,
    scopes: list[str] | None = None,
) -> tuple[UUID, str]:
    selected_scopes = scopes or STANDARD_USER_SCOPES
    async with db_session.begin():
        accounts = AccountsRepository(db_session)
        bundle = await accounts.create_user_with_local_credentials(
            email=email,
            password_hash="not-used-in-chat-tests",
        )
        if selected_scopes != STANDARD_USER_SCOPES:
            await accounts.replace_user_scopes(bundle.user.id, selected_scopes)
    token = issue_access_token(
        user_id=bundle.user.id,
        role=bundle.user.role,
        scopes=selected_scopes,
        settings=settings,
        now=datetime.now(UTC),
    )
    return bundle.user.id, token


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_conversation(client, token: str) -> dict[str, Any]:
    response = await client.post("/api/conversations", headers=_auth(token), json={"title": "Failure thread"})
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider_error", "expected_status"),
    [
        (ChatProviderError("provider_timeout", retryable=True, provider_request_id="req-timeout"), 502),
        (ChatProviderError("provider_rate_limited", retryable=True, provider_request_id="req-rate"), 502),
        (ChatProviderError("provider_auth_error", retryable=False, provider_request_id="req-auth"), 502),
        (ChatProviderError("provider_status_error", retryable=True, provider_request_id="req-status"), 502),
        (ChatProviderError("provider_empty_response", retryable=True, provider_request_id="req-empty"), 502),
    ],
)
async def test_provider_failure_persists_failed_assistant_without_fabricated_content(
    app,
    client,
    db_session,
    settings,
    provider_error: ChatProviderError,
    expected_status: int,
) -> None:
    _, token = await _create_user_token(db_session, settings, email=f"{provider_error.code}@example.test")
    provider = ScriptedChatAdapter([provider_error])
    app.state.chat_adapter = provider
    conversation = await _create_conversation(client, token)

    response = await client.post(
        f"/api/conversations/{conversation['id']}/messages",
        headers={**_auth(token), "X-Correlation-Id": f"corr-{provider_error.code}"},
        json={"client_message_id": "failure-client-id", "content": "Trigger provider failure."},
    )

    assert response.status_code == expected_status
    error = response.json()["error"]
    assert error["code"] == "provider_failed"
    assert error["provider_error_code"] == provider_error.code
    assert error["retryable"] is provider_error.retryable
    assert error["correlation_id"] == f"corr-{provider_error.code}"
    assert len(provider.calls) == 1

    rows = list(
        (
            await db_session.scalars(
                select(Message)
                .where(Message.conversation_id == UUID(conversation["id"]))
                .order_by(Message.sequence_no.asc())
            )
        ).all()
    )
    assert [(row.role, row.status, row.sequence_no) for row in rows] == [
        ("user", "completed", 1),
        ("assistant", "failed", 2),
    ]
    assert rows[1].content == ""
    assert rows[1].message_metadata == {
        "error_code": provider_error.code,
        "provider_request_id": provider_error.provider_request_id,
        "retryable": provider_error.retryable,
        "correlation_id": f"corr-{provider_error.code}",
    }


@pytest.mark.asyncio
async def test_retry_reuses_failed_turn_and_original_user_message(app, client, db_session, settings) -> None:
    _, token = await _create_user_token(db_session, settings, email="retry@example.test")
    provider = ScriptedChatAdapter(
        [
            ChatProviderError("provider_timeout", retryable=True, provider_request_id="req-timeout"),
            ChatCompletionResult(
                content="Recovered assistant answer.",
                provider_request_id="req-retry-success",
                prompt_tokens=13,
                completion_tokens=6,
                finish_reason="stop",
            ),
        ]
    )
    app.state.chat_adapter = provider
    conversation = await _create_conversation(client, token)

    failed = await client.post(
        f"/api/conversations/{conversation['id']}/messages",
        headers={**_auth(token), "X-Correlation-Id": "corr-original"},
        json={"client_message_id": "retry-client-id", "content": "Please retry me later."},
    )
    assert failed.status_code == 502

    retried = await client.post(
        f"/api/conversations/{conversation['id']}/messages/retry-client-id/retry",
        headers={**_auth(token), "X-Correlation-Id": "corr-retry"},
    )

    assert retried.status_code == 200
    body = retried.json()
    assert len(provider.calls) == 2
    assert [(turn.role, turn.content) for turn in provider.calls[1]] == [
        ("user", "Please retry me later.")
    ]
    assert [message["role"] for message in body["messages"]] == ["user", "assistant"]
    assert [message["sequence_no"] for message in body["messages"]] == [1, 2]
    assert body["messages"][1]["status"] == "completed"
    assert body["messages"][1]["content"] == "Recovered assistant answer."

    user_rows = await db_session.scalar(
        select(func.count(Message.id)).where(
            Message.conversation_id == UUID(conversation["id"]),
            Message.role == "user",
            Message.client_message_id == "retry-client-id",
        )
    )
    assistant_rows = await db_session.scalar(
        select(func.count(Message.id)).where(
            Message.conversation_id == UUID(conversation["id"]),
            Message.role == "assistant",
        )
    )
    assert user_rows == 1
    assert assistant_rows == 1
