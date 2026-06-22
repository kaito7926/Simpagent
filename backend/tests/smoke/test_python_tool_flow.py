from __future__ import annotations

import os

import httpx
import pytest

from tests.smoke._helpers import (
    DEMO_ADMIN_EMAIL,
    DEMO_ADMIN_PASSWORD,
    unique_correlation_id,
)


PUBLIC_BASE_URL = os.getenv("SIMPAGENT_PUBLIC_BASE_URL", "http://kong:8000")
RUN_SMOKE = os.getenv("SIMPAGENT_RUN_SMOKE", "false").lower() == "true"
ORIGIN = "http://localhost:3000"
DEMO_EMAIL = "demo.user@simpagent.test"
DEMO_PASSWORD = "ThayDoiMatKhauDemoUser123"


async def _login(client: httpx.AsyncClient, *, email: str, password: str) -> str:
    login = await client.post(
        "/api/auth/login",
        headers={"Origin": ORIGIN},
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_python_tool_flow_through_public_topology() -> None:
    if not RUN_SMOKE:
        pytest.skip("Smoke tests require the assembled Compose topology.")

    async with httpx.AsyncClient(base_url=PUBLIC_BASE_URL, timeout=120.0, follow_redirects=True) as client:
        token = await _login(
            client,
            email=DEMO_EMAIL,
            password=DEMO_PASSWORD,
        )
        admin_token = await _login(
            client,
            email=DEMO_ADMIN_EMAIL,
            password=DEMO_ADMIN_PASSWORD,
        )
        toggle_response = await client.patch(
            "/api/admin/orchestration/trusted-supervisor",
            headers={
                **_auth(admin_token),
                "X-Correlation-Id": unique_correlation_id("corr-smk-supervisor-enable"),
            },
            json={"enabled": True},
        )
        assert toggle_response.status_code == 200
        assert toggle_response.json()["trusted_supervisor_enabled"] is True

        created = await client.post(
            "/api/conversations",
            headers=_auth(token),
            json={
                "initial_message": {
                    "client_message_id": "python-smoke-success",
                    "content": "Use Python to run this code and summarize the result.\n```python\nprint(2 + 2)\n```",
                }
            },
        )

        assert created.status_code == 201
        body = created.json()
        conversation_id = body["id"]
        first_python = body["messages"][1]["metadata"]["python_result"]

        assert body["messages"][1]["metadata"]["tool_name"] == "python"
        assert body["messages"][1]["status"] == "completed"
        assert first_python["status"] == "succeeded"
        assert first_python["profile_name"] == "python-basic-v1"
        assert "successfully" in first_python["summary"].lower() or "completed" in first_python["summary"].lower()

        limited = await client.post(
            f"/api/conversations/{conversation_id}/messages",
            headers=_auth(token),
            json={
                "client_message_id": "python-smoke-limit",
                "content": "Use Python to run this code.\n```python\nprint('x' * 50000)\n```",
            },
        )

        assert limited.status_code == 200
        limited_python = limited.json()["messages"][-1]["metadata"]["python_result"]
        assert limited_python["status"] == "limit_reached"
        assert limited_python["limit_triggered"] == "output_size"

        denied = await client.post(
            f"/api/conversations/{conversation_id}/messages",
            headers=_auth(token),
            json={
                "client_message_id": "python-smoke-denied",
                "content": "Search the web for today's gold price and then use Python to average it for me.",
            },
        )

        assert denied.status_code == 200
        denied_python = denied.json()["messages"][-1]["metadata"]["python_result"]
        assert denied_python["status"] == "denied"
        assert denied_python["denial_reason"] == "search_required"
