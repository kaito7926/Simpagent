---
status: complete
quick_task: 260611-rv2
description: improve admin RBAC and evidence endpoints
completed: 2026-06-11
---

## Result

Added explicit admin business-layer RBAC and read-only admin evidence endpoints backed by existing persistence tables.

## Changes

- Added explicit admin role-and-scope policy evaluation for admin resources.
- Added read-only admin endpoints for users, security events, tool executions, and aggregate metrics.
- Added admin evidence repository and service shaping/pagination.
- Added unit tests for admin policy/service and DB-backed integration tests for later verification.

## Verification

- `cd backend && python -m pytest tests/unit/test_admin_policy.py tests/unit/test_admin_evidence_service.py tests/security/test_unknown_policy_state.py -q --tb=short`
- `cd backend && python -m pytest tests/security/test_search_capability_token.py tests/integration/search/test_search_capability_check.py tests/integration/search/test_search_worker_contract.py tests/integration/search/test_search_budgets.py tests/security/test_search_prompt_injection.py tests/security/test_search_secret_leakage.py tests/security/test_search_retention_allowlist.py -q --tb=short`
- `cd backend && python -m pytest tests/unit/test_config.py tests/integration/test_provider_status.py tests/security/test_jwt_profile.py -q --tb=short`
- `cd backend && python -m compileall app tests`

## Notes

- New DB-backed admin route tests were added but not executed in this session because the PostgreSQL test host `postgres-test` is not available locally.
- No git commit was created because local git identity is still not configured in this environment.
