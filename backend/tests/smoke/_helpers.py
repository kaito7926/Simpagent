from __future__ import annotations

import asyncio
import os
from time import monotonic, time_ns
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest


PUBLIC_BASE_URL = os.getenv("SIMPAGENT_PUBLIC_BASE_URL", "http://kong:8000")
LOKI_BASE_URL = os.getenv("SIMPAGENT_LOKI_BASE_URL", "http://loki:3100")
RUN_SMOKE = os.getenv("SIMPAGENT_RUN_SMOKE", "false").lower() == "true"
DEFAULT_ORIGIN = os.getenv("SIMPAGENT_SMOKE_ORIGIN", "http://localhost:3000")
EXPECTED_SEARCH_STATE = os.getenv("SIMPAGENT_EXPECT_SEARCH_STATE") or None
VALID_SEARCH_STATES = {
    "grounded",
    "missing_grounding",
    "search_unavailable",
    "provider_failed",
    "timeout",
}

DEMO_ADMIN_EMAIL = os.getenv("SIMPAGENT_DEMO_ADMIN_EMAIL", "demo.admin@simpagent.test")
DEMO_ADMIN_PASSWORD = os.getenv("SIMPAGENT_DEMO_ADMIN_PASSWORD", "ThayDoiMatKhauDemoAdmin123")
OAUTH_PROVIDERS = ("google", "github")


def require_smoke() -> None:
    if not RUN_SMOKE:
        pytest.skip("Smoke tests require the assembled Compose topology.")


def unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid4()}@example.test"


def unique_correlation_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


async def login(
    client: httpx.AsyncClient,
    *,
    email: str,
    password: str,
    correlation_id: str | None = None,
) -> str:
    headers = {"Origin": DEFAULT_ORIGIN}
    if correlation_id is not None:
        headers["X-Correlation-Id"] = correlation_id

    response: httpx.Response | None = None
    for attempt in range(5):
        response = await client.post(
            "/api/auth/login",
            headers=headers,
            json={"email": email, "password": password},
        )
        if response.status_code != 429:
            break
        retry_after = response.headers.get("retry-after")
        delay = float(retry_after) if retry_after and retry_after.isdigit() else 1.0 + attempt
        await asyncio.sleep(min(delay, 5.0))

    assert response is not None
    assert response.status_code == 200
    return str(response.json()["access_token"])


async def fetch_readiness(client: httpx.AsyncClient) -> dict[str, Any]:
    response = await client.get("/ready")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"ready", "degraded"}
    return payload


def assert_readiness_has_oauth_components(payload: dict[str, Any]) -> None:
    components = payload["components"]
    for key in ("database", "migrations", "oauth_google", "oauth_github"):
        assert key in components
    assert components["database"] == "ready"
    assert components["migrations"] == "ready"
    for provider in OAUTH_PROVIDERS:
        assert components[f"oauth_{provider}"] in {"ready", "unconfigured", "unavailable"}


def assert_no_secret_markers(text: str, *markers: str) -> None:
    lowered = text.lower()
    for marker in ("client_secret", "api_key", "password", "refresh_token", *markers):
        assert marker.lower() not in lowered


def assert_oauth_start_contract(response: httpx.Response, *, provider: str) -> None:
    assert response.status_code in {303, 503}
    assert_no_secret_markers(response.text, f"{provider.upper()}_CLIENT_SECRET")
    if response.status_code == 303:
        location = response.headers["location"]
        assert "state=" in location
        assert "client_id=" in location
        assert "client_secret" not in location.lower()
        assert f"simpagent_oauth_{provider}_state" in response.headers.get("set-cookie", "")
        assert "httponly" in response.headers.get("set-cookie", "").lower()
    else:
        payload = response.json()
        assert payload["error"]["code"] == "oauth_provider_unconfigured"


async def register_user(
    client: httpx.AsyncClient,
    *,
    email: str,
    password: str,
    correlation_id: str | None = None,
) -> None:
    headers = {"Origin": DEFAULT_ORIGIN}
    if correlation_id is not None:
        headers["X-Correlation-Id"] = correlation_id

    response = await client.post(
        "/api/auth/register",
        headers=headers,
        json={"email": email, "password": password},
    )
    assert response.status_code == 202


