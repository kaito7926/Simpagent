---
phase: 03-policy-controlled-google-search
plan: "08"
subsystem: testing-validation
tags: [search, firecrawl, gemini, smoke-tests, validation, docker-compose]

requires:
  - phase: 03-policy-controlled-google-search
    provides: Firecrawl backend runtime, admin provider override, and provider-honest frontend behavior from plans 03-05 through 03-07
provides:
  - Dual-provider smoke coverage for Gemini default, Firecrawl override, Firecrawl-unconfigured, and override-clear flows
  - Phase 03 validation commands synchronized with the provider matrix and SRCH-05 retention allowlist suite
  - Firecrawl environment passthrough for assembled and test Compose runs
affects: [phase-03-validation, smoke-tests, docker-compose, future-search-verification]

tech-stack:
  added: []
  patterns:
    - Provider-aware smoke assertions use trusted backend provider metadata instead of Google-only assumptions
    - Assembled smoke follows runtime readiness: Firecrawl success when configured, fail-closed unconfigured behavior otherwise

key-files:
  created:
    - .planning/phases/03-policy-controlled-google-search/03-08-SUMMARY.md
  modified:
    - backend/tests/smoke/test_google_search_flow.py
    - backend/tests/smoke/test_admin_flow.py
    - backend/tests/smoke/_helpers.py
    - backend/app/services/chat_turns.py
    - compose.yaml
    - compose.test.yaml
    - .env.example
    - .planning/phases/03-policy-controlled-google-search/03-VALIDATION.md

key-decisions:
  - "Keep provider identity as metadata behind the existing google_search/tool:websearch turn mode."
  - "Let assembled smoke assert Firecrawl grounded behavior only when credentials are configured, and assert search_unavailable when Firecrawl is selected without credentials."
  - "Expose Firecrawl credentials through Compose environment passthrough so smoke success can be proven without source changes."

patterns-established:
  - "Smoke search contract checks provider-specific grounding semantics: Gemini may be google_grounded; Firecrawl must not claim Google grounding."
  - "Provider override smoke tests clear runtime override state in cleanup paths."

requirements-completed: [AUTHZ-04, AGNT-06, SRCH-04, SRCH-05, SRCH-06, SRCH-07]

duration: 17 min
completed: 2026-06-23
---

# Phase 03 Plan 08: Provider Matrix Smoke and Validation Summary

**Dual-provider search smoke coverage with Gemini/Firecrawl validation commands and SRCH-05 retention proof kept in closeout evidence.**

## Performance

- **Duration:** 17 min
- **Started:** 2026-06-23T07:44:38Z
- **Completed:** 2026-06-23T08:01:12Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- Added assembled smoke coverage for Gemini default search, Firecrawl admin override search, Firecrawl-unconfigured `search_unavailable`, and provider override clear-to-default.
- Updated admin smoke to cover the current orchestration surface and provider override set/clear behavior through public admin routes.
- Updated `03-VALIDATION.md` so quick/full/smoke commands explicitly include the provider matrix and `test_search_retention_allowlist.py` for SRCH-05.
- Added Firecrawl env passthrough to Compose and `.env.example` so configured smoke can prove Firecrawl success without code changes.

## Task Commits

1. **Task 1: Add RED assembled smoke expectations for the dual-provider matrix** - `5028140` (test)
2. **Task 2: Update smoke suites and validation commands for provider-matrix closeout** - `58d7ed4` (feat)

## Files Created/Modified

- `backend/tests/smoke/test_google_search_flow.py` - Adds provider matrix smoke for Gemini default, Firecrawl override, Firecrawl-unconfigured, and override clear.
- `backend/tests/smoke/test_admin_flow.py` - Updates admin orchestration smoke to current guardrail/provider contract and covers provider override set/clear.
- `backend/tests/smoke/_helpers.py` - Adds provider-aware search assertions and bounded login retry for gateway rate limits.
- `backend/app/services/chat_turns.py` - Preserves already-ready injected search workers when no admin override is active.
- `compose.yaml` - Passes Firecrawl configuration to the assembled backend and production profile.
- `compose.test.yaml` - Passes Firecrawl configuration to backend-test.
- `.env.example` - Documents Firecrawl key/base variables.
- `.planning/phases/03-policy-controlled-google-search/03-VALIDATION.md` - Aligns quick/full/smoke commands with provider matrix and SRCH-05 retention proof.

## Verification

- `docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/smoke/test_google_search_flow.py tests/smoke/test_admin_flow.py -x` -> `4 skipped` after Task 1 because smoke requires `SIMPAGENT_RUN_SMOKE=true`.
- `docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/integration/search/test_search_persistence.py tests/security/test_search_retention_allowlist.py -x` -> `6 passed`.
- `docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/integration/search/test_search_capability_check.py tests/integration/search/test_search_persistence.py tests/security/test_search_retention_allowlist.py tests/integration/admin/test_admin_write.py tests/smoke/test_google_search_flow.py tests/smoke/test_admin_flow.py -x` -> `21 passed, 3 skipped`.
- `cd frontend && npm test -- tests/search-session.test.ts tests/search-rendering.test.tsx tests/admin-evidence.test.tsx` -> `22 passed`.
- `cd frontend && npm run typecheck` -> passed.
- `docker compose up --build --wait` -> topology healthy.
- `docker compose run --rm -e SIMPAGENT_RUN_SMOKE=true backend python -m pytest -q tests/smoke/test_google_search_flow.py tests/smoke/test_admin_flow.py -x` -> `3 passed`.
- `rg -n "Gemini|Firecrawl|test_search_retention_allowlist|test_google_search_flow|test_admin_flow|websearch_provider" ...` -> validation and smoke files reference the same provider matrix and SRCH-05 retention suite.

