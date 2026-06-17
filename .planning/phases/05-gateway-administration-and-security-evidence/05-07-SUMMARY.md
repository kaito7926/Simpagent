---
phase: 05-gateway-administration-and-security-evidence
plan: "07"
subsystem: admin-evidence-ui
tags: [nextjs, react, fastapi, admin, gateway-evidence, authorization]

requires:
  - phase: 05-gateway-administration-and-security-evidence
    provides: "05-04 admin Overview/Orchestration and 05-06 redacted gateway evidence service contracts"
provides:
  - "Shared-shell admin pages for metrics, users, security events, tool executions, gateway evidence, and orchestration"
  - "Reusable bounded evidence table, sanitized detail drawer, and explicit state panel components"
  - "Gateway evidence route exposed through the backend admin:read authorization path"
affects: [admin-ui, gateway-evidence, observability, authorization]

tech-stack:
  added: []
  patterns:
    - "Frontend admin API wrappers use AuthSessionController.authorizedJson for every protected admin call."
    - "Admin evidence tables map backend page contracts into bounded EvidenceRow data before rendering."
    - "Evidence detail drawers render backend-provided snippets and allowlisted fields only."

key-files:
  created:
    - frontend/components/admin/EvidenceTable.tsx
    - frontend/components/admin/EvidenceDetailDrawer.tsx
    - frontend/components/admin/StatePanel.tsx
  modified:
    - backend/app/api/routes/admin.py
    - backend/tests/smoke/test_admin_flow.py
    - frontend/lib/admin-api.ts
    - frontend/components/chat/ChatWorkspace.tsx
    - frontend/tests/admin-evidence.test.tsx

key-decisions:
  - "Gateway evidence is exposed as `/api/admin/gateway-evidence` through the existing AdminEvidenceService admin:read gate."
  - "The shared shell fetches users, security events, tool executions, gateway evidence, metrics, and orchestration through backend-authoritative admin wrappers."
  - "Detail drawers intentionally avoid raw JSON viewers and render only row fields plus backend-sanitized snippets."

patterns-established:
  - "EvidenceTable: one reusable desktop table/mobile card surface for bounded admin pages."
  - "EvidenceDetailDrawer: sanitized detail inspection surface shared by admin evidence rows."
  - "StatePanel: explicit loading, empty, forbidden, and error states for admin surfaces."

requirements-completed: [AUTHZ-02, OBS-03, OBS-05, OBS-06]

duration: 18 min
completed: 2026-06-16
---

# Phase 05 Plan 07: Admin Evidence Surfaces Summary

**Shared-shell admin evidence now renders all six Phase 5 surfaces from backend-authorized, redacted, bounded admin contracts.**

## Performance

- **Duration:** 18 min
- **Started:** 2026-06-16T04:59:34Z
- **Completed:** 2026-06-16T05:17:24Z
- **Tasks:** 3 completed
- **Files modified:** 8

## Accomplishments

- Added RED coverage for all six admin navigation targets, paged admin wrappers, gateway route exposure, sanitized drawers, explicit denied states, and read/write admin distinctions.
- Created reusable `EvidenceTable`, `EvidenceDetailDrawer`, and `StatePanel` components for bounded admin evidence pages.
- Exposed `/api/admin/gateway-evidence` through the same backend `admin:read` authorization and denial-evidence path as other admin reads.
- Wired Users, Security events, Tool executions, and Gateway evidence into `ChatWorkspace` with backend-paged data, safe empty states, and `Xem chi tiết` detail actions.

## Task Commits

Each task was committed atomically:

1. **Task 1: Write RED frontend and smoke tests for all six admin surfaces, gateway route exposure, and backend-enforced denied states** - `5462dd4` (test)
2. **Task 2: Implement reusable evidence table and drawer components from the UI contract** - `3fa7ca9` (feat)
3. **Task 3: Expose gateway evidence in the admin API and wire all six admin surfaces into the shared shell with AUTHZ-02 visibility** - `e422cac` (feat)

**Plan metadata:** committed separately after this summary and state updates.

## Files Created/Modified

- `frontend/components/admin/EvidenceTable.tsx` - Bounded desktop table and mobile card rendering for admin evidence pages.
- `frontend/components/admin/EvidenceDetailDrawer.tsx` - Sanitized detail inspection surface using row fields and backend snippets only.
- `frontend/components/admin/StatePanel.tsx` - Explicit loading, empty, forbidden, and error state component.
- `frontend/lib/admin-api.ts` - Typed wrappers for users, security events, tool executions, gateway evidence, metrics, orchestration, and user access writes.
- `frontend/components/chat/ChatWorkspace.tsx` - Real shared-shell admin pages for Users, Security events, Tool executions, Gateway evidence, Overview, and Orchestration.
- `frontend/tests/admin-evidence.test.tsx` - Frontend RED/GREEN coverage for wrappers, surfaces, drawer snippets, denied states, and read/write distinctions.
- `backend/app/api/routes/admin.py` - Gateway evidence route exposed behind `admin:read`.
- `backend/tests/smoke/test_admin_flow.py` - Smoke contract extended for gateway evidence allow and deny behavior.

