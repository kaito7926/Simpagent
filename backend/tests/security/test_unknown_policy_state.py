from __future__ import annotations

from app.authorization.policy import PolicyResult, evaluate_required_scopes


def test_missing_scope_denies() -> None:
    result = evaluate_required_scopes(principal_scopes={"chat:read"}, required={"admin:read"})
    assert result is PolicyResult.deny_scope
