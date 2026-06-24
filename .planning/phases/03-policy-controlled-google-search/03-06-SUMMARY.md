---
phase: 03-policy-controlled-google-search
plan: "06"
subsystem: backend-admin-search
tags: [fastapi, sqlalchemy, alembic, admin, websearch-provider, pytest]
requires:
  - phase: 03-05
    provides: fail-closed gemini/firecrawl provider runtime and Firecrawl retention coverage
provides:
  - persisted admin runtime websearch provider override
  - admin orchestration contract for default, override, effective provider, and readiness
  - request-time effective-provider resolution for search readiness and execution
affects: [phase-03-search, admin-orchestration, provider-status, chat-turns, frontend-provider-control]
tech-stack:
  added: []
  patterns:
    - nullable runtime settings value with allowlisted semantics
    - admin orchestration set/clear endpoint with correlated evidence
    - request-time provider worker resolution from persisted override
key-files:
  created:
    - backend/alembic/versions/0005_websearch_provider_runtime_override.py
  modified:
    - backend/app/models/domain.py
    - backend/app/db/repositories/agent_settings.py
    - backend/app/schemas/admin.py
    - backend/app/services/admin_evidence.py
    - backend/app/api/routes/admin.py
    - backend/app/core/provider_status.py
    - backend/app/services/chat_turns.py
    - backend/app/ai/search_worker/service.py
    - backend/app/api/routes/chat.py
    - backend/app/api/routes/conversations.py
    - backend/app/agent/coordinator.py
    - backend/tests/unit/test_admin_evidence_service.py
    - backend/tests/integration/admin/test_admin_write.py
    - backend/tests/integration/search/test_search_capability_check.py
key-decisions:
  - "Keep the provider override in the existing agent_runtime_settings table as nullable value data instead of creating a new settings table."
  - "Resolve the effective websearch provider at request time so admin reads, readiness, and live execution share the same contract."
requirements-completed: [AGNT-06, SRCH-02, SRCH-06, SRCH-07]
duration: 11 min
completed: 2026-06-23
---

# Phase 03 Plan 06: Provider Override Runtime Summary

**Admin-owned runtime websearch provider override with persisted clear semantics and request-time Gemini/Firecrawl execution resolution.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-06-23T06:42:28Z
- **Completed:** 2026-06-23T06:53:21Z
- **Tasks:** 3/3
- **Files modified:** 15

## Accomplishments

- Added nullable persisted `websearch_provider_override` storage on the existing `agent_runtime_settings` table, constrained to `gemini`, `firecrawl`, or `NULL`.
- Extended admin orchestration read/write responses with `websearch_provider_default`, `websearch_provider_override`, `websearch_provider_effective`, and `websearch_provider_readiness`.
- Added admin set and clear operations with `admin:write` enforcement, invalid-provider rejection, non-admin denial, and correlated security evidence.
- Wired live chat/search execution to resolve the persisted override per request, build/select the matching worker, and return to the environment default after clear.

## Task Commits

1. **Task 1 RED: Provider override contract tests** - `03a1628` (test)
2. **Task 2 GREEN: Admin provider override contract** - `a377775` (feat)
3. **Task 3 RED: Runtime override execution test** - `ec99fa1` (test)
4. **Task 3 GREEN: Live execution honors override** - `dcbccbd` (feat)

## Files Created/Modified

- `backend/alembic/versions/0005_websearch_provider_runtime_override.py` - Adds the nullable provider override value column and allowlist check.
- `backend/app/models/domain.py` - Models the runtime setting value field and database check constraint.
- `backend/app/db/repositories/agent_settings.py` - Adds typed get/set/clear operations for provider overrides.
- `backend/app/schemas/admin.py` - Adds orchestration provider fields and override request schema.
- `backend/app/services/admin_evidence.py` - Enforces admin RBAC, validates provider values, emits set/clear evidence, and returns coherent orchestration state.
- `backend/app/api/routes/admin.py` - Exposes the admin-only provider override endpoint and provider-aware orchestration responses.
- `backend/app/core/provider_status.py` - Resolves effective provider from runtime override before environment default.
- `backend/app/services/chat_turns.py`, `backend/app/agent/coordinator.py`, and chat routes - Refresh provider readiness and worker selection at request time.
- `backend/tests/unit/test_admin_evidence_service.py`, `backend/tests/integration/admin/test_admin_write.py`, and `backend/tests/integration/search/test_search_capability_check.py` - Cover read, write, deny, clear, evidence, and runtime execution behavior.

