---
phase: 05-gateway-administration-and-security-evidence
plan: "08"
subsystem: infra
tags: [gateway, oauth, cloudflare, smoke-tests, production-profile, docs]

requires:
  - phase: 05-gateway-administration-and-security-evidence
    provides: OAuth providers, Kong hardening, admin evidence surfaces, and auth-shell readiness from plans 05-05 through 05-09
provides:
  - Final Phase 5 smoke/profile tests for local auth, OAuth readiness, gateway/profile, admin bootstrap, chat/Search/Python coverage packaging
  - Environment-only small-production profile keys for OAuth, public origins, trusted proxies, secure cookies, and optional Cloudflare assumptions
  - Compose small-production profile wiring and repo-level evidence mounts for backend verification
  - Vietnamese operator runbook for local primary path, optional Cloudflare edge, bootstrap, migration, backup, restore, rollback, smoke checks, and prototype limits
affects: [phase-05, phase-06, gateway, deployment, documentation, smoke]

tech-stack:
  added: []
  patterns:
    - Read-only repo evidence mounts into backend test container for profile validation
    - Optional Cloudflare edge documented as an operator path, not a runtime dependency

key-files:
  created:
    - .planning/phases/05-gateway-administration-and-security-evidence/05-08-SUMMARY.md
  modified:
    - .env.example
    - compose.yaml
    - README.md
    - backend/tests/smoke/_helpers.py
    - backend/tests/smoke/test_oauth_google_flow.py
    - backend/tests/smoke/test_oauth_github_flow.py
    - backend/tests/smoke/test_topology.py
    - backend/tests/integration/gateway/test_production_profile.py
    - backend/tests/integration/cli/test_provisioning.py

key-decisions:
  - "The small-production profile stays environment-only and optional; local Compose remains the primary demo path."
  - "Cloudflare is documented as an optional edge in front of Kong with explicit trusted-proxy/source-IP assumptions, not as mandatory enterprise protection."
  - "Backend profile tests read root-level deployment artifacts through read-only Compose mounts instead of copying production docs into the backend package."

patterns-established:
  - "Profile tests validate `.env.example`, `compose.yaml`, and README through a mounted repo evidence directory."
  - "Smoke OAuth tests assert provider readiness and start-route secret non-leakage while allowing unconfigured providers."

requirements-completed: [GATE-07, GATE-08, PRODREADY-01, PRODREADY-02, PRODREADY-03, PRODREADY-04, PRODREADY-05]

duration: 13 min
completed: 2026-06-16
---

# Phase 05 Plan 08: Small Production Profile and Operator Evidence Summary

**Environment-driven Phase 5 production-profile slice with optional Cloudflare guidance, assembled smoke coverage, and Vietnamese operator runbook.**

## Performance

- **Duration:** 13 min
- **Started:** 2026-06-16T10:04:49Z
- **Completed:** 2026-06-16T10:17:10Z
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments

- Added final smoke/profile coverage for OAuth readiness, provider start routes, local login topology, production profile keys, Compose wiring, and admin bootstrap CLI behavior.
- Added `.env.example` and `compose.yaml` small-production configuration for public app/API origins, trusted proxy CIDRs, secure cookies, OAuth clients, secret-file paths, and optional Cloudflare variables.
- Updated Vietnamese README with local-primary deployment guidance, optional `Client -> Cloudflare -> Kong -> FastAPI -> PostgreSQL/LLM/Tools` route, trusted proxy/source-IP assumptions, migration/bootstrap/backup/restore/rollback steps, smoke matrix, and 100-users/month prototype limits.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add RED smoke coverage for the final assembled Phase 5 paths** - `92e0fad` (test)
2. **Task 2: Update the environment template and Compose profile for the small production target** - `bf995cc` (feat)
3. **Task 3: Document the optional Cloudflare edge and final Phase 5 operator runbook in Vietnamese** - `68c209d` (docs)

**Plan metadata:** pending final metadata commit

## Files Created/Modified

- `.env.example` - Added Phase 5 small-production environment template keys without real secrets.
- `compose.yaml` - Added read-only repo evidence mounts and optional `backend-small-production` profile wiring.
- `README.md` - Added Vietnamese Phase 5 operator runbook, optional Cloudflare path, smoke commands, recovery steps, and explicit limits.
- `backend/tests/smoke/_helpers.py` - Added OAuth/readiness smoke helper assertions.
- `backend/tests/smoke/test_oauth_google_flow.py` - Added Google OAuth readiness/start smoke contract.
- `backend/tests/smoke/test_oauth_github_flow.py` - Added GitHub OAuth readiness/start smoke contract.
- `backend/tests/smoke/test_topology.py` - Reused shared helpers and made local smoke registration deterministic.
- `backend/tests/integration/gateway/test_production_profile.py` - Added env/Compose production-profile assertions.
- `backend/tests/integration/cli/test_provisioning.py` - Added bootstrap-admin CLI safety coverage.

