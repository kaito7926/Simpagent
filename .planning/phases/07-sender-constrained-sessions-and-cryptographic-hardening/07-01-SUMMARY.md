---
phase: 07-sender-constrained-sessions-and-cryptographic-hardening
plan: "01"
subsystem: auth
tags: [sessions, replay, dpop, pkce, capabilities, alembic]

requires:
  - phase: 06-adversarial-verification-and-vietnamese-delivery
    provides: verified security evidence baseline for the assembled prototype
provides:
  - Shared replay-journal persistence for one-time security artifacts
  - Sender-constrained refresh-family metadata fields
  - Phase 07 rollout flags and TTL controls for DPoP, OAuth PKCE, and capability replay protection
  - Repository consume-once helper with correlated replay evidence
affects: [auth, oauth, search, python, security-evidence]

tech-stack:
  added: []
  patterns:
    - Shared `security_replay_records` table for bounded one-time artifact consumption
    - `SessionsRepository.consume_security_artifact_once` returns a typed accept/deny result

key-files:
  created:
    - backend/alembic/versions/0006_sender_constrained_replay_foundations.py
  modified:
    - backend/app/core/config.py
    - backend/app/models/session.py
    - backend/app/db/repositories/sessions.py
    - backend/app/services/sessions.py
    - backend/tests/integration/auth/test_session_flow.py
    - backend/tests/security/test_search_capability_token.py

key-decisions:
  - "DPoP is feature-flagged off until browser proof integration lands, while PKCE and capability replay protection default on as backend-owned hardening."
  - "The new Alembic file keeps the requested Phase 07 filename but depends on the existing declared `0006_encrypt_message_content` revision."
  - "One-time artifact replay is represented as a typed repository result instead of forcing every caller into exception control flow."

patterns-established:
  - "Replay journal rows are unique by artifact type, audience, and jti."
  - "Replay denies update the original record and create a correlated `SecurityEvent` with artifact metadata."
  - "Refresh replay evidence now includes sender-constrained binding metadata."

requirements-completed: [AUTH-12, AGNT-08, OBS-08]

duration: 30 min
completed: 2026-06-24
---

# Phase 07 Plan 01: Replay Foundation Summary

**Shared replay-journal schema, sender-constrained session metadata, and consume-once repository evidence for later PKCE, DPoP, and capability hardening.**

## Performance

- **Duration:** 30 min
- **Started:** 2026-06-24T00:00:00Z
- **Completed:** 2026-06-24T00:30:00Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- Added baseline security tests for sender-constrained refresh-family metadata and persistent search capability replay denial.
- Added Phase 07 config flags and TTLs for DPoP, OAuth PKCE, capability replay protection, OAuth transactions, and replay-journal retention.
- Added `SecurityReplayRecord` plus Alembic schema support for one-time artifact consumption.
- Added `SessionsRepository.consume_security_artifact_once` and enriched refresh replay evidence with binding metadata.

## Task Commits

1. **Task 1: Lock the replay-foundation contract in baseline security tests** - `aee2710` (test)
2. **Task 2: Add replay-journal schema and sender-constrained session metadata** - `4c27b10` (feat)
3. **Task 3: Add repository consume-once helpers and evidence-ready replay persistence** - `abb98ae` (feat)

## Files Created/Modified

- `backend/alembic/versions/0006_sender_constrained_replay_foundations.py` - Adds refresh-family binding columns and the `security_replay_records` table.
- `backend/app/core/config.py` - Adds DPoP, PKCE, capability replay, OAuth transaction, and replay journal rollout settings.
- `backend/app/models/session.py` - Adds sender-constrained refresh-family fields and the replay record model.
- `backend/app/db/repositories/sessions.py` - Adds typed consume-once replay persistence and replay event creation.
- `backend/app/services/sessions.py` - Adds binding metadata to refresh-reuse security evidence.
- `backend/tests/integration/auth/test_session_flow.py` - Asserts refresh-family binding metadata and replay evidence metadata.
- `backend/tests/security/test_search_capability_token.py` - Covers persistent consume-once search capability replay denial.

## Decisions Made

- DPoP remains disabled by default until the frontend proof integration and protected-route enforcement land later in Phase 07.
- The requested migration filename was preserved, but the actual Alembic revision follows the existing chain after `0006_encrypt_message_content`.
- Replay consume helpers return a typed result so search, Python, OAuth, and DPoP callers can all fail closed while deciding their own outward error shape.

## Deviations from Plan

None - plan executed exactly as written.

---

**Total deviations:** 0 auto-fixed
**Impact on plan:** The foundation now supports later Phase 07 plans without introducing separate replay tables or silent deny-only behavior.

## Issues Encountered

- Host-side pytest initially failed because the local Python 3.12 user environment was missing declared backend test dependencies and could not resolve the Compose-only `postgres-test` hostname. The required targeted tests were rerun inside the already-running backend container and passed.

## User Setup Required

None - no external service configuration required.

## Verification

- `docker exec simpagent-backend-1 python -m pytest -q tests/integration/auth/test_session_flow.py tests/security/test_search_capability_token.py -x` - passed, 5 tests.
- Grep verification confirmed `dpop_enabled`, `oauth_pkce_enabled`, and `capability_replay_protection_enabled` in `backend/app/core/config.py`.
- Grep verification confirmed `auth_binding_method`, `key_thumbprint`, `SecurityReplayRecord`, and `security_replay_records` in the model and migration.
- Grep verification confirmed consume-once repository helpers and correlated replay evidence paths.

## Self-Check: PASSED

- [x] All tasks executed.
- [x] Each task committed individually.
- [x] SUMMARY.md created in plan directory.
- [x] Targeted container pytest passed.
- [x] Acceptance criteria are grep-verifiable in the expected files.

## Next Phase Readiness

Plan 07-02 can add PKCE and sealed OAuth transactions using the shared replay journal. Plan 07-03 can consume search and Python capability artifacts through `SessionsRepository.consume_security_artifact_once`.

---
*Phase: 07-sender-constrained-sessions-and-cryptographic-hardening*
*Completed: 2026-06-24*
