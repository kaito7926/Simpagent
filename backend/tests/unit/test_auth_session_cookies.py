from __future__ import annotations

from fastapi import Response

from app.api.routes.auth import _set_auth_cookies as set_local_auth_cookies
from app.api.routes.auth_oauth import _set_auth_cookies as set_oauth_auth_cookies
from app.security.refresh_tokens import CSRF_COOKIE_NAME, REFRESH_COOKIE_NAME


def _auth_cookie_headers(response: Response) -> list[str]:
    return [
        header
        for header in response.headers.getlist("set-cookie")
        if header.startswith(f"{REFRESH_COOKIE_NAME}=") or header.startswith(f"{CSRF_COOKIE_NAME}=")
    ]


def _assert_session_auth_cookies(headers: list[str]) -> None:
    assert len(headers) == 2
    for header in headers:
        lowered = header.lower()
        assert "max-age=" not in lowered
        assert "expires=" not in lowered


def test_local_auth_cookies_are_session_only(settings) -> None:
    response = Response()

    set_local_auth_cookies(
        response,
        settings=settings,
        refresh_token="refresh-token-value",
        csrf_token="csrf-token-value",
    )

    _assert_session_auth_cookies(_auth_cookie_headers(response))


def test_oauth_auth_cookies_are_session_only(settings) -> None:
    response = Response()

    set_oauth_auth_cookies(
        response,
        settings=settings,
        refresh_token="refresh-token-value",
        csrf_token="csrf-token-value",
    )

    _assert_session_auth_cookies(_auth_cookie_headers(response))
