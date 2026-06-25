---
phase: 07-sender-constrained-sessions-and-cryptographic-hardening
plan: "04"
subsystem: auth
tags: [dpop, jwt, cnf, refresh, replay, kong]

requires:
  - phase: 07-01
    provides: replay journal storage and consume-once repository helper
  - phase: 07-02
    provides: one-time auth transaction hardening pattern
provides:
  - DPoP proof parsing and replay validation
  - sender-constrained access-token `cnf.jkt` support
  - refresh-family key-thumbprint binding for local auth sessions
affects: [auth, authorization, gateway-cors, frontend-device-proofs]

tech-stack:
  added: []
  patterns: [DPoP proof JWT validation, `cnf.jkt` access-token binding, refresh-family thumbprint checks]

key-files:
  created:
    - backend/app/security/dpop.py
  modified:
    - backend/app/security/access_tokens.py
    - backend/app/authorization/principal.py
    - backend/app/services/authentication.py
    - backend/app/services/sessions.py
    - backend/app/api/routes/auth.py
    - backend/tests/integration/auth/test_session_flow.py
    - backend/tests/security/test_jwt_profile.py

key-decisions:
  - "DPoP is enforced only when `settings.dpop_enabled` is true, preserving the existing bearer-mode compatibility path until frontend rollout."
  - "Access tokens carry `cnf.jkt`; refresh families store the same thumbprint and deny mismatched proof keys."
  - "DPoP proof replay evidence is committed before returning a 401 so denial does not discard security events."

patterns-established:
  - "Protected backend routes validate DPoP in FastAPI, not Kong."
  - "DPoP supplements existing Origin and CSRF controls on cookie-backed refresh/logout routes."

requirements-completed: [AUTH-11, AUTH-12, OBS-08]

duration: 42min
completed: 2026-06-25
---

# Phase 07-04: Sender-Constrained Auth Sessions Summary

**Local auth sessions can be bound to DPoP client keys, with access-token `cnf.jkt`, refresh-family thumbprints, and replay evidence.**

## Performance

- **Duration:** 42 min
- **Started:** 2026-06-24T23:25:00Z
- **Completed:** 2026-06-24T23:32:00Z
- **Tasks:** 3
- **Files modified:** 13

## Accomplishments

- Added `backend/app/security/dpop.py` for DPoP proof parsing, JWK thumbprints, method/URL checks, and replay-journal consumption.
- Extended access tokens with optional `cnf.jkt` claims and backend decode validation.
- Enforced DPoP proof matching in `resolve_principal()` when `dpop_enabled` is active.
- Bound login-issued refresh families and rotated access tokens to the validated DPoP key thumbprint.
- Added refresh mismatch and proof replay evidence tests.
- Added `DPoP` to FastAPI and Kong CORS allow headers.

## Task Commits

1. **Task 1: Lock sender-constrained auth behavior in integration and security tests** - `306b51f` (test)
2. **Task 2: Add DPoP proof helpers and sender-constrained access-token claims** - `f30f39a` (feat)
3. **Task 3: Bind login/refresh/logout flows to client proof material and evidence** - `f30f39a` (feat)

## Files Created/Modified

- `backend/app/security/dpop.py` - DPoP proof validation and replay consumption.
- `backend/app/security/access_tokens.py` - Optional `cnf.jkt` issuance and decode validation.
- `backend/app/authorization/principal.py` - DPoP proof enforcement for protected routes.
- `backend/app/services/authentication.py` - Local login refresh-family thumbprint binding.
- `backend/app/services/sessions.py` - Refresh/logout key mismatch denial and evidence.
- `backend/app/api/routes/auth.py` - DPoP extraction for login, refresh, and logout.
- `kong/kong.yml` and `kong/kong.prod.yml` - Allow browser `DPoP` preflight header.

## Decisions Made

- DPoP remains feature-flagged through `dpop_enabled` so Phase 07-05 can roll out browser key management deliberately.
- The replay journal is used for proof `jti` values across login, refresh, logout, and `/me`.
- Mismatch evidence stores thumbprints and family ids, never raw proof JWTs or private material.

## Deviations from Plan

### Auto-fixed Issues

**1. Browser proof header needed gateway CORS support**
- **Found during:** Task 3
- **Issue:** FastAPI accepted `DPoP`, but Kong CORS still only allowed the old auth headers.
- **Fix:** Added `DPoP` to dev/prod Kong CORS config and static CORS tests.
- **Verification:** Target auth tests and compile checks passed; gateway tests are skipped in the backend-only image.
- **Committed in:** `f30f39a`

**Total deviations:** 1 auto-fixed
**Impact on plan:** Required for the planned browser proof rollout; no scope creep.

## Issues Encountered

- Requirement IDs `AUTH-11`, `AUTH-12`, and `OBS-08` were not found in the local requirements matrix, matching the earlier Phase 07 traceability gap.
- Gateway smoke/static tests skip inside the backend-only Compose image because repo-root gateway files are not mounted in that context.

## User Setup Required

None for backend tests. Browser rollout still requires Phase 07-05 frontend key generation and proof attachment.

## Next Phase Readiness

07-05 can wire frontend device proofs, enable the DPoP path from the browser, and update Vietnamese rollout/verification docs.

---
*Phase: 07-sender-constrained-sessions-and-cryptographic-hardening*
*Completed: 2026-06-25*
