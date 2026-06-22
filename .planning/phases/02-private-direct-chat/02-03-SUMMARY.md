---
phase: 02-private-direct-chat
plan: "03"
subsystem: api
tags: [fastapi, sqlalchemy, postgres, openai, idempotency, chat]
requires:
  - phase: 02-02
    provides: configuration-driven OpenAI-compatible direct chat adapter
provides:
  - Durable direct-chat send and retry state machine
  - Owner-scoped initial-message, send, and retry routes
  - Provider failure persistence with retryable safe metadata and correlation IDs
affects: [02-04, 02-05, 02-06, 03-policy-controlled-google-search]
tech-stack:
  added: []
  patterns: [idempotent client_message_id turns, lazy provider adapter boundary, provider call after DB commit]
key-files:
  created:
    - backend/tests/integration/chat/test_message_send.py
    - backend/tests/security/test_chat_idempotency.py
    - backend/tests/security/test_chat_provider_failure.py
  modified:
    - backend/app/schemas/chat.py
    - backend/app/db/repositories/conversations.py
    - backend/app/services/chat.py
    - backend/app/api/routes/chat.py
key-decisions:
  - "Provider calls are made only after the accepted user message and pending assistant row are committed."
  - "Send/retry obtains the OpenAI-compatible adapter through the existing settings boundary, preserving custom LLM_API_BASE and LLM_MODEL configuration."
  - "Provider failures return a provider_failed envelope and persist a failed assistant row with safe retry metadata."
patterns-established:
  - "Duplicate client_message_id returns the existing turn state without another provider call."
  - "Retry reuses the original user message and paired assistant row."
requirements-completed: [AUTHZ-03, AUTHZ-05, AUTHZ-06, CHAT-01, CHAT-03, CHAT-05, CHAT-06, CHAT-07, CHAT-11]
duration: 14 min
completed: 2026-06-12
---

# Phase 02 Plan 03: Direct Send and Retry Summary

**Idempotent direct LLM send/retry with durable turn state and safe provider failure persistence**

## Performance

- **Duration:** 14 min
- **Started:** 2026-06-12T07:59:02Z
- **Completed:** 2026-06-12T08:13:04Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Added RED tests first for initial-message creation, active-thread send, duplicate replay, pending-turn conflict, provider failures, retry, and denied provider-call paths.
- Implemented local title generation from the first user message and non-streaming JSON responses for initial-message and existing-thread sends.
- Persisted user messages and pending assistant rows before provider calls, then updated the same assistant row to completed or failed.
- Preserved provider configurability by calling the 02-02 adapter/settings boundary instead of hardcoding OpenAI defaults in send/retry code.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create RED send, retry, idempotency, and provider-failure tests** - `a12b5f8` (test)
2. **Task 2: Implement direct non-streaming send and retry** - `22226d8` (feat)

**Plan metadata:** this docs commit

## Files Created/Modified

- `backend/tests/integration/chat/test_message_send.py` - Covers initial-message creation and existing-thread non-streaming send.
- `backend/tests/security/test_chat_idempotency.py` - Covers duplicate client IDs, pending conflict, and zero provider calls after denial.
- `backend/tests/security/test_chat_provider_failure.py` - Covers provider error persistence, correlation IDs, and retry over the original turn.
- `backend/app/schemas/chat.py` - Adds message send payload and initial-message create payload support.
- `backend/app/db/repositories/conversations.py` - Adds owner-locked turn lookup, sequence allocation, provider context, and assistant state updates.
- `backend/app/services/chat.py` - Implements send, create-with-initial-message, retry, local titles, and provider success/failure state transitions.
- `backend/app/api/routes/chat.py` - Adds send/retry routes and provider failure/conflict error mapping.

## Decisions Made

