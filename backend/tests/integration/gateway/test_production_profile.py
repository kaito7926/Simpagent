from __future__ import annotations

import pytest

from app.core.config import Settings


def _base_settings(**overrides):
    values = {
        "app_env": "production",
        "database_url_file": "/run/secrets/database_url",
        "allowed_origins": ["https://app.example.test"],
        "cookie_secure": True,
        "demo_seed_enabled": False,
        "jwt_private_key_file": "/run/secrets/jwt_private_key",
        "jwt_public_key_file": "/run/secrets/jwt_public_key",
        "refresh_hmac_key_file": "/run/secrets/refresh_hmac_key",
        "csrf_hmac_key_file": "/run/secrets/csrf_hmac_key",
        "python_capability_secret_file": "/run/secrets/python_capability_secret",
        "public_app_origin": "https://app.example.test",
        "public_api_origin": "https://api.example.test",
        "trusted_proxy_cidrs": ["10.0.0.0/8", "172.16.0.0/12"],
    }
    values.update(overrides)
    return values


def test_production_requires_public_app_and_api_origins() -> None:
    with pytest.raises(ValueError, match="public app origin"):
        Settings(**_base_settings(public_app_origin=None))

    with pytest.raises(ValueError, match="public API origin"):
        Settings(**_base_settings(public_api_origin=None))


def test_production_rejects_public_origins_with_paths_or_plain_http() -> None:
    with pytest.raises(ValueError):
        Settings(**_base_settings(public_app_origin="https://app.example.test/path"))

    with pytest.raises(ValueError):
        Settings(**_base_settings(public_api_origin="http://api.example.test"))


def test_production_requires_trusted_proxy_cidrs_for_forwarded_headers() -> None:
    with pytest.raises(ValueError, match="trusted proxy"):
        Settings(**_base_settings(trusted_proxy_cidrs=[]))


def test_trusted_proxy_cidrs_are_valid_networks() -> None:
    with pytest.raises(ValueError, match="trusted proxy"):
        Settings(**_base_settings(trusted_proxy_cidrs=["not-a-cidr"]))


@pytest.mark.asyncio
async def test_forwarded_client_ip_is_used_only_from_trusted_proxy(client) -> None:
    untrusted = await client.get(
        "/health",
        headers={
            "X-Forwarded-For": "198.51.100.10",
            "X-Forwarded-Proto": "https",
        },
    )
    assert untrusted.status_code == 200
    assert untrusted.headers.get("X-Forwarded-For") is None

    trusted = await client.get(
        "/health",
        headers={
            "X-Forwarded-For": "198.51.100.10",
            "X-Forwarded-Proto": "https",
            "X-Trusted-Proxy-For-Test": "127.0.0.1",
        },
    )
    assert trusted.status_code == 200
