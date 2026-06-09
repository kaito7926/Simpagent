from __future__ import annotations

import asyncio

import pytest

from app.identity.contracts import VerifiedIdentity
from app.identity.local_provider import LocalIdentityProvider


class DummySession:
    pass


def test_verified_identity_contract_shape() -> None:
    identity = VerifiedIdentity(
        issuer="local",
        subject="local:user",
        email="user@example.com",
        email_verified=True,
        authentication_method="password",
    )
    assert identity.issuer == "local"


def test_local_provider_rejects_wrong_request_type() -> None:
    provider = LocalIdentityProvider(DummySession())  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        asyncio.run(provider.authenticate(object()))
