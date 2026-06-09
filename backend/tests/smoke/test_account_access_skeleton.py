from __future__ import annotations

import os

import httpx
import pytest


PUBLIC_BASE_URL = os.getenv("SIMPAGENT_PUBLIC_BASE_URL", "http://kong:8000")
RUN_SMOKE = os.getenv("SIMPAGENT_RUN_SMOKE", "false").lower() == "true"


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_account_access_walking_skeleton() -> None:
    if not RUN_SMOKE:
        pytest.skip("Smoke tests require the assembled Compose topology.")
    async with httpx.AsyncClient(base_url=PUBLIC_BASE_URL, timeout=10.0, follow_redirects=True) as client:
        landing = await client.get("/")
        assert landing.status_code == 200
        assert "SimpAgent" in landing.text

        register = await client.post(
            "/api/auth/register",
            headers={"Origin": "http://localhost:3000"},
            json={"email": "student@example.com", "password": "matkhau-bao-mat-123"},
        )
        assert register.status_code == 202

        login = await client.post(
            "/api/auth/login",
            headers={"Origin": "http://localhost:3000"},
            json={"email": "student@example.com", "password": "matkhau-bao-mat-123"},
        )
        assert login.status_code == 200
        access_token = login.json()["access_token"]

        me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {access_token}"})
        assert me.status_code == 200
        assert me.json()["email"] == "student@example.com"
