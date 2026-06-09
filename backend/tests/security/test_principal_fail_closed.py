from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_missing_bearer_fails_closed(client) -> None:
    response = await client.get("/api/auth/me")
    assert response.status_code == 401
