---
phase: 03-policy-controlled-google-search
plan: "05"
subsystem: backend-search
tags: [fastapi, firecrawl, google-search, search-provider, retention, pytest]
requires:
  - phase: 03-02
    provides: dedicated Gemini search worker, capability token boundary, search readiness checks
  - phase: 03-04
    provides: search persistence, failure-state hardening, retention allowlist tests
provides:
  - fail-closed websearch provider resolver for gemini and firecrawl
  - Firecrawl Cloud HTTPX boundary behind existing tool:websearch execution
  - provider-honest search metadata with Firecrawl retention and no-click-tracking coverage
affects: [phase-03-search, provider-status, chat-turns, admin-orchestration, frontend-provider-honesty]
tech-stack:
  added: []
  patterns:
    - selected-provider worker factory
    - source URI retention sanitizer
    - provider field in normalized search envelope
key-files:
  created:
    - backend/app/ai/search_worker/firecrawl_client.py
    - .planning/phases/03-policy-controlled-google-search/03-USER-SETUP.md
  modified:
    - backend/app/core/config.py
    - backend/app/core/provider_status.py
    - backend/app/ai/search_worker/grounding.py
    - backend/app/ai/search_worker/service.py
    - backend/app/services/chat_turns.py
    - backend/tests/security/test_search_retention_allowlist.py
key-decisions:
  - "Keep Firecrawl behind the existing public google_search turn mode and tool:websearch gate; provider identity is metadata, not a new client tool."
  - "Use HTTPX directly for Firecrawl Cloud instead of adding a Firecrawl SDK."
requirements-completed: [AUTHZ-04, AUTHZ-07, AGNT-01, AGNT-02, AGNT-03, AGNT-04, AGNT-05, AGNT-06, AGNT-07, SRCH-02, SRCH-03, SRCH-05, SRCH-06, SRCH-07, SRCH-08]
duration: 14 min
completed: 2026-06-23
---

# Phase 03 Plan 05: Firecrawl Provider Runtime Summary

**Fail-closed Gemini/Firecrawl backend websearch provider boundary with Firecrawl retention sanitization and no hidden fallback.**

## Performance

- **Duration:** 14 min
- **Started:** 2026-06-23T06:22:19Z
- **Completed:** 2026-06-23T06:36:05Z
- **Tasks:** 3/3
- **Files modified:** 20

## Accomplishments

- Added `SIMPAGENT_WEBSEARCH_PROVIDER` allowlist resolution for `gemini | firecrawl`; invalid providers resolve to `invalid_provider`.
- Added `FirecrawlSearchWorkerService` and `FirecrawlSearchClient` using the existing HTTPX dependency and the existing capability-token worker contract.
- Preserved D-11: selecting Firecrawl without `FIRECRAWL_API_KEY` returns `search_unavailable` and never falls back to Gemini.
- Extended normalized search metadata with provider identity while retaining the existing `tool:websearch`, one-tool-per-turn, and capability-token boundary.
- Added Firecrawl retention tests for allowed fields, tracking-query stripping, redirect-wrapper refusal, and no raw provider payload persistence.

## Task Commits

1. **Task 1: Lock provider matrix and Firecrawl SRCH-05 RED tests** - `3a544fb` (test)
2. **Task 2: Implement allowlisted resolver and Firecrawl runtime boundary** - `d0eaf01` (feat)
3. **Task 3 RED: Add stricter Firecrawl retention sanitizer test** - `ba34196` (test)
4. **Task 3 GREEN: Enforce Firecrawl source retention sanitization** - `48a86aa` (fix)

## Files Created/Modified

