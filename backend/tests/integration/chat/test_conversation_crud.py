from __future__ import annotations

import base64
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.accounts import AccountsRepository
from app.models.domain import Conversation, Message
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


def _decode_cursor(cursor: str) -> dict[str, str]:
    padded = cursor + ("=" * (-len(cursor) % 4))
    return json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))


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
async def test_pagination_cursor_reveals_only_ordering_fields_and_list_stays_newest_first(
    client,
    db_session,
    settings,
) -> None:
    owner_id, token = await _create_user_token(db_session, settings, email="pagination@example.test")
    created = []
    for title in ("Older", "Middle", "Newest"):
        response = await client.post("/api/conversations", headers=_auth(token), json={"title": title})
        assert response.status_code == 201
        created.append(response.json())

    ordered_times = [
        datetime(2026, 6, 10, 8, 0, tzinfo=UTC),
        datetime(2026, 6, 11, 8, 0, tzinfo=UTC),
        datetime(2026, 6, 12, 8, 0, tzinfo=UTC),
    ]
    async with db_session.begin():
        for conversation, updated_at in zip(created, ordered_times, strict=True):
            await db_session.execute(
                update(Conversation)
                .where(Conversation.id == UUID(conversation["id"]), Conversation.user_id == owner_id)
                .values(updated_at=updated_at)
            )

    first_page = await client.get("/api/conversations?limit=2", headers=_auth(token))
    assert first_page.status_code == 200
    first_body = first_page.json()
    assert [item["title"] for item in first_body["items"]] == ["Newest", "Middle"]
    assert first_body["next_cursor"]
    assert _decode_cursor(first_body["next_cursor"]) == {
        "updated_at": ordered_times[1].isoformat(),
        "id": created[1]["id"],
    }

    second_page = await client.get(
        f"/api/conversations?limit=2&cursor={first_body['next_cursor']}",
        headers=_auth(token),
    )
    assert second_page.status_code == 200
    assert [item["title"] for item in second_page.json()["items"]] == ["Older"]

    async with db_session.begin():
        await db_session.execute(
            update(Conversation)
            .where(Conversation.id == UUID(created[0]["id"]), Conversation.user_id == owner_id)
            .values(updated_at=datetime(2026, 6, 12, 9, 0, tzinfo=UTC))
        )

    reordered = await client.get("/api/conversations?limit=3", headers=_auth(token))
    assert reordered.status_code == 200
    assert [item["title"] for item in reordered.json()["items"]] == ["Older", "Newest", "Middle"]


@pytest.mark.asyncio
async def test_list_exposes_only_pending_and_retry_state_labels(client, db_session, settings) -> None:
    owner_id, token = await _create_user_token(db_session, settings, email="labels@example.test")
    pending = await client.post("/api/conversations", headers=_auth(token), json={"title": "Pending"})
    failed = await client.post("/api/conversations", headers=_auth(token), json={"title": "Failed"})
    complete = await client.post("/api/conversations", headers=_auth(token), json={"title": "Complete"})
    assert pending.status_code == failed.status_code == complete.status_code == 201

    async with db_session.begin():
        db_session.add_all(
            [
                Message(
                    conversation_id=UUID(pending.json()["id"]),
                    sequence_no=1,
                    role="assistant",
                    status="pending",
                    content="",
                    message_metadata={},
                ),
                Message(
                    conversation_id=UUID(failed.json()["id"]),
                    sequence_no=1,
                    role="assistant",
                    status="failed",
                    content="",
                    message_metadata={"retryable": True},
                ),
                Message(
                    conversation_id=UUID(complete.json()["id"]),
                    sequence_no=1,
                    role="assistant",
                    status="completed",
                    content="Done",
                    message_metadata={},
                ),
            ]
        )

    response = await client.get("/api/conversations?limit=10", headers=_auth(token))
    assert response.status_code == 200
    labels = {item["title"]: item["state_label"] for item in response.json()["items"]}
    assert labels == {
        "Pending": "Pending reply",
        "Failed": "Retry available",
        "Complete": None,
    }
    assert all(item["owner_id"] == str(owner_id) for item in response.json()["items"])


