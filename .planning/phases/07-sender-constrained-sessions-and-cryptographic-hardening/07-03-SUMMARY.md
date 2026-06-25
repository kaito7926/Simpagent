---
phase: 07-sender-constrained-sessions-and-cryptographic-hardening
plan: "03"
subsystem: security
tags: [jwt, rs256, replay, search, python, sandbox]

requires:
  - phase: 07-01
    provides: replay journal storage and consume-once repository helper
provides:
  - replay-aware search worker capability consumption
  - asymmetric Python sandbox capability issuance and verification
  - replay denial tests for search and Python tool boundaries
affects: [search-worker, python-sandbox, compose, production-profile]

tech-stack:
  added: [PyJWT in sandbox image]
  patterns: [RS256 internal capability JWTs, consume-once jti enforcement, public-key sandbox verification]

key-files:
  created: []
  modified:
    - backend/app/security/search_capability.py
    - backend/app/security/tool_capabilities.py
    - backend/app/ai/search_worker/service.py
    - sandbox/server.py
    - backend/tests/security/test_search_capability_token.py
    - backend/tests/security/test_python_request_hardening.py

key-decisions:
  - "Search worker execution now consumes capability jti values through the shared replay journal before provider calls."
  - "Python sandbox capabilities now use backend-issued RS256 JWTs verified by sandbox public key instead of shared-secret HMAC for the hardened success path."
  - "The sandbox keeps its legacy HMAC helper only to prove old symmetric bearer material is rejected."

patterns-established:
  - "Capability validation remains separate from live-boundary consume-once enforcement."
  - "Tests use backend-issued capabilities for sandbox success paths and legacy helper tokens only for negative assertions."

requirements-completed: [AGNT-08, AGNT-09, OBS-08]

duration: 50min
completed: 2026-06-25
---

# Phase 07-03: Asymmetric One-Time Tool Capabilities Summary

**Search and Python worker capabilities are RS256 audience-bound artifacts with replay denial at the live execution boundary.**

## Performance

- **Duration:** 50 min
- **Started:** 2026-06-24T22:33:00Z
- **Completed:** 2026-06-24T23:23:00Z
- **Tasks:** 3
- **Files modified:** 14

## Accomplishments

- Added worker-level search capability replay denial backed by `security_replay_records`.
- Converted Python capability issuance from HMAC bearer material to backend RS256 JWTs bound to execution id, profile, code hash, and state snapshot hash.
- Updated the sandbox verifier to use a configured public key and reject second-use `jti` values before runtime launch.
- Added negative tests proving search replay denial, Python replay denial, and legacy symmetric-token rejection.

## Task Commits

1. **Task 1: Lock search and Python capability replay behavior in security tests** - `0034b69` (test)
2. **Task 2: Harden search capability issuance and worker consume-once validation** - `e054a23` (feat)
3. **Task 3: Convert Python capability verification to asymmetric consume-once semantics** - `e054a23` (feat)

## Files Created/Modified

- `backend/app/security/search_capability.py` - Added replay-aware async consume helper and safe mismatch evidence.
- `backend/app/ai/search_worker/service.py` - Consumes search capabilities before Gemini/Firecrawl execution.
- `backend/app/security/tool_capabilities.py` - Issues RS256 Python capability JWTs.
- `sandbox/server.py` - Verifies Python capabilities with a public key and tracks consumed `jti` values.
- `sandbox/Dockerfile` - Installs PyJWT for sandbox verification.
- `compose.yaml` and `.env.example` - Document and wire the sandbox public-key trust path.
- `backend/tests/security/test_search_capability_token.py` - Adds worker-bound replay denial coverage.
- `backend/tests/security/test_python_request_hardening.py` - Adds replay and legacy-token denial coverage.

## Decisions Made

- Kept `validate_search_capability()` stateless for low-level token tests while requiring `consume_search_capability_once()` at worker execution.
- Passed the app session factory into the startup search worker and disposed fallback engines for directly constructed test workers.
- Left the old sandbox HMAC issuer as a negative-test fixture only; successful verification no longer depends on `python_capability_secret`.

## Deviations from Plan

### Auto-fixed Issues

**1. Sandbox image lacked JWT verification dependency**
- **Found during:** Task 3
- **Issue:** The sandbox previously verified HMAC manually and did not install PyJWT.
- **Fix:** Added `PyJWT[crypto]` to `sandbox/Dockerfile`.
- **Verification:** Sandbox module import and Python capability tests passed.
- **Committed in:** `e054a23`

**2. Direct search worker tests leaked temporary DB engines**
- **Found during:** Adjacent verification
- **Issue:** Directly constructed workers without an injected session factory opened fallback engines and left connections for pytest to report.
- **Fix:** Fallback factories are now disposed after consume-once validation.
- **Verification:** Adjacent search and sandbox tests passed.
- **Committed in:** `e054a23`

**Total deviations:** 2 auto-fixed
**Impact on plan:** Both changes support the planned hardened boundary and local verification path.

## Issues Encountered

- Ruff is not installed in the backend test image, so syntax checks used `compileall` plus a sandbox import check instead.
- The production-profile test cannot read repo-root `.env.example` inside the current backend-test Compose mount, but the affected assertions were updated to match the public-key sandbox boundary.
- Requirement IDs `AGNT-08`, `AGNT-09`, and `OBS-08` were not found in the local requirements matrix, matching the Phase 07 traceability gap observed in prior plans.

## User Setup Required

None - no external service configuration required. Local users should rebuild the sandbox image so PyJWT and the public-key verifier are present.

## Next Phase Readiness

07-04 can build DPoP-style browser session proof checks on top of the replay journal and the established one-time internal capability pattern.

---
*Phase: 07-sender-constrained-sessions-and-cryptographic-hardening*
*Completed: 2026-06-25*
