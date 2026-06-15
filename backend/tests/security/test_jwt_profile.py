from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest

from app.schemas.auth import STANDARD_USER_SCOPES
from app.security.access_tokens import (
    JWT_LEEWAY_SECONDS,
    AccessTokenError,
    decode_access_token,
    issue_access_token,
)


def test_decode_rejects_malformed_token(settings) -> None:
    with pytest.raises(AccessTokenError):
        decode_access_token("not-a-token", settings=settings)


def test_decode_uses_supplied_now_for_temporal_claims(settings) -> None:
    issued_at = datetime(2020, 1, 1, tzinfo=UTC)
    user_id = UUID("00000000-0000-0000-0000-000000000001")
    token = issue_access_token(
        user_id=user_id,
        role="user",
        scopes=STANDARD_USER_SCOPES,
        settings=settings,
        now=issued_at,
    )

    claims = decode_access_token(
        token,
        settings=settings,
        now=issued_at + timedelta(seconds=settings.access_token_ttl_seconds - 1),
    )

    assert claims.sub == user_id
    assert claims.iat == int(issued_at.timestamp())


def test_decode_rejects_expired_token_against_supplied_now(settings) -> None:
    issued_at = datetime(2020, 1, 1, tzinfo=UTC)
    token = issue_access_token(
        user_id=UUID("00000000-0000-0000-0000-000000000002"),
        role="user",
        scopes=STANDARD_USER_SCOPES,
        settings=settings,
        now=issued_at,
    )

    with pytest.raises(AccessTokenError):
        decode_access_token(
            token,
            settings=settings,
            now=issued_at + timedelta(seconds=settings.access_token_ttl_seconds + JWT_LEEWAY_SECONDS),
        )


def test_kong_jwt_screening_is_coarse_and_backend_still_rejects_stale_claims(settings) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    kong_config_path = repo_root / "kong" / "kong.yml"
    if not kong_config_path.exists():
        pytest.skip("Kong declarative config is outside the backend container test context.")
    kong_config = kong_config_path.read_text(encoding="utf-8")
    principal_source = (repo_root / "backend" / "app" / "authorization" / "principal.py").read_text(
        encoding="utf-8"
    )
    issued_at = datetime(2020, 1, 1, tzinfo=UTC)
    token = issue_access_token(
        user_id=UUID("00000000-0000-0000-0000-000000000003"),
        role="user",
        scopes=STANDARD_USER_SCOPES,
        settings=settings,
        now=issued_at,
    )

    claims = decode_access_token(token, settings=settings, now=issued_at)

    assert claims.role == "user"
    assert claims.scopes == STANDARD_USER_SCOPES
    assert claims.kid == settings.jwt_active_kid
    assert "name: jwt" in kong_config
    assert "anonymous:" in kong_config
    assert "stale_token" in principal_source
    assert "inactive_principal" in principal_source
    assert "unknown_policy_state" in principal_source
