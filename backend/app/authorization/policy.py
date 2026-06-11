from __future__ import annotations

from enum import Enum

from app.schemas.auth import ADMIN_SCOPES, STANDARD_USER_SCOPES


class Role(str, Enum):
    user = "user"
    admin = "admin"


class Scope(str, Enum):
    chat_read = "chat:read"
    chat_write = "chat:write"
    tool_websearch = "tool:websearch"
    tool_python = "tool:python"
    admin_read = "admin:read"
    admin_write = "admin:write"


class PolicyResult(str, Enum):
    allow = "ALLOW"
    deny_missing_principal = "DENY_MISSING_PRINCIPAL"
    deny_inactive = "DENY_INACTIVE"
    deny_role = "DENY_ROLE"
    deny_scope = "DENY_SCOPE"
    deny_unknown_state = "DENY_UNKNOWN_STATE"


KNOWN_ROLE_VALUES = {role.value for role in Role}
KNOWN_SCOPE_VALUES = {scope.value for scope in Scope}
STANDARD_SCOPE_BUNDLE = [*STANDARD_USER_SCOPES]
ADMIN_SCOPE_BUNDLE = [*ADMIN_SCOPES]


def evaluate_required_scopes(*, principal_scopes: set[str], required: set[str]) -> PolicyResult:
    if not required.issubset(principal_scopes):
        return PolicyResult.deny_scope
    return PolicyResult.allow


def evaluate_admin_access(*, principal_role: str, principal_scopes: set[str], required_scope: str) -> PolicyResult:
    if principal_role not in KNOWN_ROLE_VALUES or set(principal_scopes) - KNOWN_SCOPE_VALUES:
        return PolicyResult.deny_unknown_state
    if required_scope not in KNOWN_SCOPE_VALUES:
        return PolicyResult.deny_unknown_state
    if principal_role != Role.admin.value:
        return PolicyResult.deny_role
    if required_scope not in principal_scopes:
        return PolicyResult.deny_scope
    return PolicyResult.allow
