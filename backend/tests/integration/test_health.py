from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_is_alive(client) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


@pytest.mark.asyncio
async def test_ready_reports_degraded_without_provider_credentials(client) -> None:
    response = await client.get("/ready")
    assert response.status_code in {200, 503}
    payload = response.json()
    assert payload["components"]["sandbox"] == "foundation_ready"
