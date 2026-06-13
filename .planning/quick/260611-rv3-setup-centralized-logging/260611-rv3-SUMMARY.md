---
status: complete
quick_task: 260611-rv3
description: setup centralized logging with Grafana Loki and JSON logs
completed: 2026-06-11
---

## Result

Added a local centralized logging stack based on Grafana Loki and Promtail, plus structured JSON logging for FastAPI request access and security-relevant events.

## Changes

- Added `backend/app/core/logging.py` and wired it into `app.main` for JSON stdout/file logs with correlation-aware access logging.
- Added structured log emission for persisted `security_event` and `tool_execution` writes.
- Added local observability configs under `observability/` for Loki, Promtail, and Grafana datasource provisioning.
- Extended `compose.yaml` with `loki`, `promtail`, and `grafana` services plus shared log volumes for backend and Kong.
- Disabled duplicate Uvicorn access logs in the backend container and documented local Grafana usage in `README.md` and `.env.example`.
- Added `backend/tests/unit/test_logging.py` to lock JSON formatter redaction and correlation behavior.

## Verification

- `cd backend && python -m pytest tests/unit/test_logging.py tests/integration/auth tests/security/test_jwt_profile.py tests/security/test_principal_fail_closed.py tests/security/test_unknown_policy_state.py -q --tb=short`
- `cd backend && python -m pytest tests/unit/test_admin_policy.py tests/unit/test_admin_evidence_service.py tests/integration/admin/test_admin_evidence.py tests/integration/admin/test_admin_write.py tests/integration/search/test_search_authz.py tests/integration/search/test_turn_routing.py tests/integration/search/test_grounding_contract.py tests/integration/search/test_search_failure_states.py tests/integration/search/test_search_persistence.py tests/integration/search/test_search_budgets.py tests/integration/search/test_search_capability_check.py tests/integration/search/test_search_worker_contract.py tests/security/test_search_guardrails.py tests/security/test_search_prompt_injection.py tests/security/test_search_retention_allowlist.py tests/security/test_search_secret_leakage.py tests/security/test_search_capability_token.py -q --tb=short`

## Notes

- `docker compose config -q` could not be executed in this terminal session because `docker` is not available in `PATH`.
- The current Compose stack centralizes backend JSON logs and Kong file logs; Grafana is provisioned automatically with a Loki datasource on startup.
