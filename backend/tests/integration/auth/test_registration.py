from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_register_accepts_generic_response(client) -> None:
    response = await client.post(
        "/api/auth/register",
        headers={"Origin": "http://localhost:3000"},
        json={"email": "student@example.com", "password": "matkhau-bao-mat-123"},
    )
    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "accepted"
