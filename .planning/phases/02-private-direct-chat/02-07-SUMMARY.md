---
phase: 02-private-direct-chat
plan: "07"
subsystem: assembled-smoke
tags: [fastapi, postgres, nextjs, docker-compose, smoke, authorization, markdown]
requires:
  - phase: 02-05
    provides: owner-scoped navigation, delete, undo, and retry state labels
  - phase: 02-06
    provides: safe assistant Markdown and inert code rendering
provides:
  - Assembled Phase 2 private direct-chat smoke gate
  - End-to-end verification evidence for owner isolation, idempotency, provider failure, retry, unsafe Markdown persistence, and session cleanup
  - Phase 2 completion state for the local Docker Compose topology
affects: [03-policy-controlled-google-search]
tech-stack:
  added: []
  patterns:
    - deterministic provider-boundary smoke adapter
    - assembled two-user BOLA smoke
    - final default-compose health gate
key-files:
  created:
    - backend/tests/smoke/test_private_direct_chat.py
    - .planning/phases/02-private-direct-chat/02-07-SUMMARY.md
  modified:
    - .planning/ROADMAP.md
    - .planning/STATE.md
key-decisions:
  - "The final Phase 2 smoke injects a deterministic chat adapter at the app provider boundary so it does not need live external provider credentials."
  - "The assembled gate verifies raw unsafe assistant Markdown persistence at the API boundary while frontend Plan 06 tests verify inert browser rendering."
  - "No Phase 2 source gaps were found by the assembled smoke; only test cookie setup was adjusted for current HTTPX behavior."
patterns-established:
  - "End-of-phase smoke tests exercise auth, owner predicates, provider boundary, durable message state, and browser session contract in one scenario."
  - "Final phase verification runs both isolated test-compose backend coverage and default-compose health/smoke evidence."
requirements-completed: [AUTHZ-03, AUTHZ-05, AUTHZ-06, CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05, CHAT-06, CHAT-07, CHAT-08, CHAT-09, CHAT-10, CHAT-11]
duration: 16 min
completed: 2026-06-12
---

# Phase 02 Plan 07: Assembled Private Direct Chat Smoke Summary

**Phase 2 now has an assembled smoke gate proving the private direct-chat slice works across authentication, owner-scoped persistence, provider failure handling, retry, deletion, undo, unsafe content persistence, and logout cleanup.**

## Performance

- **Duration:** 16 min
- **Started:** 2026-06-12T12:36:00Z
- **Completed:** 2026-06-12T12:52:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added `backend/tests/smoke/test_private_direct_chat.py` as the final assembled Phase 2 gate.
- Covered real register/login/current-user flow, conversation creation with `initial_message`, ordered history reload, newest-first listing, delete, undo, logout, and failed refresh after logout.
- Covered two-user BOLA denial for retrieve, send, retry, delete, undo-delete, and list visibility without leaking the owner message body.
- Covered missing-scope and stale-token fail-closed paths without invoking the provider adapter.
- Covered duplicate `client_message_id` idempotency by asserting one durable user row and no duplicate provider work.
- Covered provider failure by asserting a 502 response, a failed assistant row with retry metadata and correlation ID, no fabricated assistant content, and successful retry reuse.
- Covered unsafe Markdown persistence by asserting the backend stores raw adversarial content and does not return rendered HTML or sanitizer-warning fields.
- Ran the full default Compose stack with `docker compose up --build --wait`; all services reached healthy.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create the assembled private-direct-chat smoke test** - `735d7c5` (test)

**Plan metadata:** this docs commit

## Files Created/Modified

- `backend/tests/smoke/test_private_direct_chat.py` - Deterministic assembled Phase 2 smoke with fake provider boundary and two-user authorization probes.
- `.planning/phases/02-private-direct-chat/02-07-SUMMARY.md` - This closeout summary.
- `.planning/ROADMAP.md` - Marks Phase 2 as complete with 7/7 plans executed.
- `.planning/STATE.md` - Advances GSD state to Phase 2 complete and ready for Phase 3 planning.

## Decisions Made

