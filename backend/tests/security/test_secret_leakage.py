from __future__ import annotations

import pytest

from app.core.config import Settings
from app.identity.redaction import sanitize_admin_evidence


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


@pytest.mark.security
@pytest.mark.asyncio
async def test_github_oauth_failure_does_not_leak_secret_material(client, secret_canary: str) -> None:
    response = await client.get(
        "/api/auth/oauth/github/callback",
        params={
            "state": secret_canary,
            "code": "github-code-containing-client_secret",
            "error": "access_denied",
        },
    )

    assert response.status_code in {400, 401, 503}
    assert secret_canary not in response.text
    assert "github-code-containing-client_secret" not in response.text
    assert "GITHUB_CLIENT_SECRET" not in response.text


@pytest.mark.security
def test_admin_evidence_redaction_removes_canary_from_recursive_snippets(secret_canary: str) -> None:
    sanitized = sanitize_admin_evidence(
        {
            "prompt": f"please summarize {secret_canary}",
            "provider_payload": {
                "groundingMetadata": {"token": secret_canary},
                "searchEntryPoint": {"renderedContent": f"<b>{secret_canary}</b>"},
            },
            "sandbox": {
                "stdout": f"full sandbox output {secret_canary}",
                "container_id": "abc123def456",
                "host_path": "/var/run/docker.sock",
            },
            "safe": "retained",
        }
    )

    dumped = repr(sanitized)
    assert secret_canary not in dumped
    assert "groundingMetadata" not in dumped
    assert "renderedContent" not in dumped
    assert "/var/run/docker.sock" not in dumped
    assert sanitized["safe"] == "retained"
