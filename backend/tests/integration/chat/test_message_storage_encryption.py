from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import text

from app.ai.schemas import ChatCompletionResult
from app.db.repositories.accounts import AccountsRepository
from app.schemas.auth import STANDARD_USER_SCOPES
from app.security.access_tokens import issue_access_token


class StaticChatAdapter:
    async def complete(self, *, messages):
        return ChatCompletionResult(
            content="Assistant ciphertext should decrypt before response serialization.",
            provider_request_id="req-storage-encryption",
            prompt_tokens=9,
            completion_tokens=6,
            finish_reason="stop",
        )


async def _create_user_token(db_session, settings, *, email: str) -> tuple[UUID, str]:
    async with db_session.begin():
        accounts = AccountsRepository(db_session)
        bundle = await accounts.create_user_with_local_credentials(
            email=email,
            password_hash="not-used-in-storage-test",
        )
    token = issue_access_token(
        user_id=bundle.user.id,
        role=bundle.user.role,
        scopes=STANDARD_USER_SCOPES,
        settings=settings,
        now=datetime.now(UTC),
    )
    return bundle.user.id, token


@pytest.mark.asyncio
async def test_messages_are_stored_encrypted_at_rest_but_return_plaintext_via_api(
    app,
    client,
    db_session,
    settings,
) -> None:
    _, token = await _create_user_token(db_session, settings, email="encrypted-rest@example.test")
    app.state.chat_adapter = StaticChatAdapter()

    response = await client.post(
        "/api/conversations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "initial_message": {
                "client_message_id": "encrypted-rest-client-id",
                "content": "Store this securely at rest, but keep the reply readable.",
            }
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["messages"][0]["content"] == "Store this securely at rest, but keep the reply readable."
    assert payload["messages"][1]["content"] == "Assistant ciphertext should decrypt before response serialization."

    stored_rows = (
        await db_session.execute(
            text(
                "SELECT content FROM messages WHERE conversation_id = :conversation_id ORDER BY sequence_no ASC"
            ),
            {"conversation_id": UUID(payload["id"])},
        )
    ).scalars().all()

    assert len(stored_rows) == 2
    assert all(isinstance(row, str) and row.startswith("enc-v1:") for row in stored_rows)
    assert "Store this securely at rest" not in stored_rows[0]
    assert "Assistant ciphertext should decrypt before response serialization." not in stored_rows[1]
