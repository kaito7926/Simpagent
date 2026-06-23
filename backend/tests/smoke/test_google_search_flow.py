from __future__ import annotations

from uuid import uuid4

import httpx
import pytest

from tests.smoke._helpers import (
    DEMO_ADMIN_EMAIL,
    DEMO_ADMIN_PASSWORD,
    PUBLIC_BASE_URL,
    RUN_SMOKE,
    assert_search_contract,
    login,
    register_and_login_user,
    require_smoke,
    submit_search_turn,
    unique_correlation_id,
    unique_email,
)


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


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_public_stack_search_flow_covers_gemini_firecrawl_and_unconfigured_matrix() -> None:
    require_smoke()

    async with httpx.AsyncClient(base_url=PUBLIC_BASE_URL, timeout=25.0, follow_redirects=True) as client:
        admin_token = await login(
            client,
            email=DEMO_ADMIN_EMAIL,
            password=DEMO_ADMIN_PASSWORD,
            correlation_id=unique_correlation_id("corr-smk-provider-admin-login"),
        )
        user_token = await register_and_login_user(
            client,
            email=unique_email("search-provider-matrix"),
            password="MatKhauBaoMatSearchMatrix123",
        )
        conversation_id = uuid4()

        clear_response = await client.patch(
            "/api/admin/orchestration/websearch-provider",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Correlation-Id": unique_correlation_id("corr-smk-provider-clear-start"),
            },
            json={"provider": None},
        )
        assert clear_response.status_code == 200
        default_provider = clear_response.json()["websearch_provider_effective"]
        assert default_provider == "gemini"

        gemini_payload = await submit_search_turn(
            client,
            access_token=user_token,
            conversation_id=conversation_id,
            correlation_id=unique_correlation_id("corr-smk-gemini-default"),
            prompt="current software supply chain security news",
        )
        assert_search_contract(gemini_payload)
        assert gemini_payload["assistant_message"]["search"]["provider"] == "gemini"

        firecrawl_response = await client.patch(
            "/api/admin/orchestration/websearch-provider",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Correlation-Id": unique_correlation_id("corr-smk-provider-firecrawl"),
            },
            json={"provider": "firecrawl"},
        )
        assert firecrawl_response.status_code == 200
        assert firecrawl_response.json()["websearch_provider_effective"] == "firecrawl"

        firecrawl_payload = await submit_search_turn(
            client,
            access_token=user_token,
            conversation_id=conversation_id,
            correlation_id=unique_correlation_id("corr-smk-firecrawl-override"),
            prompt="current web application security guidance",
        )
        assert_search_contract(firecrawl_payload)
        firecrawl_search = firecrawl_payload["assistant_message"]["search"]
        assert firecrawl_search["provider"] == "firecrawl"
        assert firecrawl_search["state"] == "grounded"
        assert firecrawl_search["google_grounded"] is False

        clear_back_response = await client.patch(
            "/api/admin/orchestration/websearch-provider",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Correlation-Id": unique_correlation_id("corr-smk-provider-clear-end"),
            },
            json={"provider": None},
        )
        assert clear_back_response.status_code == 200
        assert clear_back_response.json()["websearch_provider_override"] is None
        assert clear_back_response.json()["websearch_provider_effective"] == "gemini"