## Decisions Made

- The production profile is intentionally a small, single-node Compose profile for demonstration and operator rehearsal, not a production hosting guarantee.
- Cloudflare guidance is documentation and environment wiring only; the local stack does not require Cloudflare and the backend remains the authorization authority.
- The backend container validates root-level profile artifacts through explicit read-only mounts so tests exercise the same files operators use.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Rebuilt backend image so verification used current test code**
- **Found during:** Task 1
- **Issue:** The initial Docker verification used a previously built backend image, so the new RED tests were not present and the gate passed unexpectedly.
- **Fix:** Rebuilt the backend image before rerunning the RED and subsequent GREEN verification commands.
- **Files modified:** None
- **Verification:** RED rerun failed on missing repo-level profile evidence; later plan-level verification passed.
- **Committed in:** Not applicable; build environment correction only.

**2. [Rule 1 - Test Scope] Kept provisioning tests aligned to Task 2 scope**
- **Found during:** Task 2
- **Issue:** The RED provisioning test initially asserted README runbook content even though README updates were assigned to Task 3, which would have blocked Task 2 for the wrong reason.
- **Fix:** Changed the provisioning assertion to cover bootstrap-admin CLI behavior without secret echo; README runbook content was completed in Task 3.
- **Files modified:** `backend/tests/integration/cli/test_provisioning.py`
- **Verification:** `docker compose run --rm backend python -m pytest tests/integration/gateway/test_production_profile.py tests/integration/cli/test_provisioning.py -q` passed.
- **Committed in:** `bf995cc`

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 test-scope correction)  
**Impact on plan:** Both corrections preserved the intended task boundaries and verification fidelity. No production behavior was broadened beyond the plan.

## Issues Encountered

- Smoke tests in the specified commands skip unless `SIMPAGENT_RUN_SMOKE=true`; this is existing harness behavior. Plan-level verification still passed with `13 passed, 3 skipped`.

## Verification

- `docker compose build backend` - passed before containerized verification after test edits.
- `docker compose run --rm backend python -m pytest tests/smoke/test_oauth_google_flow.py tests/smoke/test_oauth_github_flow.py tests/smoke/test_topology.py tests/integration/gateway/test_production_profile.py tests/integration/cli/test_provisioning.py -q` - `13 passed, 3 skipped`.
- `docker compose config -q` - passed.
- Task 2 gate: `docker compose run --rm backend python -m pytest tests/integration/gateway/test_production_profile.py tests/integration/cli/test_provisioning.py -q && docker compose config -q` - passed.
- Task 3 gate: `docker compose run --rm backend python -m pytest tests/smoke/test_oauth_google_flow.py tests/smoke/test_oauth_github_flow.py tests/smoke/test_topology.py -q` - `3 skipped` because assembled smoke mode was not enabled.

## Known Stubs

None. The stub-pattern scan found only `trusted_proxy_cidrs=[]` in a negative test case.

## Threat Flags

None. The new environment, Compose, documentation, and smoke-test surfaces match the plan threat model for production-profile and optional Cloudflare/trusted-proxy evidence.

## Issues Encountered

None beyond the auto-fixed verification/test-scope issues documented above.

## User Setup Required

None for local demo. Real small-production or OAuth runs require operator-provided secrets and provider client credentials as documented in README and `.env.example`.

## Next Phase Readiness

Phase 5 now has its final small-production profile, optional edge documentation, and assembled smoke/profile gates. Ready for Phase 5 verification/UAT and then Phase 6 adversarial verification and Vietnamese delivery documentation.

## Self-Check: PASSED

- Summary file created at `.planning/phases/05-gateway-administration-and-security-evidence/05-08-SUMMARY.md`.
- Task commits found: `92e0fad`, `bf995cc`, `68c209d`.
- Key files exist: `.env.example`, `compose.yaml`, `README.md`, smoke tests, profile tests, provisioning tests.
- Plan-level verification passed before summary creation.

---
*Phase: 05-gateway-administration-and-security-evidence*
*Completed: 2026-06-16*
