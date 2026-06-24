from __future__ import annotations

from fastapi import Response

from app.api.routes.auth_oauth import _delete_state_cookie, _issue_state_cookie
from app.security.oauth_transaction import issue_oauth_transaction


def test_oauth_state_cookie_uses_lax_even_when_session_cookies_are_strict(settings) -> None:
    strict_settings = settings.model_copy(update={"cookie_samesite": "strict"})
    response = Response()
    transaction = issue_oauth_transaction(
        provider="google",
        settings=strict_settings,
        now=strict_settings.now_utc(),
    )

    _issue_state_cookie(response, provider="google", transaction=transaction, settings=strict_settings)

    set_cookie = response.headers["set-cookie"]
    assert "simpagent_oauth_google_state=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "SameSite=strict" not in set_cookie
    assert transaction.code_verifier not in set_cookie
    assert transaction.state not in set_cookie


def test_oauth_state_cookie_delete_matches_lax_callback_cookie(settings) -> None:
    strict_settings = settings.model_copy(update={"cookie_samesite": "strict"})
    response = Response()

    _delete_state_cookie(response, provider="github", settings=strict_settings)

    set_cookie = response.headers["set-cookie"]
    assert "simpagent_oauth_github_state=" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "SameSite=strict" not in set_cookie
