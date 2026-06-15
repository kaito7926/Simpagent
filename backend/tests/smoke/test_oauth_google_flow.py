from __future__ import annotations

import httpx
import pytest

from tests.smoke._helpers import PUBLIC_BASE_URL, RUN_SMOKE


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_google_oauth_start_is_exposed_without_secret_leakage() -> None:
    if not RUN_SMOKE:
        pytest.skip("Smoke tests require the assembled Compose topology.")
    async with httpx.AsyncClient(
        base_url=PUBLIC_BASE_URL,
        timeout=10.0,
        follow_redirects=False,
    ) as client:
        response = await client.get("/api/auth/oauth/google/start")

    assert response.status_code in {302, 303, 307, 503}
    assert "client_secret" not in response.text
    assert "GOOGLE_CLIENT_SECRET" not in response.text
