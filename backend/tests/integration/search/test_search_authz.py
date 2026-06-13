from __future__ import annotations

from sqlalchemy import select

from app.models.domain import ToolExecution
from tests.integration.search._helpers import RecordingSearchWorker, create_conversation, create_user, grounded_result, issue_token


async def test_search_without_scope_returns_denied_and_skips_worker(client, app, db_session, settings) -> None:
    user = await create_user(
        db_session,
        email="denied-search@example.test",
        scopes=["chat:read", "chat:write"],
    )
    conversation = await create_conversation(db_session, user_id=user.id)
    await db_session.commit()

    app.state.search_ready = True
    worker = RecordingSearchWorker(grounded_result())
    app.state.search_worker = worker

    token = issue_token(user=user, scopes=["chat:read", "chat:write"], settings=settings)
    response = await client.post(
        f"/api/conversations/{conversation.id}/turns",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Correlation-Id": "corr-search-denied",
        },
        json={"mode": "google_search", "prompt": "Tin mới hôm nay là gì?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"]["search"]["state"] == "denied"
    assert payload["assistant_message"]["search"]["tool_executed"] is False
    assert worker.calls == 0

    await db_session.rollback()
    execution = (
        await db_session.execute(
            select(ToolExecution).where(ToolExecution.conversation_id == conversation.id)
        )
    ).scalar_one()
    assert execution.status == "denied"
    assert execution.correlation_id == "corr-search-denied"
