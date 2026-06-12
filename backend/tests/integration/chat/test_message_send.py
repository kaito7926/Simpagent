from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas import ChatCompletionResult
from app.db.repositories.accounts import AccountsRepository
from app.models.domain import Message
from app.schemas.auth import STANDARD_USER_SCOPES
from app.security.access_tokens import issue_access_token


class RecordingChatAdapter:
    def __init__(self) -> None:
        self.calls: list[list[Any]] = []

    async def complete(self, *, messages: list[Any]) -> ChatCompletionResult:
        self.calls.append(list(messages))
        return ChatCompletionResult(
            content="Assistant response from the deterministic fake provider.",
            provider_request_id=f"req-{len(self.calls)}",
            prompt_tokens=11,
            completion_tokens=7,
            finish_reason="stop",
        )


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


@pytest.mark.asyncio
async def test_initial_message_creates_conversation_and_completed_assistant_turn(
    app,
    client,
    db_session,
    settings,
) -> None:
    owner_id, token = await _create_user_token(db_session, settings, email="first-send@example.test")
    provider = RecordingChatAdapter()
    app.state.chat_adapter = provider

    response = await client.post(
        "/api/conversations",
        headers=_auth(token),
        json={
            "initial_message": {
                "client_message_id": "first-client-message",
                "content": "Explain why idempotency matters for secure chat retries.",
            }
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["owner_id"] == str(owner_id)
    assert body["title"].startswith("Explain why idempotency matters")
    assert len(body["title"]) <= 80
    assert [message["role"] for message in body["messages"]] == ["user", "assistant"]
    assert [message["sequence_no"] for message in body["messages"]] == [1, 2]
    assert [message["status"] for message in body["messages"]] == ["completed", "completed"]
    assert body["messages"][0]["client_message_id"] == "first-client-message"
    assert body["messages"][1]["content"] == "Assistant response from the deterministic fake provider."
    assert body["messages"][1]["metadata"] == {
        "provider_request_id": "req-1",
        "prompt_tokens": 11,
        "completion_tokens": 7,
        "finish_reason": "stop",
    }
    assert len(provider.calls) == 1
    assert [(turn.role, turn.content) for turn in provider.calls[0]] == [
        ("user", "Explain why idempotency matters for secure chat retries.")
    ]

    message_count = await db_session.scalar(
        select(func.count(Message.id)).where(Message.conversation_id == UUID(body["id"]))
    )
    assert message_count == 2


@pytest.mark.asyncio
async def test_send_message_to_existing_conversation_returns_non_streaming_ordered_history(
    app,
    client,
    db_session,
    settings,
) -> None:
    _, token = await _create_user_token(db_session, settings, email="active-send@example.test")
    provider = RecordingChatAdapter()
    app.state.chat_adapter = provider

    created = await client.post("/api/conversations", headers=_auth(token), json={"title": "Existing thread"})
    assert created.status_code == 201
    conversation_id = created.json()["id"]

    sent = await client.post(
        f"/api/conversations/{conversation_id}/messages",
        headers=_auth(token),
        json={"client_message_id": "active-client-message", "content": "Give me a concise answer."},
    )

    assert sent.status_code == 200
    sent_body = sent.json()
    assert sent_body["id"] == conversation_id
    assert [message["sequence_no"] for message in sent_body["messages"]] == [1, 2]
    assert sent_body["messages"][0]["content"] == "Give me a concise answer."
    assert sent_body["messages"][1]["status"] == "completed"
    assert len(provider.calls) == 1

    reloaded = await client.get(f"/api/conversations/{conversation_id}", headers=_auth(token))
    assert reloaded.status_code == 200
    assert reloaded.json()["messages"] == sent_body["messages"]
