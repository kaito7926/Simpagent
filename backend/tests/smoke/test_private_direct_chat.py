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
from app.security.refresh_tokens import CSRF_COOKIE_NAME, REFRESH_COOKIE_NAME


ORIGIN = "http://localhost:3000"


class SmokeChatAdapter:
    def __init__(self) -> None:
        self.calls: list[list[tuple[str, str]]] = []
        self.failed_once = False

    async def complete(self, *, messages: list[Any]) -> ChatCompletionResult:
        self.calls.append([(turn.role, turn.content) for turn in messages])
        latest = messages[-1].content
        if "force provider failure" in latest and not self.failed_once:
            self.failed_once = True
            raise ChatProviderError(
                "provider_timeout",
                retryable=True,
                provider_request_id="req-smoke-failure",
            )
        if "unsafe markdown" in latest:
            content = "\n".join(
                [
                    '<img src=x onerror="alert(1)">',
                    "[unsafe](javascript:alert(1)) [ok](https://example.test)",
                    "| Control | Status |",
                    "| --- | --- |",
                    "| HTML | inert |",
                    "```python",
                    "print('not executed')",
                    "```",
                ]
            )
        elif "force provider failure" in latest:
            content = "Recovered smoke answer."
        else:
            content = f"Smoke answer {len(self.calls)}."
        return ChatCompletionResult(
            content=content,
            provider_request_id=f"req-smoke-{len(self.calls)}",
            prompt_tokens=7,
            completion_tokens=4,
            finish_reason="stop",
        )


