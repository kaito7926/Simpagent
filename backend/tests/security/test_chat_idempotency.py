from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas import ChatCompletionResult
from app.db.repositories.accounts import AccountsRepository
from app.models.domain import Conversation, Message
from app.schemas.auth import STANDARD_USER_SCOPES
from app.security.access_tokens import issue_access_token


class RecordingChatAdapter:
    def __init__(self) -> None:
        self.calls: list[list[Any]] = []

    async def complete(self, *, messages: list[Any]) -> ChatCompletionResult:
        self.calls.append(list(messages))
        return ChatCompletionResult(
            content=f"Deterministic assistant response {len(self.calls)}.",
            provider_request_id=f"req-{len(self.calls)}",
            prompt_tokens=5,
            completion_tokens=3,
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


async def _create_conversation(client, token: str, title: str = "Idempotent thread") -> dict[str, Any]:
    response = await client.post("/api/conversations", headers=_auth(token), json={"title": title})
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_duplicate_client_message_id_replays_turn_without_second_provider_call(
    app,
    client,
    db_session,
    settings,
) -> None:
    _, token = await _create_user_token(db_session, settings, email="dedupe@example.test")
    provider = RecordingChatAdapter()
    app.state.chat_adapter = provider
    conversation = await _create_conversation(client, token)
    payload = {"client_message_id": "duplicate-client-id", "content": "Only process this once."}

    first = await client.post(
        f"/api/conversations/{conversation['id']}/messages",
        headers=_auth(token),
        json=payload,
    )
    replay = await client.post(
        f"/api/conversations/{conversation['id']}/messages",
        headers=_auth(token),
        json=payload,
    )

    assert first.status_code == 200
    assert replay.status_code == 200
    assert replay.json()["messages"] == first.json()["messages"]
    assert len(provider.calls) == 1

    user_rows = await db_session.scalar(
        select(func.count(Message.id)).where(
            Message.conversation_id == UUID(conversation["id"]),
            Message.role == "user",
            Message.client_message_id == "duplicate-client-id",
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


@pytest.mark.asyncio
async def test_pending_assistant_turn_blocks_second_send_without_provider_call(
    app,
    client,
    db_session,
    settings,
) -> None:
    _, token = await _create_user_token(db_session, settings, email="pending@example.test")
    provider = RecordingChatAdapter()
    app.state.chat_adapter = provider
    conversation = await _create_conversation(client, token)

    async with db_session.begin():
        db_session.add_all(
            [
                Message(
                    conversation_id=UUID(conversation["id"]),
                    sequence_no=1,
                    client_message_id="already-pending",
                    role="user",
                    status="completed",
                    content="Existing turn",
                    message_metadata={},
                ),
                Message(
                    conversation_id=UUID(conversation["id"]),
                    sequence_no=2,
                    role="assistant",
                    status="pending",
                    content="",
                    message_metadata={},
                ),
            ]
        )

    response = await client.post(
        f"/api/conversations/{conversation['id']}/messages",
        headers=_auth(token),
        json={"client_message_id": "blocked-client-id", "content": "Do not start yet."},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "turn_in_progress"
    assert len(provider.calls) == 0


@pytest.mark.asyncio
async def test_denied_send_paths_do_not_call_provider(app, client, db_session, settings) -> None:
    _, owner_token = await _create_user_token(db_session, settings, email="deny-owner@example.test")
    _, attacker_token = await _create_user_token(db_session, settings, email="deny-attacker@example.test")
    _, read_only_token = await _create_user_token(
        db_session,
        settings,
        email="deny-readonly@example.test",
        scopes=["chat:read"],
    )
    stale_user_id, stale_token = await _create_user_token(
        db_session,
        settings,
        email="deny-stale@example.test",
    )
    provider = RecordingChatAdapter()
    app.state.chat_adapter = provider
    conversation = await _create_conversation(client, owner_token, "Owner private thread")

    async with db_session.begin():
        accounts = AccountsRepository(db_session)
        await accounts.replace_user_scopes(stale_user_id, ["chat:read"])

    payload = {"client_message_id": "denied-client-id", "content": "This must not reach the provider."}
    unauthenticated = await client.post(f"/api/conversations/{conversation['id']}/messages", json=payload)
    missing_scope = await client.post(
        f"/api/conversations/{conversation['id']}/messages",
        headers=_auth(read_only_token),
        json=payload,
    )
    stale = await client.post(
        f"/api/conversations/{conversation['id']}/messages",
        headers=_auth(stale_token),
        json=payload,
    )
    cross_owner = await client.post(
        f"/api/conversations/{conversation['id']}/messages",
        headers=_auth(attacker_token),
        json=payload,
    )

    deleted = await client.delete(f"/api/conversations/{conversation['id']}", headers=_auth(owner_token))
    assert deleted.status_code == 204
    soft_deleted = await client.post(
        f"/api/conversations/{conversation['id']}/messages",
        headers=_auth(owner_token),
        json={"client_message_id": "deleted-client-id", "content": "Deleted thread"},
    )

    assert unauthenticated.status_code == 401
    assert missing_scope.status_code == 403
    assert missing_scope.json()["error"]["code"] == "missing_scope"
    assert stale.status_code == 401
    assert stale.json()["error"]["code"] == "stale_token"
    assert cross_owner.status_code == 404
    assert cross_owner.json()["error"]["code"] == "conversation_not_found"
    assert soft_deleted.status_code == 404
    assert soft_deleted.json()["error"]["code"] == "conversation_not_found"
    assert len(provider.calls) == 0

    owner_conversation = await db_session.scalar(
        select(Conversation).where(Conversation.id == UUID(conversation["id"]))
    )
    assert owner_conversation is not None
    assert owner_conversation.deleted_at is not None
