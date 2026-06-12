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


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_owner_can_create_list_retrieve_and_soft_delete_conversation(client, db_session, settings) -> None:
    owner_id, token = await _create_user_token(db_session, settings, email="owner@example.test")
    other_id, other_token = await _create_user_token(db_session, settings, email="other@example.test")

    first = await client.post("/api/conversations", headers=_auth(token), json={"title": "First private thread"})
    assert first.status_code == 201
    first_body = first.json()
    assert first_body["title"] == "First private thread"
    assert first_body["owner_id"] == str(owner_id)
    assert first_body["messages"] == []

    second = await client.post("/api/conversations", headers=_auth(token), json={"title": "Second private thread"})
    assert second.status_code == 201
    second_body = second.json()

    other = await client.post("/api/conversations", headers=_auth(other_token), json={"title": "Other user thread"})
    assert other.status_code == 201
    assert other.json()["owner_id"] == str(other_id)

    first_page = await client.get("/api/conversations?limit=1", headers=_auth(token))
    assert first_page.status_code == 200
    first_page_body = first_page.json()
    assert [item["id"] for item in first_page_body["items"]] == [second_body["id"]]
    assert first_page_body["items"][0]["message_count"] == 0
    assert first_page_body["next_cursor"]

    second_page = await client.get(
        f"/api/conversations?limit=5&cursor={first_page_body['next_cursor']}",
        headers=_auth(token),
    )
    assert second_page.status_code == 200
    assert [item["id"] for item in second_page.json()["items"]] == [first_body["id"]]
    assert "Other user thread" not in str(first_page_body) + str(second_page.json())

    retrieved = await client.get(f"/api/conversations/{first_body['id']}", headers=_auth(token))
    assert retrieved.status_code == 200
    retrieved_body = retrieved.json()
    assert retrieved_body["id"] == first_body["id"]
    assert retrieved_body["owner_id"] == str(owner_id)
    assert retrieved_body["messages"] == []

    deleted = await client.delete(f"/api/conversations/{first_body['id']}", headers=_auth(token))
    assert deleted.status_code == 204

    hidden_retrieve = await client.get(f"/api/conversations/{first_body['id']}", headers=_auth(token))
    assert hidden_retrieve.status_code == 404
    assert hidden_retrieve.json()["error"]["code"] == "conversation_not_found"
    assert "First private thread" not in hidden_retrieve.text

    hidden_list = await client.get("/api/conversations?limit=10", headers=_auth(token))
    assert hidden_list.status_code == 200
    assert [item["id"] for item in hidden_list.json()["items"]] == [second_body["id"]]

    row = await db_session.scalar(select(Conversation).where(Conversation.id == UUID(first_body["id"])))
    assert row is not None
    assert row.user_id == owner_id
    assert row.deleted_at is not None


@pytest.mark.asyncio
async def test_create_rejects_missing_title_without_creating_row(client, db_session, settings) -> None:
    _, token = await _create_user_token(db_session, settings, email="creator@example.test")

    response = await client.post("/api/conversations", headers=_auth(token), json={"title": ""})

    assert response.status_code == 422
    count = await db_session.scalar(select(Conversation))
    assert count is None
