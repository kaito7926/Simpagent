from __future__ import annotations

from app.authorization.policy import PolicyResult, evaluate_admin_access


def test_admin_access_allows_admin_with_required_scope() -> None:
    result = evaluate_admin_access(
        principal_role="admin",
        principal_scopes={"chat:read", "admin:read"},
        required_scope="admin:read",
    )

    assert result is PolicyResult.allow


def test_admin_access_allows_distinct_admin_write_scope() -> None:
    result = evaluate_admin_access(
        principal_role="admin",
        principal_scopes={"chat:read", "admin:write"},
        required_scope="admin:write",
    )

    assert result is PolicyResult.allow


def test_admin_access_denies_non_admin_role_even_with_scope() -> None:
    result = evaluate_admin_access(
        principal_role="user",
        principal_scopes={"admin:read"},
        required_scope="admin:read",
    )

    assert result is PolicyResult.deny_role


def test_admin_access_denies_under_scoped_admin() -> None:
    result = evaluate_admin_access(
        principal_role="admin",
        principal_scopes={"chat:read"},
        required_scope="admin:read",
    )

    assert result is PolicyResult.deny_scope


def test_admin_access_denies_unknown_state() -> None:
    result = evaluate_admin_access(
        principal_role="super-admin",
        principal_scopes={"admin:read"},
        required_scope="admin:read",
    )

    assert result is PolicyResult.deny_unknown_state
