from __future__ import annotations

from sqlalchemy import select

from app.models.domain import Message, ToolExecution
from tests.integration.search._helpers import (
    RecordingSearchWorker,
    create_conversation,
    create_user,
    grounded_result,
    issue_token,
    provider_failed_result,
)


async def test_grounded_turn_persists_allowlisted_metadata_and_lifecycle(client, app, db_session, settings) -> None:
    user = await create_user(
        db_session,
        email="search-persistence@example.test",
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
            "X-Correlation-Id": "corr-persistence",
        },
        json={"mode": "google_search", "prompt": "Tin mới nhất là gì?"},
    )

    assert response.status_code == 200

    await db_session.rollback()
    assistant = (
        await db_session.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id, Message.role == "assistant")
        )
    ).scalar_one()
    search = assistant.message_metadata["search"]
    assert search["web_search_queries"] == ["tu khoa goc"]
    assert [event["event"] for event in search["lifecycle"]] == ["requested", "started", "succeeded"]
    assert "rendered_content" not in search
    assert "sdk_blob" not in search


async def test_firecrawl_turn_persists_provider_and_retention_allowlist(client, app, db_session, settings) -> None:
    user = await create_user(
        db_session,
        email="firecrawl-persistence@example.test",
        scopes=["chat:read", "chat:write", "tool:websearch"],
    )
    conversation = await create_conversation(db_session, user_id=user.id)
    await db_session.commit()

    app.state.search_provider = "firecrawl"
    app.state.search_status = "ready"
    app.state.search_ready = True
    app.state.search_worker = RecordingSearchWorker(
        grounded_result().model_copy(
            update={
                "provider": "firecrawl",
                "google_grounded": False,
                "web_search_queries": ["firecrawl query"],
            }
        )
    )

    token = issue_token(
        user=user,
        scopes=["chat:read", "chat:write", "tool:websearch"],
        settings=settings,
    )
    response = await client.post(
        f"/api/conversations/{conversation.id}/turns",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Correlation-Id": "corr-firecrawl-persistence",
        },
        json={"mode": "google_search", "prompt": "Firecrawl persistence"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"]["search"]["provider"] == "firecrawl"
    assert payload["assistant_message"]["search"]["google_grounded"] is False

    await db_session.rollback()
    assistant = (
        await db_session.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id, Message.role == "assistant")
        )
    ).scalar_one()
    search = assistant.message_metadata["search"]
    assert search["provider"] == "firecrawl"
    assert search["web_search_queries"] == ["firecrawl query"]
    assert [event["event"] for event in search["lifecycle"]] == ["requested", "started", "succeeded"]
    assert "click_tracking_id" not in str(search)
    assert "redirect_url" not in str(search)
    assert "utm_source" not in str(search)


async def test_retry_reuses_same_assistant_message_and_adds_a_second_tool_execution(client, app, db_session, settings) -> None:
    user = await create_user(
        db_session,
        email="search-retry@example.test",
        scopes=["chat:read", "chat:write", "tool:websearch"],
    )
    conversation = await create_conversation(db_session, user_id=user.id)
    await db_session.commit()

    app.state.search_ready = True
    app.state.search_worker = RecordingSearchWorker(provider_failed_result())

    token = issue_token(
        user=user,
        scopes=["chat:read", "chat:write", "tool:websearch"],
        settings=settings,
    )
    first_response = await client.post(
        f"/api/conversations/{conversation.id}/turns",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Correlation-Id": "corr-retry-1",
        },
        json={"mode": "google_search", "prompt": "Thử lại tìm kiếm"},
    )

    assert first_response.status_code == 200
    first_payload = first_response.json()
    assistant_id = first_payload["assistant_message"]["id"]

    app.state.search_worker = RecordingSearchWorker(grounded_result())
    retry_response = await client.post(
        f"/api/conversations/{conversation.id}/turns",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Correlation-Id": "corr-retry-2",
        },
        json={
            "mode": "google_search",
            "prompt": "Thử lại tìm kiếm",
            "retry_of_message_id": assistant_id,
        },
    )

    assert retry_response.status_code == 200
    retry_payload = retry_response.json()
    assert retry_payload["assistant_message"]["id"] == assistant_id
    assert retry_payload["assistant_message"]["search"]["state"] == "grounded"

    await db_session.rollback()
    messages = (
        await db_session.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.sequence_no.asc())
        )
    ).scalars().all()
    assert [message.role for message in messages] == ["user", "assistant"]
    assert messages[1].message_metadata["search"]["retry_of_message_id"] == assistant_id
    assert [event["event"] for event in messages[1].message_metadata["search"]["lifecycle"]] == [
        "requested",
        "started",
        "failed",
        "requested",
        "started",
        "succeeded",
    ]

    executions = (
        await db_session.execute(
            select(ToolExecution)
            .where(ToolExecution.conversation_id == conversation.id)
            .order_by(ToolExecution.created_at.asc())
        )
    ).scalars().all()
    assert len(executions) == 2
    assert [execution.status for execution in executions] == ["failed", "succeeded"]