## Decisions Made

- Gateway evidence route exposure stays thin: FastAPI route handlers delegate to `AdminEvidenceService`, preserving the existing admin authorization and denial-recording path.
- The frontend maps backend response shapes to a local `EvidenceRow` view model instead of passing raw metadata objects into reusable components.
- Drawer details remain intentionally bounded and do not include raw JSON, raw metadata dumps, tokens, cookies, passwords, API keys, provider payloads, or full prompts.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Normalized frontend verification commands for this npm environment**
- **Found during:** Task 1 and final verification
- **Issue:** The planned command path `frontend/tests/...` is resolved from the `frontend/` package when using `npm --prefix frontend`, which would point to `frontend/frontend/tests/...`.
- **Fix:** Used the equivalent repository command form `npm --prefix frontend test -- tests/...`; used `npm --prefix frontend run typecheck` for the configured typecheck script.
- **Files modified:** None
- **Verification:** `npm --prefix frontend test -- tests/admin-evidence.test.tsx tests/chat-workspace.test.ts` and `npm --prefix frontend run typecheck` passed.
- **Committed in:** N/A

**2. [Rule 3 - Blocking] Rebuilt backend image before Docker route verification**
- **Found during:** Task 3
- **Issue:** `docker compose run --rm backend ...` used the previously built backend image and did not include the newly added gateway evidence route.
- **Fix:** Ran `docker compose build backend`, then reran route/import and backend test verification against the rebuilt image.
- **Files modified:** None
- **Verification:** Route check returned `['/api/admin/gateway-evidence']`; backend admin integration/unit tests passed.
- **Committed in:** N/A

**3. [Rule 3 - Blocking] Split Task 2 verification around downstream Task 3 assertions**
- **Found during:** Task 2
- **Issue:** The full `admin-evidence.test.tsx` file included Task 3 wrapper and workspace assertions from the RED gate, so it could not fully pass after only the component primitives existed.
- **Fix:** Verified the component contract inside the full test output after Task 2, then completed the remaining wrapper/workspace assertions in Task 3 and reran the full suite.
- **Files modified:** None beyond planned implementation files.
- **Verification:** Full frontend admin evidence suite passed after Task 3.
- **Committed in:** `3fa7ca9`, completed by `e422cac`

---

**Total deviations:** 3 auto-handled (3 blocking)
**Impact on plan:** All deviations were verification-flow or container-staleness issues. The shipped behavior stayed within the planned admin evidence route and frontend surface scope.

## Issues Encountered

- The assembled-stack smoke test skipped locally because `tests/smoke/_helpers.py` requires the smoke topology gate. The route exists in the rebuilt backend image, and admin integration/unit tests passed.
- Docker Compose reported an existing orphan `simpagent-postgres-test-1` container warning during backend verification; it did not affect test results.

## Verification

- `npm --prefix frontend test -- tests/admin-evidence.test.tsx` - passed, 7 tests.
- `npm --prefix frontend test -- tests/chat-workspace.test.ts` - passed, 8 tests.
- `npm --prefix frontend test -- tests/admin-evidence.test.tsx tests/chat-workspace.test.ts` - passed, 15 tests.
- `npm --prefix frontend run typecheck` - passed.
- `docker compose build backend` - passed.
- `docker compose run --rm backend python -c "from app.api.routes import admin; print([route.path for route in admin.router.routes if 'gateway-evidence' in route.path])"` - passed, route found.
- `docker compose run --rm backend python -m pytest tests/smoke/test_admin_flow.py -q` - skipped, smoke topology gate disabled.
- `docker compose run --rm backend python -m pytest tests/integration/admin/test_admin_evidence.py tests/unit/test_admin_evidence_service.py -q` - passed, 17 tests.

## Authentication Gates

None.

## Known Stubs

None. Stub scan hits were default parameters, nullable state sentinels, and negative test assertions that ensure placeholder copy is absent.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for Phase 05 Plan 08/09 follow-up work. The admin shell can now consume bounded backend evidence for all required admin surfaces, and gateway evidence route exposure is available for later production-profile and auth-shell verification work.

## Self-Check: PASSED

- Summary file created at `.planning/phases/05-gateway-administration-and-security-evidence/05-07-SUMMARY.md`.
- Created files found: `frontend/components/admin/EvidenceTable.tsx`, `frontend/components/admin/EvidenceDetailDrawer.tsx`, `frontend/components/admin/StatePanel.tsx`.
- Task commits found: `5462dd4`, `3fa7ca9`, `e422cac`.
- Final frontend verification and backend route/service verification completed as documented.

---
*Phase: 05-gateway-administration-and-security-evidence*
*Completed: 2026-06-16*
