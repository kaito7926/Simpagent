from __future__ import annotations

import os

import httpx
import pytest

PUBLIC_BASE_URL = os.getenv("SIMPAGENT_PUBLIC_BASE_URL", "http://kong:8000")
RUN_SMOKE = os.getenv("SIMPAGENT_RUN_SMOKE", "false").lower() == "true"


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_topology_reports_degraded_but_usable_account_stack() -> None:
    if not RUN_SMOKE:
        pytest.skip("Smoke tests require the assembled Compose topology.")
    async with httpx.AsyncClient(base_url=PUBLIC_BASE_URL, timeout=10.0, follow_redirects=True) as client:
        ready = await client.get("/ready")
        assert ready.status_code == 200
        payload = ready.json()
        assert payload["status"] in {"ready", "degraded"}
        assert payload["components"]["database"] == "ready"
        assert payload["components"]["sandbox"] == "foundation_ready"

        page = await client.get("/")
        assert page.status_code == 200
        assert "SimpAgent" in page.text
        assert "Đăng nhập | SimpAgent" in page.text

        register = await client.post(
            "/api/auth/register",
            headers={"Origin": "http://localhost:3000"},
            json={
                "email": "topology@example.com",
                "password": "MatKhauBaoMatTopology123",
            },
        )
        assert register.status_code == 202

        login = await client.post(
            "/api/auth/login",
            headers={"Origin": "http://localhost:3000"},
            json={
                "email": "topology@example.com",
                "password": "MatKhauBaoMatTopology123",
            },
        )
        assert login.status_code == 200
        token = login.json()["access_token"]

        me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["email"] == "topology@example.com"
