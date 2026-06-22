from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from tests.smoke._helpers import DEFAULT_ORIGIN, PUBLIC_BASE_URL, RUN_SMOKE, unique_email


REPO_ROOT = Path(__file__).resolve().parents[4]
KONG_CONFIG = REPO_ROOT / "kong" / "kong.yml"


def _kong_config() -> str:
    if not KONG_CONFIG.exists():
        pytest.skip("Kong declarative config is outside the backend container test context.")
    return KONG_CONFIG.read_text(encoding="utf-8")


def test_kong_uses_route_specific_rate_limits_for_auth_chat_and_tools() -> None:
    config = _kong_config()

    for route_name in (
        "backend-auth-login",
        "backend-auth-register",
        "backend-auth-refresh",
        "backend-chat-turns",
        "backend-python-execute",
    ):
        assert f"route: {route_name}" in config

    assert config.count("name: rate-limiting") >= 4
    assert "policy: local" in config
    assert "limit_by: ip" in config
    assert "hide_client_headers: false" in config
    assert "fault_tolerant: true" in config


def test_sensitive_and_tool_routes_are_stricter_than_chat_routes() -> None:
    config = _kong_config()

    assert "auth-sensitive-rate-limit" in config
    assert "refresh-sensitive-rate-limit" in config
    assert "tool-sensitive-rate-limit" in config
    assert "chat-standard-rate-limit" in config
    assert "minute: 5" in config
    assert "minute: 20" in config
    assert "minute: 30" in config
    assert "minute: 60" in config


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_login_route_returns_429_with_limit_metadata_through_kong() -> None:
    if not RUN_SMOKE:
        pytest.skip("Gateway smoke tests require the assembled Compose topology.")

    async with httpx.AsyncClient(base_url=PUBLIC_BASE_URL, timeout=10.0) as client:
        status_codes: list[int] = []
        last_response: httpx.Response | None = None
        for _ in range(8):
            last_response = await client.post(
                "/api/auth/login",
                headers={"Origin": DEFAULT_ORIGIN},
                json={"email": unique_email("rate-login"), "password": "WrongPassword12345"},
            )
            status_codes.append(last_response.status_code)
            if last_response.status_code == 429:
                break

        assert 429 in status_codes
        assert last_response is not None
        assert any(
            header in last_response.headers
            for header in ("RateLimit-Remaining", "X-RateLimit-Remaining-Minute")
        )