async def _register_and_login(client, *, email: str, password: str) -> tuple[str, str, str]:
    registered = await client.post(
        "/api/auth/register",
        headers={"Origin": ORIGIN},
        json={"email": email, "password": password},
    )
    assert registered.status_code == 202

    login = await client.post(
        "/api/auth/login",
        headers={"Origin": ORIGIN},
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    access_token = login.json()["access_token"]
    csrf_token = login.cookies.get(CSRF_COOKIE_NAME) or client.cookies.get(CSRF_COOKIE_NAME)
    refresh_token = login.cookies.get(REFRESH_COOKIE_NAME) or client.cookies.get(REFRESH_COOKIE_NAME)
    assert csrf_token
    assert refresh_token
    return access_token, csrf_token, refresh_token


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


async def _message_count(db_session: AsyncSession, *, conversation_id: str, role: str, client_message_id: str) -> int:
    count = await db_session.scalar(
        select(func.count(Message.id)).where(
            Message.conversation_id == UUID(conversation_id),
            Message.role == role,
            Message.client_message_id == client_message_id,
        )
    )
    return int(count or 0)


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_private_direct_chat_assembled_phase_2_gate(app, client, db_session, settings) -> None:
    provider = SmokeChatAdapter()
    app.state.chat_adapter = provider

    owner_token, csrf_token, refresh_token = await _register_and_login(
        client,
        email="phase2-owner@example.test",
        password="MatKhauBaoMatPhase2Owner123",
    )
    attacker_token, _, _ = await _register_and_login(
        client,
        email="phase2-attacker@example.test",
        password="MatKhauBaoMatPhase2Attacker123",
    )
    _, read_only_token = await _create_user_token(
        db_session,
        settings,
        email="phase2-readonly@example.test",
        scopes=["chat:read"],
    )
    stale_user_id, stale_token = await _create_user_token(
        db_session,
        settings,
        email="phase2-stale@example.test",
    )
    async with db_session.begin():
        accounts = AccountsRepository(db_session)
        await accounts.replace_user_scopes(stale_user_id, ["chat:read"])

    me = await client.get("/api/auth/me", headers=_auth(owner_token))
    assert me.status_code == 200
    assert me.json()["email"] == "phase2-owner@example.test"

    older = await client.post(
        "/api/conversations",
        headers=_auth(owner_token),
        json={"title": "Older smoke thread"},
    )
    assert older.status_code == 201

    created = await client.post(
        "/api/conversations",
        headers=_auth(owner_token),
        json={
            "initial_message": {
                "client_message_id": "smoke-initial",
                "content": "Start the assembled private direct chat smoke.",
            }
        },
    )
    assert created.status_code == 201
    conversation = created.json()
    conversation_id = conversation["id"]
    assert [message["role"] for message in conversation["messages"]] == ["user", "assistant"]
    assert [message["sequence_no"] for message in conversation["messages"]] == [1, 2]
    assert conversation["messages"][1]["status"] == "completed"
    assert conversation["messages"][1]["content"] == "Smoke answer 1."
    assert provider.calls == [[("user", "Start the assembled private direct chat smoke.")]]

    reloaded = await client.get(f"/api/conversations/{conversation_id}", headers=_auth(owner_token))
    assert reloaded.status_code == 200
    assert [message["sequence_no"] for message in reloaded.json()["messages"]] == [1, 2]

    listed = await client.get("/api/conversations?limit=2", headers=_auth(owner_token))
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [conversation_id, older.json()["id"]]

    duplicate_payload = {
        "client_message_id": "smoke-duplicate",
        "content": "Process this idempotent message once.",
    }
    first_send = await client.post(
        f"/api/conversations/{conversation_id}/messages",
        headers=_auth(owner_token),
        json=duplicate_payload,
    )
    duplicate_send = await client.post(
        f"/api/conversations/{conversation_id}/messages",
        headers=_auth(owner_token),
        json=duplicate_payload,
    )
    assert first_send.status_code == 200
    assert duplicate_send.status_code == 200
    assert duplicate_send.json()["messages"] == first_send.json()["messages"]
    assert len(provider.calls) == 2
    assert await _message_count(
        db_session,
        conversation_id=conversation_id,
        role="user",
        client_message_id="smoke-duplicate",
    ) == 1

    for denied in (
        await client.get(f"/api/conversations/{conversation_id}", headers=_auth(attacker_token)),
        await client.post(
            f"/api/conversations/{conversation_id}/messages",
            headers=_auth(attacker_token),
            json={"client_message_id": "attacker-send", "content": "Cross-user append"},
        ),
        await client.post(
            f"/api/conversations/{conversation_id}/messages/smoke-duplicate/retry",
            headers=_auth(attacker_token),
        ),
        await client.delete(f"/api/conversations/{conversation_id}", headers=_auth(attacker_token)),
        await client.post(f"/api/conversations/{conversation_id}/undo-delete", headers=_auth(attacker_token)),
    ):
        assert denied.status_code == 404
        assert denied.json()["error"]["code"] == "conversation_not_found"
        assert "Process this idempotent message" not in denied.text
    attacker_list = await client.get("/api/conversations?limit=10", headers=_auth(attacker_token))
    assert attacker_list.status_code == 200
    assert attacker_list.json()["items"] == []
    assert len(provider.calls) == 2

    missing_scope = await client.post(
        f"/api/conversations/{conversation_id}/messages",
        headers=_auth(read_only_token),
        json={"client_message_id": "missing-scope", "content": "Should not send"},
    )
    stale = await client.post(
        f"/api/conversations/{conversation_id}/messages",
        headers=_auth(stale_token),
        json={"client_message_id": "stale-scope", "content": "Should not send"},
    )
    assert missing_scope.status_code == 403
    assert missing_scope.json()["error"]["code"] == "missing_scope"
    assert stale.status_code == 401
    assert stale.json()["error"]["code"] == "stale_token"
    assert len(provider.calls) == 2

    failed = await client.post(
        f"/api/conversations/{conversation_id}/messages",
        headers={**_auth(owner_token), "X-Correlation-Id": "corr-smoke-failure"},
        json={"client_message_id": "smoke-failure", "content": "force provider failure once"},
    )
    assert failed.status_code == 502
    assert failed.json()["error"]["code"] == "provider_failed"
    failure_state = await client.get(f"/api/conversations/{conversation_id}", headers=_auth(owner_token))
    failed_row = failure_state.json()["messages"][-1]
    assert failed_row["role"] == "assistant"
    assert failed_row["status"] == "failed"
    assert failed_row["content"] == ""
    assert failed_row["metadata"]["correlation_id"] == "corr-smoke-failure"
    assert failed_row["metadata"]["retryable"] is True
    state_labels = await client.get("/api/conversations?limit=1", headers=_auth(owner_token))
    assert state_labels.json()["items"][0]["state_label"] == "Retry available"

    retried = await client.post(
        f"/api/conversations/{conversation_id}/messages/smoke-failure/retry",
        headers={**_auth(owner_token), "X-Correlation-Id": "corr-smoke-retry"},
    )
    assert retried.status_code == 200
    retried_messages = retried.json()["messages"]
    assert retried_messages[-1]["status"] == "completed"
    assert retried_messages[-1]["content"] == "Recovered smoke answer."
    assert await _message_count(
        db_session,
        conversation_id=conversation_id,
        role="user",
        client_message_id="smoke-failure",
    ) == 1

    unsafe = await client.post(
        f"/api/conversations/{conversation_id}/messages",
        headers=_auth(owner_token),
        json={"client_message_id": "smoke-unsafe", "content": "return unsafe markdown corpus"},
    )
    assert unsafe.status_code == 200
    unsafe_message = unsafe.json()["messages"][-1]
    assert unsafe_message["status"] == "completed"
    assert '<img src=x onerror="alert(1)">' in unsafe_message["content"]
    assert "[unsafe](javascript:alert(1))" in unsafe_message["content"]
    assert "rendered_html" not in unsafe_message
    assert "sanitizer_warnings" not in unsafe_message

    deleted = await client.delete(f"/api/conversations/{conversation_id}", headers=_auth(owner_token))
    assert deleted.status_code == 204
    hidden_list = await client.get("/api/conversations?limit=10", headers=_auth(owner_token))
    assert conversation_id not in [item["id"] for item in hidden_list.json()["items"]]
    attacker_undo_deleted = await client.post(
        f"/api/conversations/{conversation_id}/undo-delete",
        headers=_auth(attacker_token),
    )
    assert attacker_undo_deleted.status_code == 404
    restored = await client.post(f"/api/conversations/{conversation_id}/undo-delete", headers=_auth(owner_token))
    assert restored.status_code == 200
    assert restored.json()["id"] == conversation_id

    client.cookies.clear()
    client.cookies.set(REFRESH_COOKIE_NAME, refresh_token)
    client.cookies.set(CSRF_COOKIE_NAME, csrf_token)
    logout = await client.post(
        "/api/auth/logout",
        headers={"Origin": ORIGIN, "X-CSRF-Token": csrf_token},
    )
    assert logout.status_code == 204
    client.cookies.clear()
    client.cookies.set(REFRESH_COOKIE_NAME, refresh_token)
    client.cookies.set(CSRF_COOKIE_NAME, csrf_token)
    refresh_after_logout = await client.post(
        "/api/auth/refresh",
        headers={"Origin": ORIGIN, "X-CSRF-Token": csrf_token},
    )
    assert refresh_after_logout.status_code == 401
    assert refresh_after_logout.json()["error"]["code"] == "session_invalid"