- Kept provider construction lazy until after the pending assistant row is committed, so configuration/provider failures still become durable failed turns.
- Returned `409 turn_in_progress` for a second send while another assistant row is pending in the same conversation.
- Used `502 provider_failed` with safe `provider_error_code`, `retryable`, and correlation ID fields for provider failures.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Rebuilt the backend image before RED verification**
- **Found during:** Task 1
- **Issue:** The development Compose backend image did not contain the new test files, causing `pytest` to report missing files instead of the intended RED failures.
- **Fix:** Rebuilt the backend image and reran the plan RED command.
- **Files modified:** None
- **Verification:** RED rerun collected all 11 tests and failed on absent send/retry behavior.
- **Committed in:** N/A - verification environment only

**2. [Rule 1 - Bug] Fixed transaction handling after principal resolution**
- **Found during:** Task 2 verification
- **Issue:** `resolve_principal` starts a session transaction before route code runs, so `async with session.begin()` in the service raised `InvalidRequestError`.
- **Fix:** Used explicit flush/commit/rollback around pre-provider writes and post-provider updates, preserving the no-provider-call-inside-transaction guarantee.
- **Files modified:** `backend/app/services/chat.py`
- **Verification:** Focused Task 2 pytest command passed.
- **Committed in:** `22226d8`

**3. [Rule 2 - Missing Critical] Made provider adapter acquisition lazy**
- **Found during:** Task 2 implementation
- **Issue:** Constructing the real provider adapter in the route before persisting the pending turn would bypass durable failed-turn state for provider configuration failures.
- **Fix:** Passed a lazy adapter factory into the service and constructed/called the adapter only in the post-commit provider step.
- **Files modified:** `backend/app/services/chat.py`, `backend/app/api/routes/chat.py`
- **Verification:** Provider failure and retry tests passed; no send/retry code hardcodes OpenAI base URL or model values.
- **Committed in:** `22226d8`

---

**Total deviations:** 3 auto-fixed (1 blocking verification issue, 1 bug, 1 missing critical safeguard)
**Impact on plan:** All fixes preserved the planned scope and strengthened the required state-machine guarantees.

## Issues Encountered

- Docker continued to report pre-existing orphan containers from prior Compose runs. They were not removed and did not affect the focused verification.
- The development backend image must be rebuilt after source/test changes because the Compose service copies backend code at image build time.

## User Setup Required

None - no new external service configuration required. Live provider use still depends on the 02-02 `LLM_API_KEY`/`LLM_API_KEY_FILE`, `LLM_API_BASE`, and `LLM_MODEL` settings.

## Known Stubs

None. Empty assistant content is intentional only for pending/failed assistant rows, and `messages=[]` remains the correct response for explicitly created empty conversations.

## Verification

- RED: `docker compose run --rm backend pytest -q tests/integration/chat/test_message_send.py tests/security/test_chat_idempotency.py tests/security/test_chat_provider_failure.py; if ($LASTEXITCODE -eq 0) { throw "Expected direct-chat send tests to be RED" }` failed with 11 collected test failures after rebuilding the backend image.
- GREEN: `docker compose run --rm backend pytest -q tests/integration/chat/test_message_send.py tests/security/test_chat_authorization.py tests/security/test_chat_idempotency.py tests/security/test_chat_provider_failure.py tests/unit/ai/test_chat_adapter.py -x` passed with `24 passed`.
- Migration drift: `docker compose run --rm backend alembic check` passed with `No new upgrade operations detected.`
- Config boundary: `rg -n "LLM_API_BASE|LLM_MODEL|gpt-4o|api\\.openai|OpenAIChatAdapter" backend/app/services/chat.py backend/app/api/routes/chat.py backend/app/ai/chat_adapter.py backend/app/core/config.py` showed send/retry reaches `OpenAIChatAdapter(settings=...)` and did not add hardcoded provider defaults.

## Self-Check: PASSED

- Key created and modified files exist on disk.
- Task commits `a12b5f8` and `22226d8` exist in git history.
- Focused send/retry, authorization, provider-failure, and adapter tests passed.
- Alembic check passed with no schema drift.
- Stub scan found no unresolved implementation stubs.

## Next Phase Readiness

Ready for Plan 02-04 to connect the frontend chat workspace to the new initial-message, send, retry, pending, and failed-turn API states.

---
*Phase: 02-private-direct-chat*
*Completed: 2026-06-12*