async def register_and_login_user(
    client: httpx.AsyncClient,
    *,
    email: str,
    password: str,
) -> str:
    await register_user(client, email=email, password=password)
    return await login(client, email=email, password=password)


async def submit_search_turn(
    client: httpx.AsyncClient,
    *,
    access_token: str,
    conversation_id: UUID,
    correlation_id: str,
    prompt: str,
) -> dict[str, Any]:
    response = await client.post(
        f"/api/conversations/{conversation_id}/turns",
        headers={
            "Authorization": f"Bearer {access_token}",
            "X-Correlation-Id": correlation_id,
        },
        json={"mode": "google_search", "prompt": prompt},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["tool_execution"]["correlation_id"] == correlation_id
    return payload


def assert_search_contract(
    payload: dict[str, Any],
    *,
    expected_provider: str | None = None,
    expected_state: str | None = None,
) -> None:
    search = payload["assistant_message"]["search"]
    expected = expected_state or EXPECTED_SEARCH_STATE
    if expected is not None:
        assert search["state"] == expected
    else:
        assert search["state"] in VALID_SEARCH_STATES
    if expected_provider is not None:
        assert search["provider"] == expected_provider
    assert payload["assistant_message"]["id"]
    if search["state"] == "grounded":
        if search["provider"] == "gemini":
            assert search["google_grounded"] is True
        else:
            assert search["google_grounded"] is False
        assert search["sources"]
        assert search["citations"]
    else:
        assert search["google_grounded"] is False


async def find_admin_user_by_email(
    client: httpx.AsyncClient,
    *,
    access_token: str,
    email: str,
    page_size: int = 100,
    max_pages: int = 10,
) -> dict[str, Any]:
    offset = 0
    for _ in range(max_pages):
        response = await client.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"limit": page_size, "offset": offset},
        )
        assert response.status_code == 200
        payload = response.json()
        for item in payload["items"]:
            if item["email"] == email:
                return item
        if not payload["page"]["has_more"]:
            break
        offset = int(payload["page"]["next_offset"])
    raise AssertionError(f"Admin user list did not include {email}.")


async def poll_loki_lines(
    query: str,
    *,
    timeout_seconds: float = 30.0,
    poll_interval_seconds: float = 1.0,
    limit: int = 50,
    window_seconds: int = 300,
) -> list[str]:
    deadline = monotonic() + timeout_seconds
    last_lines: list[str] = []

    async with httpx.AsyncClient(base_url=LOKI_BASE_URL, timeout=5.0) as client:
        while True:
            end_ns = time_ns()
            start_ns = end_ns - (window_seconds * 1_000_000_000)
            response = await client.get(
                "/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": start_ns,
                    "end": end_ns,
                    "limit": limit,
                    "direction": "backward",
                },
            )
            response.raise_for_status()
            payload = response.json()
            last_lines = _extract_loki_lines(payload)
            if last_lines or monotonic() >= deadline:
                return last_lines
            await asyncio.sleep(poll_interval_seconds)


def _extract_loki_lines(payload: dict[str, Any]) -> list[str]:
    results = payload.get("data", {}).get("result", [])
    lines: list[str] = []
    for stream in results:
        values = stream.get("values", [])
        for _, line in values:
            lines.append(str(line))
    return lines


__all__ = [
    "DEFAULT_ORIGIN",
    "DEMO_ADMIN_EMAIL",
    "DEMO_ADMIN_PASSWORD",
    "EXPECTED_SEARCH_STATE",
    "OAUTH_PROVIDERS",
    "PUBLIC_BASE_URL",
    "RUN_SMOKE",
    "assert_no_secret_markers",
    "assert_oauth_start_contract",
    "assert_readiness_has_oauth_components",
    "assert_search_contract",
    "fetch_readiness",
    "find_admin_user_by_email",
    "login",
    "poll_loki_lines",
    "register_and_login_user",
    "require_smoke",
    "submit_search_turn",
    "unique_correlation_id",
    "unique_email",
]
