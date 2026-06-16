from __future__ import annotations

import httpx
import pytest

from tests.smoke._helpers import (
    PUBLIC_BASE_URL,
    assert_oauth_start_contract,
    assert_readiness_has_oauth_components,
    fetch_readiness,
    require_smoke,
)


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_google_oauth_start_matches_auth_shell_readiness_without_secret_leakage() -> None:
    require_smoke()
    async with httpx.AsyncClient(
        base_url=PUBLIC_BASE_URL,
        timeout=10.0,
        follow_redirects=False,
    ) as client:
        readiness = await fetch_readiness(client)
        assert_readiness_has_oauth_components(readiness)
        response = await client.get("/api/auth/oauth/google/start")

    assert readiness["components"]["oauth_google"] in {"ready", "unconfigured", "unavailable"}
    assert_oauth_start_contract(response, provider="google")
