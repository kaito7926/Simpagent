---
phase: 07-sender-constrained-sessions-and-cryptographic-hardening
plan: "02"
subsystem: auth
tags: [oauth, pkce, replay, google, github, security-events]

requires:
  - phase: 07-sender-constrained-sessions-and-cryptographic-hardening
    provides: 07-01 shared replay-journal persistence and consume-once repository helper
provides:
  - PKCE S256 authorization starts for Google and GitHub OAuth
  - Sealed provider-bound OAuth transaction cookies
  - Callback-side one-time replay-journal consumption before code exchange
  - Correlated OAuth transaction invalid/replay security evidence
affects: [auth, oauth, identity, security-evidence]

tech-stack:
  added: []
  patterns:
    - Backend-owned OAuth transaction cookies are signed and HttpOnly.
    - OAuth transaction jtis are consumed through `SessionsRepository.consume_security_artifact_once`.

key-files:
  created:
    - backend/app/security/oauth_transaction.py
  modified:
    - backend/app/api/routes/auth_oauth.py
    - backend/app/identity/providers/google.py
    - backend/app/identity/providers/github.py
    - backend/tests/integration/auth/test_oauth_flows.py
    - backend/tests/unit/test_oauth_state_cookie.py
    - backend/tests/integration/auth/test_google_oauth.py
    - backend/tests/integration/auth/test_github_oauth.py

key-decisions:
  - "OAuth start remains backend-owned; the browser receives only a redirect and an HttpOnly sealed transaction cookie."
  - "Callback transaction reuse is denied through the shared replay journal before provider code exchange."
  - "In-process HTTP OAuth tests set `cookie_secure=false` in fixtures so Secure-cookie transport policy does not mask route behavior."

patterns-established:
  - "OAuth callback validation order is transaction verification, replay-journal consumption, code presence, provider exchange, then local session issuance."
  - "OAuth transaction denial evidence uses `oauth_transaction_invalid` and `oauth_transaction_replay` security events."

requirements-completed: [IDEN-09, OBS-08]

duration: 35 min
completed: 2026-06-24
---

# Phase 07 Plan 02: OAuth PKCE Transaction Summary

**Google and GitHub OAuth callbacks are now PKCE-bound and consume one-time provider-bound transaction artifacts before code exchange.**

## Performance

- **Duration:** 35 min
- **Started:** 2026-06-24T00:30:00Z
- **Completed:** 2026-06-24T01:05:00Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments

- Added RED tests requiring PKCE challenge parameters, sealed transaction cookie invariants, and callback replay denial evidence.
- Added `backend/app/security/oauth_transaction.py` for issuing, sealing, and verifying provider-bound PKCE transactions.
- Updated Google and GitHub provider request builders to include `code_challenge`, `code_challenge_method=S256`, and callback `code_verifier`.
- Wired OAuth start/callback routes so callbacks consume transaction jtis through the replay journal before provider exchange.

## Task Commits

1. **Task 1: Lock PKCE and one-time transaction behavior in OAuth tests** - `b058905` (test)
2. **Task 2: Add sealed OAuth transaction helpers and provider PKCE support** - `eb3d986` (feat)
3. **Task 3: Wire PKCE and one-time transaction validation into OAuth routes and evidence** - `cb52e3d` (feat)

## Files Created/Modified

- `backend/app/security/oauth_transaction.py` - Issues, seals, and verifies provider-bound PKCE OAuth transactions.
- `backend/app/api/routes/auth_oauth.py` - Issues transaction cookies, adds PKCE redirect challenge, consumes transaction jtis before code exchange, and records denial evidence.
- `backend/app/identity/providers/google.py` - Adds PKCE authorization and token-exchange support.
- `backend/app/identity/providers/github.py` - Adds PKCE authorization and token-exchange support.
- `backend/tests/integration/auth/test_oauth_flows.py` - Asserts PKCE challenge parameters on Google start.
- `backend/tests/unit/test_oauth_state_cookie.py` - Covers sealed transaction cookie invariants.
- `backend/tests/integration/auth/test_google_oauth.py` - Covers PKCE callback verifier and transaction replay denial evidence.
- `backend/tests/integration/auth/test_github_oauth.py` - Covers GitHub PKCE redirect and callback verifier behavior.

## Decisions Made

- The transaction cookie is signed and HttpOnly rather than stored client-side in readable browser storage.
- The callback fails with the existing safe `oauth_state_invalid` shape for malformed, mismatched, expired, or replayed transactions.
- Replay events use the shared replay foundation from 07-01 rather than an OAuth-only in-memory cache.

## Deviations from Plan

None - plan executed exactly as written.

---

**Total deviations:** 0 auto-fixed
**Impact on plan:** OAuth hardening now builds directly on the shared replay foundation and keeps existing provider-unconfigured behavior intact.

## Issues Encountered

- The running development backend container was image-built and did not reflect changed app code, so verification used the dedicated `backend-test` Compose service with `--build`.
- OAuth integration fixtures needed `cookie_secure=false` because their in-process HTTP transport uses `http://testserver`; production and default app behavior remain secure-cookie capable.

## User Setup Required

None - no external service configuration required.

## Verification

- `docker compose -f compose.test.yaml run --rm --build backend-test python -m pytest -q tests/integration/auth/test_oauth_flows.py tests/integration/auth/test_google_oauth.py tests/integration/auth/test_github_oauth.py tests/unit/test_oauth_state_cookie.py -x` - passed, 16 tests.
- Grep verification confirmed PKCE challenge issuance, transaction sealing, callback transaction consumption, and replay evidence hooks.

## Self-Check: PASSED

- [x] All tasks executed.
- [x] Each task committed individually.
- [x] SUMMARY.md created in plan directory.
- [x] Targeted Compose test suite passed.
- [x] Replay and mismatch denial paths return safe OAuth errors without exposing verifier material.

## Next Phase Readiness

Plan 07-03 can use the same replay-journal consume-once pattern for search and Python capability credentials.

---
*Phase: 07-sender-constrained-sessions-and-cryptographic-hardening*
*Completed: 2026-06-24*