## Verification

- RED gate after rebuild: `docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/unit/test_admin_evidence_service.py tests/integration/admin/test_admin_write.py tests/integration/search/test_search_capability_check.py -x` - failed as expected on missing `websearch_provider_default`.
- Task 2: `docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/unit/test_admin_evidence_service.py tests/integration/admin/test_admin_write.py -x` - `22 passed`.
- Task 3 and plan-level: `docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/unit/test_admin_evidence_service.py tests/integration/admin/test_admin_write.py tests/integration/search/test_search_capability_check.py -x` - `31 passed`.

## Decisions Made

- Runtime override persistence reuses the established `agent_runtime_settings` ownership and audit pattern rather than adding another configuration table.
- Live execution does not trust startup-only `app.state.search_provider`; it refreshes the effective provider from the repository for each search turn.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Shortened Alembic revision id**
- **Found during:** Task 2
- **Issue:** The first revision id exceeded the existing `alembic_version.version_num` length and failed migration with `value too long for type character varying(32)`.
- **Fix:** Changed the revision id to `0005_websearch_override` while keeping the requested migration filename.
- **Files modified:** `backend/alembic/versions/0005_websearch_provider_runtime_override.py`
- **Verification:** Task 2 integration verification passed after rebuild.
- **Committed in:** `a377775`

**2. [Rule 2 - Missing Critical] Returned provider contract from guardrail toggle responses**
- **Found during:** Task 2
- **Issue:** The guardrail write response initially risked returning hardcoded provider defaults, which would let the orchestration surface drift from persisted override state.
- **Fix:** Reused the current provider override/default/readiness response fields on guardrail writes.
- **Files modified:** `backend/app/services/admin_evidence.py`, `backend/app/api/routes/admin.py`
- **Verification:** Task 2 verification passed with orchestration response assertions.
- **Committed in:** `a377775`

**3. [Rule 2 - Missing Critical] Wired request-time provider override into live execution**
- **Found during:** Task 3
- **Issue:** Startup `app.state.search_worker` could keep using the environment provider even after an admin override changed the effective provider.
- **Fix:** Added request-time provider refresh in `ChatTurnsService` and `ChatCoordinator`, plus provider-aware worker construction.
- **Files modified:** `backend/app/services/chat_turns.py`, `backend/app/agent/coordinator.py`, `backend/app/ai/search_worker/service.py`, `backend/app/api/routes/chat.py`, `backend/app/api/routes/conversations.py`
- **Verification:** Task 3 verification passed, including override-to-Firecrawl and clear-to-Gemini execution.
- **Committed in:** `dcbccbd`

---

**Total deviations:** 3 auto-fixed (1 Rule 1, 2 Rule 2).
**Impact on plan:** All fixes were required for correctness and security. No new public tool surface or dependency was added.

## Issues Encountered

- The first RED run used a stale `backend-test` image and passed before the new tests were copied in. Rebuilding `backend-test` produced the expected RED failure.
- Docker Compose reported unrelated orphan containers from the local full stack during test runs. They did not affect the backend-test verification.

## Known Stubs

- `backend/app/services/chat_turns.py` still contains the pre-existing direct-chat placeholder path. It was not introduced by this plan and does not block the provider override goal.

## User Setup Required

None - no new external service configuration is required beyond the existing Firecrawl setup from `03-05`.

## Next Phase Readiness

Ready for `03-07`: frontend/admin UI work can consume the backend orchestration fields and render provider-honest Gemini/Firecrawl controls.

## Self-Check: PASSED

- Verified created file exists: `backend/alembic/versions/0005_websearch_provider_runtime_override.py`.
- Verified task commits exist: `03a1628`, `a377775`, `ec99fa1`, and `dcbccbd`.
- Verified plan-level command passed: `31 passed`.

---
*Phase: 03-policy-controlled-google-search*
*Completed: 2026-06-23*
