from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
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
async def test_conversation_detail_returns_raw_message_content_without_rendered_html(
    client,
    db_session,
    settings,
) -> None:
    owner_id, token = await _create_user_token(
        db_session,
        settings,
        email="rendering-contract@example.test",
    )
    adversarial_content = (
        '<script>alert("xss")</script>\n'
        '<img src=x onerror="alert(1)">\n'
        "[unsafe](javascript:alert(1))\n"
        "```python\nprint('inert')\n```"
    )

    async with db_session.begin():
        conversation = Conversation(user_id=owner_id, title="Rendering contract")
        db_session.add(conversation)
        await db_session.flush()
        db_session.add(
            Message(
                conversation_id=conversation.id,
                sequence_no=1,
                role="assistant",
                status="completed",
                content=adversarial_content,
                message_metadata={},
            )
        )

    response = await client.get(f"/api/conversations/{conversation.id}", headers=_auth(token))

    assert response.status_code == 200
    body = response.json()
    assert len(body["messages"]) == 1
    message = body["messages"][0]
    assert message["content"] == adversarial_content
    assert message["metadata"] == {}
    assert "rendered_html" not in message
    assert "sanitized_html" not in message
    assert "sanitizer_warnings" not in message
    assert "rendered_html" not in body
