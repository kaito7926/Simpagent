---
status: complete
quick_task: 260611-rv5
description: add full topology smoke coverage for admin search and logging flows
completed: 2026-06-12
---

## Result

Added full-topology smoke coverage for admin evidence, search activity, and centralized logging ingestion through Kong and Loki.

## Changes

- Added `backend/tests/smoke/_helpers.py` for shared public-stack auth helpers, search submission, admin user lookup, and Loki polling.
- Added `backend/tests/smoke/test_admin_flow.py` to verify admin evidence visibility, non-admin denial, search evidence visibility, and stale-token behavior after an admin role change.
- Added `backend/tests/smoke/test_logging_flow.py` to verify backend JSON access/tool/security logs and Kong access logs arrive in Loki after admin and search requests.

## Verification

- `cd backend && python -m pytest tests/smoke/test_admin_flow.py tests/smoke/test_logging_flow.py -q --tb=short`
- `cd backend && python -m pytest tests/smoke -q --tb=short`
- `$env:SIMPAGENT_DATABASE_URL='postgresql+psycopg://postgres:postgres@127.0.0.1:55432/simpagent_test'; python -m pytest tests/unit/test_logging.py tests/integration/admin/test_admin_evidence.py tests/integration/admin/test_admin_write.py -q --tb=short`

## Notes

- Smoke tests remain guarded by `SIMPAGENT_RUN_SMOKE=true`, so in this local non-Compose shell they were verified at collection/skip level only.
- Full assembled-topology execution still needs `docker compose up --build --wait` followed by running the smoke suite from the main `backend` service container.
