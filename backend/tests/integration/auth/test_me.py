from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_me_requires_principal(client) -> None:
    response = await client.get("/api/auth/me")
    assert response.status_code == 401
