---
phase: 02-private-direct-chat
plan: "01"
subsystem: api
tags: [fastapi, sqlalchemy, postgres, alembic, authorization, chat]
requires:
  - phase: 01-secure-platform-and-account-access
    provides: strict principal resolution, chat scopes, PostgreSQL account foundation
provides:
  - Owner-scoped conversation create, list, retrieve, and soft-delete API
  - Message turn-state schema foundation for future idempotent chat sends
  - PostgreSQL-backed BOLA and chat-scope regression coverage
affects: [02-02, 02-03, 02-04, 03-policy-controlled-google-search]
tech-stack:
  added: []
  patterns: [owner-constrained repository queries, cursor pagination, soft-delete retention]
key-files:
  created:
    - backend/alembic/versions/0003_chat_turn_state.py
    - backend/app/schemas/chat.py
    - backend/app/db/repositories/conversations.py
    - backend/app/services/chat.py
    - backend/app/api/routes/chat.py
    - backend/tests/integration/chat/test_conversation_crud.py
    - backend/tests/security/test_chat_authorization.py
  modified:
    - backend/app/models/domain.py
    - backend/app/api/__init__.py
    - backend/app/main.py
key-decisions:
  - "Conversation ownership is enforced in repository SQL predicates using both conversation ID and user ID."
  - "Cross-user conversation access returns the same generic not-found envelope used for missing owned rows."
patterns-established:
  - "Chat routes require resolve_principal plus evaluate_required_scopes before data return or mutation."
  - "Conversation pagination uses a signed-shape opaque cursor over updated_at and id, not offset paging."
requirements-completed: [AUTHZ-03, AUTHZ-05, AUTHZ-06, CHAT-01, CHAT-02, CHAT-03, CHAT-04]
duration: 16 min
completed: 2026-06-12
---

# Phase 02 Plan 01: Owner-Scoped Conversation Lifecycle Summary

**Owner-only conversation CRUD with PostgreSQL-backed BOLA tests and migrated message turn-state fields**

## Performance

- **Duration:** 16 min
- **Started:** 2026-06-12T07:05:56Z
- **Completed:** 2026-06-12T07:21:05Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments

- Added RED tests first for conversation create/list/retrieve/delete, chat scope denial, stale/inactive principals, and two-user BOLA denial.
- Added Alembic revision `0003_chat_turn_state` with `client_message_id`, `status`, status check, partial idempotency index, and conversation/status lookup index.
- Implemented `/api/conversations` CRUD routes through a service and repository that constrain `Conversation.id`, `Conversation.user_id`, and `deleted_at IS NULL` in SQL.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create RED owner-scoped conversation lifecycle tests** - `7a2dcdf` (test)
2. **Task 2: Implement migrated owner-only conversation CRUD** - `dce4ecb` (feat)

**Plan metadata:** this docs commit

## Files Created/Modified

- `backend/alembic/versions/0003_chat_turn_state.py` - Adds message turn-state and idempotency schema fields.
- `backend/app/models/domain.py` - Mirrors message status and client-message fields in the ORM.
- `backend/app/schemas/chat.py` - Defines typed conversation, message, and cursor-page response schemas.
- `backend/app/db/repositories/conversations.py` - Implements owner-constrained CRUD and cursor pagination.
- `backend/app/services/chat.py` - Coordinates conversation lifecycle commits and not-found behavior.
- `backend/app/api/routes/chat.py` - Exposes scoped create, list, retrieve, and delete endpoints.
- `backend/app/api/__init__.py` - Exports the chat route module.
- `backend/app/main.py` - Registers the chat router and permits DELETE in CORS.
- `backend/tests/integration/chat/test_conversation_crud.py` - Covers owner lifecycle and soft-delete retention.
- `backend/tests/security/test_chat_authorization.py` - Covers missing principal, missing scope, stale/inactive principal, and BOLA denial.

## Decisions Made

- Use `404 conversation_not_found` for both missing and cross-user conversation IDs to avoid an existence signal.
- Keep message send/provider behavior out of this plan; newly created conversations intentionally return an empty `messages` array.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Used the repository test Compose target for PostgreSQL verification**
- **Found during:** Task 1 and Task 2 verification
- **Issue:** `docker compose run --rm backend pytest ...` used the development backend image and did not include newly created tests until rebuild; the repository already has `compose.test.yaml` with `backend-test` and `postgres-test`.
- **Fix:** Rebuilt `backend-test` and ran the same Alembic/pytest checks through `docker compose -f compose.test.yaml run --rm backend-test ...`.
- **Files modified:** None
- **Verification:** `docker compose -f compose.test.yaml run --rm backend-test sh -lc "alembic upgrade head && pytest -q tests/integration/chat/test_conversation_crud.py tests/security/test_chat_authorization.py -x"` passed.
- **Committed in:** N/A - verification environment only

**2. [Rule 2 - Missing Critical] Allowed DELETE in FastAPI CORS configuration**
- **Found during:** Task 2 implementation
- **Issue:** The plan adds browser-facing `DELETE /api/conversations/{id}`, but existing CORS allowed methods omitted DELETE.
- **Fix:** Added `DELETE` to `allow_methods` in `backend/app/main.py`.
- **Files modified:** `backend/app/main.py`
- **Verification:** Focused chat test suite passed after router registration.
- **Committed in:** `dce4ecb`

---

**Total deviations:** 2 auto-fixed (1 blocking verification environment, 1 missing critical browser API support)
**Impact on plan:** Both changes were necessary to verify and operate the planned CRUD route surface. No feature scope was added beyond the plan.

## Issues Encountered

- The first full `docker compose build backend` attempt exceeded the command timeout; targeted `compose.test.yaml` rebuild completed quickly and was used for verification.
- Docker reported pre-existing orphan containers from the development Compose project during test runs. They did not affect the isolated `postgres-test` verification.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None. The empty `messages=[]` response for new conversations is intentional because message send/provider work is explicitly deferred to later Phase 02 plans.

## Verification

- RED: `docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/integration/chat/test_conversation_crud.py tests/security/test_chat_authorization.py` failed with six `404 Not Found` assertions before implementation.
- GREEN: `docker compose -f compose.test.yaml run --rm backend-test sh -lc "alembic upgrade head && pytest -q tests/integration/chat/test_conversation_crud.py tests/security/test_chat_authorization.py -x"` passed with `6 passed`.

## Self-Check: PASSED

- Key files exist on disk.
- Task commits `7a2dcdf` and `dce4ecb` exist in git history.
- Focused Alembic and pytest verification passed after implementation.
- Stub scan found only intentional empty conversation messages for out-of-scope message-send behavior.

## Next Phase Readiness

Ready for Plan 02 to add durable message send/idempotency on top of the migrated turn-state fields and owner-scoped conversation access.

---
*Phase: 02-private-direct-chat*
*Completed: 2026-06-12*