- Used `app.state.chat_adapter` injection for the smoke provider boundary. This keeps the test deterministic and still exercises the same chat service behavior as configured provider calls.
- Kept unsafe Markdown verification split by responsibility: backend smoke proves raw content remains raw API data; frontend Plan 06 tests prove browser rendering is inert.
- Did not modify production chat, repository, provider, or frontend source during Plan 07 because the assembled gate found no product gaps.

## Deviations from Plan

### Auto-fixed Issues

**1. [Test Compatibility] Avoided deprecated HTTPX per-request cookies**
- **Found during:** Smoke verification.
- **Issue:** The test passed logout/refresh cookies via per-request `cookies=...`, and warnings are treated as errors.
- **Fix:** Set the refresh and CSRF cookies directly on `client.cookies` before logout and refresh probes.
- **Files modified:** `backend/tests/smoke/test_private_direct_chat.py`
- **Verification:** The focused smoke passed with `1 passed`.
- **Committed in:** `735d7c5`

---

**Total deviations:** 1 test compatibility fix.
**Impact on plan:** No product scope change; the assembled smoke remains deterministic and credential-free.

## Issues Encountered

- Docker Compose continued to report pre-existing orphan containers, including the test Postgres container. They were not removed and did not affect verification.
- Docker Desktop emitted a transient HTTP/2 pipe warning during `docker compose up --build --wait`; Compose returned success and all services reached healthy.

## User Setup Required

None. No new packages, secrets, environment variables, or external provider credentials were added by Plan 07.

## Known Stubs

None for Phase 2 private direct chat. Search grounding and Python sandbox execution remain later-phase scope.

## Verification

- Backend test image rebuild: `docker compose -f compose.test.yaml build backend-test` passed.
- Focused test-compose smoke: `docker compose -f compose.test.yaml run --rm backend-test pytest tests/smoke/test_private_direct_chat.py -q` passed with `1 passed`.
- Isolated backend regression pack: `docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/integration/chat tests/security/test_chat_authorization.py tests/security/test_chat_idempotency.py tests/security/test_chat_provider_failure.py tests/security/test_chat_rendering_contract.py tests/unit/ai/test_chat_adapter.py tests/smoke/test_private_direct_chat.py -x` passed with `32 passed`.
- Frontend chat tests: `docker compose run --rm frontend npm run test -- tests/chat-workspace.test.ts tests/chat-markdown.test.ts tests/chat-session-routing.test.ts` passed with `14 passed`.
- Frontend typecheck: `docker compose run --rm frontend npm run typecheck` passed.
- Frontend production build: `docker compose run --rm frontend npm run build` passed.
- Default topology: `docker compose up --build --wait` passed; Postgres, backend, frontend, Kong, and sandbox were healthy.
- Default backend smoke: `docker compose run --rm backend pytest -q tests/smoke/test_private_direct_chat.py` passed with `1 passed`.
- Default backend regression pack: `docker compose run --rm backend pytest -q tests/integration/chat tests/security/test_chat_authorization.py tests/security/test_chat_idempotency.py tests/security/test_chat_provider_failure.py tests/security/test_chat_rendering_contract.py tests/unit/ai/test_chat_adapter.py -x` passed with `31 passed`.

## Next Phase Readiness

Phase 2 is complete and ready for Phase 3 planning. The next phase can build policy-controlled Google Search on top of authenticated direct chat, owner-scoped durable conversations, safe Markdown rendering, and a healthy Compose topology.

## Self-Check: PASSED

- `backend/tests/smoke/test_private_direct_chat.py` exists and passes in both test-compose and default backend contexts.
- The smoke covers register, login, chat create, send, history reload, list ordering, duplicate submit, provider failure, retry, unsafe Markdown persistence, delete, undo, cross-user denial, missing scope, stale token, logout, and invalid refresh.
- No live external LLM provider credential is required.
- Phase 2 final backend, frontend, build, and default Compose gates passed.
- Task commit `735d7c5` exists in git history.

---
*Phase: 02-private-direct-chat*
*Completed: 2026-06-12*