- `backend/app/ai/search_worker/firecrawl_client.py` - Firecrawl Cloud `/v2/search` HTTPX boundary with typed normalization.
- `backend/app/core/config.py` - Firecrawl API key/base settings and provider selection configuration.
- `backend/app/core/provider_status.py` - `gemini | firecrawl` resolver and provider-specific readiness.
- `backend/app/ai/search_worker/service.py` - Firecrawl worker service and selected-provider worker factory.
- `backend/app/ai/search_worker/grounding.py` - shared public URI validation, tracking-query stripping, and redirect-wrapper refusal.
- `backend/app/services/chat_turns.py` - provider metadata persistence and Firecrawl grounded-result handling.
- `backend/app/schemas/search.py` - provider field in worker and turn result envelopes.
- `backend/tests/integration/search/*` and `backend/tests/security/*` - provider, failure, guardrail, persistence, and retention regression coverage.
- `.planning/phases/03-policy-controlled-google-search/03-USER-SETUP.md` - Firecrawl dashboard/API-key setup instructions.

## Verification

- `docker compose -f compose.test.yaml build backend-test` - passed.
- `docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/integration/search/test_search_capability_check.py tests/integration/search/test_search_failure_states.py tests/integration/search/test_search_persistence.py tests/security/test_search_guardrails.py -x` - `17 passed`.
- `docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/integration/search/test_search_persistence.py tests/security/test_search_retention_allowlist.py -x` - `6 passed`.

## Decisions Made

- Firecrawl does not introduce a second browser-visible tool mode. The public turn remains `google_search` for compatibility, and provider honesty is carried in `search.provider`.
- Firecrawl success can be `grounded` without setting `google_grounded=true`; Google-specific UI should use the provider field in later plans.
- Firecrawl source links are refused when they look like redirect wrappers and are stripped of common tracking query keys before persistence.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Wired adjacent startup, route, and coordinator provider state**
- **Found during:** Task 2
- **Issue:** The plan listed core config/status and worker files, but selected-provider behavior also had to reach FastAPI startup, route injection, and the legacy chat coordinator path. Without that wiring, Firecrawl readiness could be computed but not reliably enforced at execution.
- **Fix:** Updated `backend/app/main.py`, `backend/app/api/routes/chat.py`, `backend/app/api/routes/conversations.py`, `backend/app/agent/coordinator.py`, `backend/app/schemas/search.py`, and `backend/app/models/domain.py`.
- **Verification:** Task 2 verification command passed with provider allowlist, Firecrawl configured, and Firecrawl-without-key no-fallback tests.
- **Committed in:** `d0eaf01`

---

**Total deviations:** 1 auto-fixed (Rule 2).
**Impact on plan:** Required for correctness and fail-closed behavior. No new public tool surface or dependency was added.

## Issues Encountered

- Initial Docker RED run reused a stale backend-test image; rebuilding the image produced the expected RED failure on missing provider resolver.
- Local Python dependencies were not installed, so verification used the Compose backend-test image as required by the plan.

## Known Stubs

- `backend/app/services/chat_turns.py` contains the pre-existing `DIRECT_CHAT_PLACEHOLDER` path for ordinary direct chat in this branch. It was not introduced by this plan and does not block the Firecrawl websearch goal.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: external-provider | backend/app/ai/search_worker/firecrawl_client.py | New outbound Firecrawl Cloud `/v2/search` boundary protected by provider allowlist, API-key configuration, public-URI filtering, and no arbitrary user URL fetch path. |
| threat_flag: retention | backend/app/ai/search_worker/grounding.py | Source-link sanitizer strips tracking query parameters and refuses redirect wrappers before provider metadata can persist. |

## User Setup Required

External Firecrawl configuration is required only when operators choose the Firecrawl provider. See `.planning/phases/03-policy-controlled-google-search/03-USER-SETUP.md`.

## Next Phase Readiness

Ready for `03-06`: admin runtime provider override can now build on the environment default, selected-provider readiness, and normalized provider metadata added here.

## Self-Check: PASSED

- Verified created files exist: `backend/app/ai/search_worker/firecrawl_client.py`, `03-USER-SETUP.md`, and `03-05-SUMMARY.md`.
- Verified task commits exist: `3a544fb`, `d0eaf01`, `ba34196`, and `48a86aa`.

---
*Phase: 03-policy-controlled-google-search*
*Completed: 2026-06-23*
