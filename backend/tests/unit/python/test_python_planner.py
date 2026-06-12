from __future__ import annotations

import pytest

from app.agent.decisions import OpenAIPythonPlanner
from app.ai.chat_adapter import ChatProviderError
from app.ai.schemas import ChatTurn


@pytest.mark.asyncio
async def test_embedded_python_code_does_not_require_llm_secret(settings) -> None:
    planner = OpenAIPythonPlanner(
        settings=settings.model_copy(
            update={
                "llm_api_key": None,
                "llm_api_key_file": "/tmp/missing-llm-secret",
            }
        )
    )
    prompt = "Use Python to run this snippet.\n```python\nprint(2 + 2)\n```"

    plan = await planner.plan(
        messages=[ChatTurn(role="user", content=prompt)],
        prompt=prompt,
        state_binding_names=(),
    )

    assert plan.code == "print(2 + 2)"
    assert plan.needs_search is False


@pytest.mark.asyncio
async def test_non_embedded_plan_requires_configured_llm_client(settings) -> None:
    planner = OpenAIPythonPlanner(
        settings=settings.model_copy(
            update={
                "llm_api_key": None,
                "llm_api_key_file": "/tmp/missing-llm-secret",
            }
        )
    )
    prompt = "Use Python to calculate the rolling average for this dataset."

    with pytest.raises(ChatProviderError) as exc_info:
        await planner.plan(
            messages=[ChatTurn(role="user", content=prompt)],
            prompt=prompt,
            state_binding_names=(),
        )

    assert exc_info.value.code == "provider_unconfigured"
