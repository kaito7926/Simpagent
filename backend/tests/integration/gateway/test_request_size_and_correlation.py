from __future__ import annotations

from pathlib import Path
import re

import httpx
import pytest

from tests.smoke._helpers import DEFAULT_ORIGIN, PUBLIC_BASE_URL, RUN_SMOKE, unique_correlation_id


REPO_ROOT = Path(__file__).resolve().parents[4]
KONG_CONFIG = REPO_ROOT / "kong" / "kong.yml"


def _kong_config() -> str:
    if not KONG_CONFIG.exists():
        pytest.skip("Kong declarative config is outside the backend container test context.")
    return KONG_CONFIG.read_text(encoding="utf-8")


def test_kong_rejects_large_requests_before_fastapi() -> None:
    config = _kong_config()

    assert "name: request-size-limiting" in config
    assert "allowed_payload_size: 1" in config
    assert "route: backend-auth-login" in config
    assert "route: backend-chat-turns" in config
    assert "route: backend-python-execute" in config


def test_kong_generates_or_propagates_correlation_ids() -> None:
    config = _kong_config()

    assert "name: correlation-id" in config
    assert "header_name: X-Correlation-Id" in config
    assert "generator: uuid" in config
    assert "echo_downstream: true" in config


@pytest.mark.parametrize(
    "correlation_id",
    [
        "corr-allowed-123456",
        "bad correlation id with spaces",
        "x" * 129,
    ],
)
@pytest.mark.asyncio
async def test_fastapi_accepts_only_valid_correlation_ids(client, correlation_id: str) -> None:
    response = await client.get("/health", headers={"X-Correlation-Id": correlation_id})

    if re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", correlation_id):
        assert response.status_code == 200
        assert response.headers["X-Correlation-Id"] == correlation_id
    else:
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "invalid_correlation_id"


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_correlation_id_is_preserved_through_kong_and_fastapi() -> None:
    if not RUN_SMOKE:
        pytest.skip("Gateway smoke tests require the assembled Compose topology.")

    correlation_id = unique_correlation_id("corr-gateway")
    async with httpx.AsyncClient(base_url=PUBLIC_BASE_URL, timeout=10.0) as client:
        response = await client.get("/health", headers={"X-Correlation-Id": correlation_id})

    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == correlation_id


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_oversized_request_body_is_rejected_by_kong() -> None:
    if not RUN_SMOKE:
        pytest.skip("Gateway smoke tests require the assembled Compose topology.")

    oversized_payload = {"prompt": "x" * (1024 * 1024 + 1)}
    async with httpx.AsyncClient(base_url=PUBLIC_BASE_URL, timeout=10.0) as client:
        response = await client.post(
            "/api/auth/login",
            headers={"Origin": DEFAULT_ORIGIN},
            json=oversized_payload,
        )

    assert response.status_code in {413, 400}
    assert response.headers.get("X-Correlation-Id")
