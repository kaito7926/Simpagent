from __future__ import annotations

from uuid import uuid4

import httpx
import pytest

from tests.smoke._helpers import PUBLIC_BASE_URL, RUN_SMOKE, assert_search_contract


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_public_stack_search_flow_preserves_the_phase_three_contract() -> None:
    if not RUN_SMOKE:
        pytest.skip("Smoke tests require the assembled Compose topology.")

    async with httpx.AsyncClient(base_url=PUBLIC_BASE_URL, timeout=20.0, follow_redirects=True) as client:
        email = f"search-smoke-{uuid4()}@example.test"
        password = "MatKhauBaoMatSearchSmoke123"

        register = await client.post(
            "/api/auth/register",
            headers={"Origin": "http://localhost:3000"},
            json={"email": email, "password": password},
        )
        assert register.status_code == 202

        login = await client.post(
            "/api/auth/login",
            headers={"Origin": "http://localhost:3000"},
            json={"email": email, "password": password},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]

        conversation_id = uuid4()
        search_turn = await client.post(
            f"/api/conversations/{conversation_id}/turns",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Correlation-Id": "corr-smoke-search",
            },
            json={"mode": "google_search", "prompt": "Tin mới hôm nay là gì?"},
        )

        assert search_turn.status_code == 200
        payload = search_turn.json()
        assert_search_contract(payload)
        assert payload["assistant_message"]["id"]
        assert payload["tool_execution"]["correlation_id"] == "corr-smoke-search"
