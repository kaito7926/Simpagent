from __future__ import annotations

from sqlalchemy import select
from uuid import UUID

from app.models.domain import Message, ToolExecution
from tests.integration.search._helpers import RecordingSearchWorker, create_conversation, create_user, grounded_result, issue_token


async def test_turn_route_rejects_unsupported_modes(client, app, db_session, settings) -> None:
    user = await create_user(
        db_session,
        email="invalid-mode@example.test",
        scopes=["chat:read", "chat:write", "tool:websearch"],
    )
    conversation = await create_conversation(db_session, user_id=user.id)
    await db_session.commit()

    app.state.search_ready = True
    app.state.search_worker = RecordingSearchWorker(grounded_result())

    token = issue_token(
        user=user,
        scopes=["chat:read", "chat:write", "tool:websearch"],
        settings=settings,
    )
    response = await client.post(
        f"/api/conversations/{conversation.id}/turns",
        headers={"Authorization": f"Bearer {token}"},
        json={"mode": "python", "prompt": "invalid"},
    )

    assert response.status_code == 422


async def test_grounded_search_turn_persists_messages_and_tool_execution(client, app, db_session, settings) -> None:
    user = await create_user(
        db_session,
        email="grounded-search@example.test",
        scopes=["chat:read", "chat:write", "tool:websearch"],
    )
    conversation = await create_conversation(db_session, user_id=user.id)
    await db_session.commit()

    app.state.search_ready = True
    app.state.search_worker = RecordingSearchWorker(grounded_result())

    token = issue_token(
        user=user,
        scopes=["chat:read", "chat:write", "tool:websearch"],
        settings=settings,
    )
    response = await client.post(
        f"/api/conversations/{conversation.id}/turns",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Correlation-Id": "corr-grounded-turn",
        },
        json={"mode": "google_search", "prompt": "Tình hình thời tiết hôm nay thế nào?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"]["search"]["state"] == "grounded"
    assert payload["assistant_message"]["search"]["google_grounded"] is True
    assert payload["tool_execution"]["status"] == "succeeded"

    await db_session.rollback()
    messages = (
        await db_session.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.sequence_no.asc())
        )
    ).scalars().all()
    assert [message.role for message in messages] == ["user", "assistant"]
    assert messages[0].sequence_no == 1
    assert messages[1].sequence_no == 2
    assert messages[1].message_metadata["search"]["state"] == "grounded"
    assert messages[1].message_metadata["search"]["correlation_id"] == "corr-grounded-turn"

    execution = (
        await db_session.execute(
            select(ToolExecution).where(ToolExecution.conversation_id == conversation.id)
        )
    ).scalar_one()
    assert execution.status == "succeeded"
    assert execution.correlation_id == "corr-grounded-turn"


async def test_turn_route_never_mutates_another_users_conversation(client, app, db_session, settings) -> None:
    owner = await create_user(
        db_session,
        email="owner-search@example.test",
        scopes=["chat:read", "chat:write", "tool:websearch"],
    )
    intruder = await create_user(
        db_session,
        email="intruder-search@example.test",
        scopes=["chat:read", "chat:write", "tool:websearch"],
    )
    conversation = await create_conversation(db_session, user_id=owner.id)
    await db_session.commit()

    app.state.search_ready = True
    app.state.search_worker = RecordingSearchWorker(grounded_result())

    token = issue_token(
        user=intruder,
        scopes=["chat:read", "chat:write", "tool:websearch"],
        settings=settings,
    )
    response = await client.post(
        f"/api/conversations/{conversation.id}/turns",
        headers={"Authorization": f"Bearer {token}"},
        json={"mode": "google_search", "prompt": "Không được phép"},
    )

    assert response.status_code == 404

    await db_session.rollback()
    messages = (
        await db_session.execute(
            select(Message).where(Message.conversation_id == conversation.id)
        )
    ).scalars().all()
    assert messages == []


async def test_turn_route_creates_missing_owned_conversation_on_first_turn(client, app, db_session, settings) -> None:
    user = await create_user(
        db_session,
        email="implicit-conversation@example.test",
        scopes=["chat:read", "chat:write", "tool:websearch"],
    )
    await db_session.commit()

    app.state.search_ready = True
    app.state.search_worker = RecordingSearchWorker(grounded_result())

    token = issue_token(
        user=user,
        scopes=["chat:read", "chat:write", "tool:websearch"],
        settings=settings,
    )
    conversation_id = UUID("11111111-1111-1111-1111-111111111111")
    response = await client.post(
        f"/api/conversations/{conversation_id}/turns",
        headers={"Authorization": f"Bearer {token}"},
        json={"mode": "google_search", "prompt": "Táº¡o há»™i thoáº¡i tá»« lÆ°á»£t Ä‘áº§u"},
    )

    assert response.status_code == 200

    await db_session.rollback()
    messages = (
        await db_session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.sequence_no.asc())
        )
    ).scalars().all()
    assert [message.role for message in messages] == ["user", "assistant"]
