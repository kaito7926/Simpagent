from __future__ import annotations

import httpx
import pytest

from tests.smoke._helpers import (
    DEFAULT_ORIGIN,
    PUBLIC_BASE_URL,
    assert_readiness_has_oauth_components,
    fetch_readiness,
    require_smoke,
    unique_email,
)


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_topology_reports_degraded_but_usable_account_stack() -> None:
    require_smoke()
    async with httpx.AsyncClient(base_url=PUBLIC_BASE_URL, timeout=10.0, follow_redirects=True) as client:
        payload = await fetch_readiness(client)
        assert_readiness_has_oauth_components(payload)
        assert payload["components"]["sandbox"] == "foundation_ready"

        page = await client.get("/")
        assert page.status_code == 200
        assert "SimpAgent" in page.text
        assert "Đăng nhập | SimpAgent" in page.text

        email = unique_email("topology")
        register = await client.post(
            "/api/auth/register",
            headers={"Origin": DEFAULT_ORIGIN},
            json={
                "email": email,
                "password": "MatKhauBaoMatTopology123",
            },
        )
        assert register.status_code == 202

        login = await client.post(
            "/api/auth/login",
            headers={"Origin": DEFAULT_ORIGIN},
            json={
                "email": email,
                "password": "MatKhauBaoMatTopology123",
            },
        )
        assert login.status_code == 200
        token = login.json()["access_token"]

        me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["email"] == email