@pytest.mark.asyncio
async def test_owner_can_undo_recent_soft_delete_but_not_after_window(client, db_session, settings) -> None:
    owner_id, token = await _create_user_token(db_session, settings, email="undo-owner@example.test")
    created = await client.post("/api/conversations", headers=_auth(token), json={"title": "Undo me"})
    assert created.status_code == 201
    conversation_id = UUID(created.json()["id"])

    deleted = await client.delete(f"/api/conversations/{conversation_id}", headers=_auth(token))
    assert deleted.status_code == 204
    deleted_row = await db_session.scalar(select(Conversation).where(Conversation.id == conversation_id))
    assert deleted_row is not None
    assert deleted_row.user_id == owner_id
    assert deleted_row.deleted_at is not None

    restored = await client.post(
        f"/api/conversations/{conversation_id}/undo-delete",
        headers=_auth(token),
    )
    assert restored.status_code == 200
    assert restored.json()["id"] == str(conversation_id)
    assert restored.json()["title"] == "Undo me"
    await db_session.refresh(deleted_row)
    assert deleted_row.deleted_at is None

    deleted_again = await client.delete(f"/api/conversations/{conversation_id}", headers=_auth(token))
    assert deleted_again.status_code == 204
    async with db_session.begin():
        await db_session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id, Conversation.user_id == owner_id)
            .values(deleted_at=datetime.now(UTC) - timedelta(seconds=7))
        )

    expired = await client.post(
        f"/api/conversations/{conversation_id}/undo-delete",
        headers=_auth(token),
    )
    assert expired.status_code == 404
    assert expired.json()["error"]["code"] == "conversation_not_found"


@pytest.mark.asyncio
async def test_delete_and_undo_require_write_scope_and_same_owner(client, db_session, settings) -> None:
    owner_id, owner_token = await _create_user_token(db_session, settings, email="undo-scope-owner@example.test")
    _, attacker_token = await _create_user_token(db_session, settings, email="undo-scope-attacker@example.test")
    _, read_only_token = await _create_user_token(
        db_session,
        settings,
        email="undo-scope-reader@example.test",
        scopes=["chat:read"],
    )
    created = await client.post("/api/conversations", headers=_auth(owner_token), json={"title": "Owner only"})
    assert created.status_code == 201
    conversation_id = created.json()["id"]

    denied_delete = await client.delete(
        f"/api/conversations/{conversation_id}",
        headers=_auth(read_only_token),
    )
    denied_undo = await client.post(
        f"/api/conversations/{conversation_id}/undo-delete",
        headers=_auth(read_only_token),
    )
    attacker_delete = await client.delete(
        f"/api/conversations/{conversation_id}",
        headers=_auth(attacker_token),
    )
    attacker_undo = await client.post(
        f"/api/conversations/{conversation_id}/undo-delete",
        headers=_auth(attacker_token),
    )

    assert denied_delete.status_code == 403
    assert denied_undo.status_code == 403
    assert denied_delete.json()["error"]["code"] == "missing_scope"
    assert denied_undo.json()["error"]["code"] == "missing_scope"
    assert attacker_delete.status_code == 404
    assert attacker_undo.status_code == 404
    assert attacker_delete.json()["error"]["code"] == "conversation_not_found"
    assert attacker_undo.json()["error"]["code"] == "conversation_not_found"

    row = await db_session.scalar(select(Conversation).where(Conversation.id == UUID(conversation_id)))
    assert row is not None
    assert row.user_id == owner_id
    assert row.deleted_at is None


@pytest.mark.asyncio
async def test_create_rejects_missing_title_without_creating_row(client, db_session, settings) -> None:
    _, token = await _create_user_token(db_session, settings, email="creator@example.test")

    response = await client.post("/api/conversations", headers=_auth(token), json={"title": ""})

    assert response.status_code == 422
    count = await db_session.scalar(select(Conversation))
    assert count is None
