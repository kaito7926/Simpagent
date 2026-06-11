from __future__ import annotations

from sqlalchemy import select

from app.models.domain import Message
from app.schemas.search import SearchWorkerResult
from tests.integration.search._helpers import RecordingSearchWorker, create_conversation, create_user, issue_token


async def test_missing_grounding_is_not_treated_as_grounded(client, app, db_session, settings) -> None:
    user = await create_user(
        db_session,
        email="missing-grounding@example.test",
        scopes=["chat:read", "chat:write", "tool:websearch"],
    )
    conversation = await create_conversation(db_session, user_id=user.id)
    await db_session.commit()

    app.state.search_ready = True
    app.state.search_worker = RecordingSearchWorker(
        SearchWorkerResult(
            state="grounded",
            answer_markdown="Câu trả lời không có grounding hợp lệ.",
            google_grounded=True,
            tool_executed=True,
            sources=[],
            citations=[],
            output_summary="grounded_without_evidence",
        )
    )

    token = issue_token(
        user=user,
        scopes=["chat:read", "chat:write", "tool:websearch"],
        settings=settings,
    )
    response = await client.post(
        f"/api/conversations/{conversation.id}/turns",
        headers={"Authorization": f"Bearer {token}"},
        json={"mode": "google_search", "prompt": "Nguồn ở đâu?"},
    )

    assert response.status_code == 200
    payload = response.json()
    search = payload["assistant_message"]["search"]
    assert search["state"] == "missing_grounding"
    assert search["google_grounded"] is False
    assert search["citations"] == []
    assert search["sources"] == []
    assert search.get("suggestions") is None

    await db_session.rollback()
    assistant = (
        await db_session.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id, Message.role == "assistant")
        )
    ).scalar_one()
    assert assistant.message_metadata["search"]["state"] == "missing_grounding"
    assert assistant.message_metadata["search"]["google_grounded"] is False
