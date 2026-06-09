from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_login_unknown_user_fails_generically(client) -> None:
    response = await client.post(
        "/api/auth/login",
        headers={"Origin": "http://localhost:3000"},
        json={"email": "missing@example.com", "password": "matkhau-bao-mat-123"},
    )
    assert response.status_code == 401
    assert "Unable to sign in" in response.text
