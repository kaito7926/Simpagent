from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.accounts import AccountsRepository
from app.models.domain import Conversation
from app.schemas.auth import STANDARD_USER_SCOPES
from app.security.access_tokens import issue_access_token


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
        bundle = await accounts.create_user_with_local_credentials(email=email, password_hash="not-used-in-chat-tests")
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


async def _create_conversation(client, token: str, title: str = "Private thread") -> dict:
    response = await client.post("/api/conversations", headers=_auth(token), json={"title": title})
    assert response.status_code == 201
    return response.json()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_chat_routes_require_authenticated_principal(client) -> None:
    create = await client.post("/api/conversations", json={"title": "No principal"})
    list_response = await client.get("/api/conversations")
    retrieve = await client.get("/api/conversations/00000000-0000-0000-0000-000000000000")
    delete = await client.delete("/api/conversations/00000000-0000-0000-0000-000000000000")

    assert create.status_code == 401
    assert list_response.status_code == 401
    assert retrieve.status_code == 401
    assert delete.status_code == 401
    assert create.json()["error"]["code"] == "missing_principal"


@pytest.mark.asyncio
async def test_chat_read_and_write_scopes_are_required(client, db_session, settings) -> None:
    _, full_token = await _create_user_token(db_session, settings, email="full@example.test")
    conversation = await _create_conversation(client, full_token, "Scoped thread")

    _, read_only_token = await _create_user_token(db_session, settings, email="read-only@example.test", scopes=["chat:read"])
    _, write_only_token = await _create_user_token(db_session, settings, email="write-only@example.test", scopes=["chat:write"])

    create_without_write = await client.post(
        "/api/conversations",
        headers=_auth(read_only_token),
        json={"title": "Should fail"},
    )
    delete_without_write = await client.delete(f"/api/conversations/{conversation['id']}", headers=_auth(read_only_token))
    list_without_read = await client.get("/api/conversations", headers=_auth(write_only_token))
    retrieve_without_read = await client.get(f"/api/conversations/{conversation['id']}", headers=_auth(write_only_token))

    assert create_without_write.status_code == 403
    assert create_without_write.json()["error"]["code"] == "missing_scope"
    assert delete_without_write.status_code == 403
    assert delete_without_write.json()["error"]["code"] == "missing_scope"
    assert list_without_read.status_code == 403
    assert list_without_read.json()["error"]["code"] == "missing_scope"
    assert retrieve_without_read.status_code == 403
    assert retrieve_without_read.json()["error"]["code"] == "missing_scope"

    list_after_denials = await client.get("/api/conversations", headers=_auth(full_token))
    assert [item["id"] for item in list_after_denials.json()["items"]] == [conversation["id"]]


@pytest.mark.asyncio
async def test_second_user_cannot_infer_retrieve_delete_or_list_another_users_conversation(client, db_session, settings) -> None:
    owner_id, owner_token = await _create_user_token(db_session, settings, email="owner-bola@example.test")
    _, attacker_token = await _create_user_token(db_session, settings, email="attacker-bola@example.test")
    conversation = await _create_conversation(client, owner_token, "Owner secret title")

    attacker_list = await client.get("/api/conversations?limit=10", headers=_auth(attacker_token))
    attacker_retrieve = await client.get(f"/api/conversations/{conversation['id']}", headers=_auth(attacker_token))
    attacker_delete = await client.delete(f"/api/conversations/{conversation['id']}", headers=_auth(attacker_token))

    assert attacker_list.status_code == 200
    assert attacker_list.json()["items"] == []
    assert "Owner secret title" not in attacker_list.text

    assert attacker_retrieve.status_code == 404
    assert attacker_retrieve.json()["error"]["code"] == "conversation_not_found"
    assert "Owner secret title" not in attacker_retrieve.text

    assert attacker_delete.status_code == 404
    assert attacker_delete.json()["error"]["code"] == "conversation_not_found"
    assert "Owner secret title" not in attacker_delete.text

    owner_retrieve = await client.get(f"/api/conversations/{conversation['id']}", headers=_auth(owner_token))
    assert owner_retrieve.status_code == 200
    assert owner_retrieve.json()["title"] == "Owner secret title"

    row = await db_session.scalar(select(Conversation).where(Conversation.id == UUID(conversation["id"])))
    assert row is not None
    assert row.user_id == owner_id
    assert row.deleted_at is None


@pytest.mark.asyncio
async def test_inactive_and_stale_principals_fail_before_chat_logic(client, db_session, settings) -> None:
    inactive_user_id, inactive_token = await _create_user_token(db_session, settings, email="inactive-chat@example.test")
    stale_user_id, stale_token = await _create_user_token(db_session, settings, email="stale-chat@example.test")

    async with db_session.begin():
        accounts = AccountsRepository(db_session)
        await accounts.set_user_active(inactive_user_id, is_active=False)
        await accounts.replace_user_scopes(stale_user_id, ["chat:read"])

    inactive = await client.get("/api/conversations", headers=_auth(inactive_token))
    stale = await client.get("/api/conversations", headers=_auth(stale_token))

    assert inactive.status_code == 401
    assert inactive.json()["error"]["code"] == "inactive_principal"
    assert stale.status_code == 401
    assert stale.json()["error"]["code"] == "stale_token"
