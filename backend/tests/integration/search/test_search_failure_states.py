from __future__ import annotations

from sqlalchemy import select

from app.models.domain import Message
from tests.integration.search._helpers import (
    RecordingSearchWorker,
    create_conversation,
    create_user,
    grounded_result,
    issue_token,
    provider_failed_result,
    timeout_result,
)


async def test_failure_states_keep_distinct_lifecycle_and_retry_contract(client, app, db_session, settings) -> None:
    cases = [
        ("search_unavailable", False, RecordingSearchWorker(grounded_result()), "failed"),
        ("provider_failed", True, RecordingSearchWorker(provider_failed_result()), "failed"),
        ("timeout", True, RecordingSearchWorker(timeout_result()), "timed_out"),
    ]

    for index, (expected_state, search_ready, worker, final_event) in enumerate(cases, start=1):
        user = await create_user(
            db_session,
            email=f"failure-{index}@example.test",
            scopes=["chat:read", "chat:write", "tool:websearch"],
        )
        conversation = await create_conversation(db_session, user_id=user.id, title=expected_state)
        await db_session.commit()

        app.state.search_ready = search_ready
        app.state.search_worker = worker

        token = issue_token(
            user=user,
            scopes=["chat:read", "chat:write", "tool:websearch"],
            settings=settings,
        )
        response = await client.post(
            f"/api/conversations/{conversation.id}/turns",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Correlation-Id": f"corr-{expected_state}",
            },
            json={"mode": "google_search", "prompt": expected_state},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["assistant_message"]["search"]["state"] == expected_state

        await db_session.rollback()
        assistant = (
            await db_session.execute(
                select(Message)
                .where(Message.conversation_id == conversation.id, Message.role == "assistant")
            )
        ).scalar_one()
        lifecycle = assistant.message_metadata["search"]["lifecycle"]
        assert lifecycle[0]["event"] == "requested"
        assert lifecycle[-1]["event"] == final_event


async def test_missing_grounding_stays_distinct_from_grounded_after_hardening(client, app, db_session, settings) -> None:
    user = await create_user(
        db_session,
        email="failure-missing-grounding@example.test",
        scopes=["chat:read", "chat:write", "tool:websearch"],
    )
    conversation = await create_conversation(db_session, user_id=user.id)
    await db_session.commit()

    app.state.search_ready = True
    app.state.search_worker = RecordingSearchWorker(
        grounded_result().model_copy(
            update={"google_grounded": False, "sources": [], "citations": [], "suggestions": None}
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
        json={"mode": "google_search", "prompt": "missing-grounding"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"]["search"]["state"] == "missing_grounding"
    assert payload["assistant_message"]["search"]["google_grounded"] is False
    assert payload["assistant_message"]["search"]["sources"] == []
    assert payload["assistant_message"]["search"]["suggestions"] is None
