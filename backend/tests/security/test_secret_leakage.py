from __future__ import annotations

import pytest

from app.core.config import Settings


@pytest.mark.security
def test_settings_repr_redacts_sensitive_values(settings: Settings, secret_canary: str) -> None:
    repr_text = repr(settings)
    assert secret_canary not in repr_text
    assert "postgresql+psycopg://" not in repr_text


@pytest.mark.security
@pytest.mark.asyncio
async def test_health_response_does_not_echo_canary(client, secret_canary: str) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert secret_canary not in response.text


@pytest.mark.security
@pytest.mark.asyncio
async def test_validation_errors_do_not_leak_secret(client, secret_canary: str) -> None:
    response = await client.post("/api/auth/login")
    assert response.status_code == 422
    assert secret_canary not in response.text
