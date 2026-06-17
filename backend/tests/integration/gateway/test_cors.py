from __future__ import annotations

import re
from pathlib import Path

import httpx
import pytest

from tests.smoke._helpers import DEFAULT_ORIGIN, PUBLIC_BASE_URL, RUN_SMOKE


REPO_ROOT = Path(__file__).resolve().parents[4]
KONG_CONFIG = REPO_ROOT / "kong" / "kong.yml"


def _kong_config() -> str:
    if not KONG_CONFIG.exists():
        pytest.skip("Kong declarative config is outside the backend container test context.")
    return KONG_CONFIG.read_text(encoding="utf-8")


def test_kong_cors_is_strict_for_browser_clients() -> None:
    config = _kong_config()

    assert '_format_version: "3.0"' in config
    assert "_transform: true" in config
    assert "name: cors" in config
    assert "http://localhost:3000" in config
    assert "http://localhost:8000" not in config
    assert re.search(r"(?m)^\s*-\s*['\"]?\*['\"]?\s*$", config) is None
    assert "credentials: true" in config
    for method in ("GET", "POST", "PATCH", "DELETE", "OPTIONS"):
        assert f"- {method}" in config
    for header in ("Authorization", "Content-Type", "X-CSRF-Token", "X-Correlation-Id"):
        assert f"- {header}" in config
    assert "exposed_headers:" in config
    assert "- X-Correlation-Id" in config


def test_kong_cors_plugin_is_bound_to_public_routes_not_a_wildcard_proxy() -> None:
    config = _kong_config()

    assert "route: backend-auth-login" in config
    assert "route: backend-auth-register" in config
    assert "route: backend-auth-refresh" in config
    assert "route: backend-oauth" in config
    assert "- /api/auth/oauth" in config
    assert "- /api/oauth" not in config
    assert "route: backend-chat-turns" in config
    assert "route: backend-python-execute" in config


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_browser_preflight_allows_only_configured_origin_through_kong() -> None:
    if not RUN_SMOKE:
        pytest.skip("Gateway smoke tests require the assembled Compose topology.")

    async with httpx.AsyncClient(base_url=PUBLIC_BASE_URL, timeout=10.0) as client:
        allowed = await client.options(
            "/api/auth/login",
            headers={
                "Origin": DEFAULT_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization, Content-Type, X-CSRF-Token, X-Correlation-Id",
            },
        )
        assert allowed.status_code in {200, 204}
        assert allowed.headers["Access-Control-Allow-Origin"] == DEFAULT_ORIGIN
        assert "X-Correlation-Id" in allowed.headers.get("Access-Control-Expose-Headers", "")

        blocked = await client.options(
            "/api/auth/login",
            headers={
                "Origin": "https://evil.example.test",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization, Content-Type",
            },
        )
        assert blocked.headers.get("Access-Control-Allow-Origin") != "https://evil.example.test"
