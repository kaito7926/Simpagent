---
phase: 07-sender-constrained-sessions-and-cryptographic-hardening
plan: "05"
subsystem: frontend
tags: [dpop, frontend, device-proof, vietnamese-docs, rollout]

requires:
  - phase: 07-03
    provides: one-time asymmetric internal tool capabilities
  - phase: 07-04
    provides: backend DPoP proof and `cnf.jkt` enforcement
provides:
  - browser-held device proof helper
  - frontend auth-session DPoP header integration
  - Vietnamese rollout and limitation documentation
affects: [auth-shell, chat-shell, admin-api, docs]

tech-stack:
  added: []
  patterns: [memory-only browser proof keys, per-request DPoP headers, re-auth on proof loss]

key-files:
  created:
    - frontend/lib/device-proof.ts
  modified:
    - frontend/lib/auth-session.ts
    - frontend/tests/auth-session.test.ts
    - docs/security.vi.md
    - docs/runbook.vi.md
    - docs/limitations.vi.md

key-decisions:
  - "Browser proof private keys remain memory-only and are not written to localStorage or sessionStorage."
  - "Proof generation failure moves the auth shell to session_expired instead of sending bearer-only requests."
  - "Vietnamese docs describe re-auth expectations and explicitly keep WebAuthn step-up deferred."

patterns-established:
  - "AuthSessionController obtains DPoP proof headers through a single device-proof provider."
  - "Frontend tests can inject a proof provider to assert request contracts without depending on WebCrypto internals."

requirements-completed: [AUTH-11, AUTH-12, PRODREADY-06, OBS-08]

duration: 32min
completed: 2026-06-25
---

# Phase 07-05: Frontend Proof Rollout and Docs Summary

**The browser auth controller now attaches DPoP-style proof headers and Vietnamese docs explain replay hardening, key loss, and deferred limits.**

## Performance

- **Duration:** 32 min
- **Started:** 2026-06-24T23:33:00Z
- **Completed:** 2026-06-24T23:39:00Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- Added `frontend/lib/device-proof.ts` for memory-only browser RSA proof keys and per-request DPoP JWT headers.
- Wired login, refresh, logout, `/me`, and protected requests through the device proof provider.
- Ensured proof generation failure clears local session state and forces re-auth instead of bearer fallback.
- Added frontend tests for DPoP header attachment and proof-loss behavior.
- Updated Vietnamese security, runbook, and limitation docs for PKCE, DPoP, re-auth, replay evidence, and WebAuthn deferral.

## Task Commits

1. **Task 1: Lock proof-bound frontend session behavior in auth-shell tests** - `4e22d21` (test)
2. **Task 2: Add browser-held device proof helpers and wire the auth session controller** - `49f8519` (feat)
3. **Task 3: Update Vietnamese security, runbook, and limitation docs** - `f39f415` (docs)

## Files Created/Modified

- `frontend/lib/device-proof.ts` - Browser-held proof key and DPoP JWT helper.
- `frontend/lib/auth-session.ts` - DPoP integration for session and protected request paths.
- `frontend/tests/auth-session.test.ts` - Regression tests for proof headers and proof loss.
- `docs/security.vi.md` - Security model update for PKCE, DPoP, and one-time tool capabilities.
- `docs/runbook.vi.md` - Operator guidance for DPoP replay/mismatch and OAuth transaction replay.
- `docs/limitations.vi.md` - Remaining limits, including WebAuthn deferral and re-auth on proof loss.

## Decisions Made

- Used WebCrypto directly instead of adding a frontend crypto dependency.
- Kept the proof key in module memory only; this favors replay resistance over silent session survival after key loss.
- Reused the existing `session_expired` UX state for proof-loss recovery because that is the truthful user action: sign in again.

## Deviations from Plan

### Auto-fixed Issues

**1. Proof signing changed the timing of concurrent refresh tests**
- **Found during:** Task 2
- **Issue:** Two simultaneous protected requests could trigger a second refresh if the first refresh completed just before the second reached the 401 handler.
- **Fix:** `requestWithRefresh()` now reuses a newly refreshed token when the local token changed after the first attempt.
- **Verification:** Frontend auth-session tests passed.
- **Committed in:** `49f8519`

**Total deviations:** 1 auto-fixed
**Impact on plan:** Improved existing refresh behavior while preserving the proof-bound contract.

## Issues Encountered

- Requirement IDs `AUTH-11`, `AUTH-12`, `PRODREADY-06`, and `OBS-08` were not found in the local requirements matrix, matching the prior Phase 07 traceability gap.
- The plan command includes `--runInBand`, but the frontend test script is `tsx --test`; npm passed through the actual file arguments and the target tests ran successfully.

## User Setup Required

None for local tests. Users should rebuild/restart the frontend and backend to exercise DPoP-enabled flows end to end.

## Next Phase Readiness

Phase 07 is complete. A future hardening slice can add WebAuthn step-up and user-facing multi-device session management.

---
*Phase: 07-sender-constrained-sessions-and-cryptographic-hardening*
*Completed: 2026-06-25*