## Decisions Made

- Firecrawl smoke assertions are readiness-sensitive: configured Firecrawl must return grounded provider-honest evidence, while unconfigured Firecrawl must return `search_unavailable` without Gemini fallback.
- Provider override smoke assertions were folded into the existing admin smoke flow to avoid exceeding Kong's local login rate limit during assembled tests.
- `chat_turns.py` preserves injected ready search workers when no runtime override exists, keeping integration and smoke harnesses from being overwritten by environment-derived unconfigured status.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added Firecrawl Compose env passthrough**
- **Found during:** Task 2
- **Issue:** Firecrawl credentials existed in backend settings but were not passed through Compose, so assembled Firecrawl success smoke could not be configured.
- **Fix:** Added Firecrawl key, key-file, and API base passthrough to `compose.yaml`, `compose.test.yaml`, and `.env.example`.
- **Files modified:** `compose.yaml`, `compose.test.yaml`, `.env.example`
- **Verification:** Full Task 2 command passed; assembled smoke passed with unconfigured fail-closed branch.
- **Committed in:** `58d7ed4`

**2. [Rule 1 - Bug] Preserved injected ready search workers during runtime refresh**
- **Found during:** Task 2 verification
- **Issue:** `_refresh_search_runtime()` overwrote test-injected ready search workers with environment-derived `unconfigured` status when no admin override existed.
- **Fix:** Return early when no override is active and the service already has a ready valid search worker/provider.
- **Files modified:** `backend/app/services/chat_turns.py`
- **Verification:** `test_search_persistence.py` and `test_search_retention_allowlist.py` passed.
- **Committed in:** `58d7ed4`

**3. [Rule 1 - Bug] Updated stale admin smoke orchestration assertions**
- **Found during:** Assembled smoke verification
- **Issue:** Smoke expected removed `trusted_supervisor_enabled` fields/routes instead of the current guardrail/provider orchestration contract.
- **Fix:** Asserted the current orchestration response keys and used cleanup-safe guardrail/provider override writes.
- **Files modified:** `backend/tests/smoke/test_admin_flow.py`
- **Verification:** Assembled smoke passed.
- **Committed in:** `58d7ed4`

**4. [Rule 3 - Blocking] Made smoke login resilient to gateway rate-limit buckets**
- **Found during:** Assembled smoke verification
- **Issue:** Sequential smoke auth calls could hit Kong's local login rate limit and fail unrelated provider assertions.
- **Fix:** Added bounded retry on `429` in the smoke login helper and folded provider override assertions into the existing admin smoke flow to reduce auth calls.
- **Files modified:** `backend/tests/smoke/_helpers.py`, `backend/tests/smoke/test_admin_flow.py`
- **Verification:** Assembled smoke passed after restarting Kong's local test counter.
- **Committed in:** `58d7ed4`

---

**Total deviations:** 4 auto-fixed (2 bugs, 1 missing critical functionality, 1 blocking issue)
**Impact on plan:** All fixes were required to make the provider-matrix smoke and validation evidence executable against the assembled topology. No unrelated user-facing feature scope was added.

## Issues Encountered

- The literal Task 1 smoke command skipped tests because smoke execution is gated by `SIMPAGENT_RUN_SMOKE`; meaningful assembled execution was verified later with the updated Compose smoke command.
- Local Firecrawl credentials were not configured, so assembled smoke proved the Firecrawl-selected `search_unavailable` branch. The validation contract now states that Firecrawl success smoke requires `FIRECRAWL_API_KEY` or `SIMPAGENT_FIRECRAWL_API_KEY_FILE`.

## Known Stubs

- `backend/app/services/chat_turns.py` contains the pre-existing `DIRECT_CHAT_PLACEHOLDER`/`_append_direct_chat_placeholder` path for direct chat in this branch. This was not introduced by this plan and does not affect the provider-matrix search closeout.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: external-provider-config | `compose.yaml`, `compose.test.yaml`, `.env.example` | Firecrawl credential/base-url passthrough was added so the reviewed provider boundary can be exercised in assembled smoke; no secret values were added. |

## User Setup Required

None - no new mandatory external service configuration required. Optional Firecrawl success smoke requires a configured Firecrawl API key.

## Next Phase Readiness

Phase 03 enhancement pack is ready for verification closeout. The historical Phase 03 verification debt remains visible, but 03-08 closes the Gemini/Firecrawl smoke and validation matrix requested by the enhancement plans.

## Self-Check: PASSED

- Found `.planning/phases/03-policy-controlled-google-search/03-08-SUMMARY.md`.
- Found `.planning/phases/03-policy-controlled-google-search/03-08-PLAN.md`.
- Found task commit `5028140`.
- Found task commit `58d7ed4`.

---
*Phase: 03-policy-controlled-google-search*
*Completed: 2026-06-23*
