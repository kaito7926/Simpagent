from __future__ import annotations

import pytest

from app.security.access_tokens import AccessTokenError, decode_access_token


def test_decode_rejects_malformed_token(settings) -> None:
    with pytest.raises(AccessTokenError):
        decode_access_token("not-a-token", settings=settings)
