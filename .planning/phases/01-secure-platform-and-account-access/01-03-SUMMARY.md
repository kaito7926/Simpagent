---
phase: 01-secure-platform-and-account-access
plan: "03"
subsystem: ui
tags: [nextjs, kong, compose, account-access, smoke]
requires:
  - phase: 01-02
    provides: working backend registration/login/me slice
provides:
  - Same-origin frontend -> Kong -> FastAPI -> PostgreSQL walking skeleton
  - Main Compose topology and DB-less Kong routing
affects: [01-06, 01-08]
tech-stack:
  added: [Next.js runtime image, Kong DB-less config, main Compose topology]
  patterns: [same-origin API routing, memory-only browser access token]
key-files:
  created: [compose.yaml, kong/kong.yml, frontend/app/page.tsx, frontend/Dockerfile]
  modified: [frontend/components/account-access/AccountAccessShell.tsx]
key-decisions:
  - "Use Kong as the single public origin for frontend-visible app and API traffic."
  - "Keep the browser access token in memory while refresh remains cookie-backed."
patterns-established:
  - "Route /api, /health, /ready, and / through the assembled Compose/Kong topology."
  - "Keep Phase 1 UI limited to account access only; no later-phase controls."
requirements-completed: [PLAT-01, PLAT-02, AUTH-01, AUTH-02, AUTH-08, AUTH-09]
duration: combined-session
completed: 2026-06-10
---

# Phase 01: Plan 03 Summary

**The first real user-visible path now works through Next.js, Kong, FastAPI, and PostgreSQL from a fresh Compose startup.**

## Performance

- **Duration:** Combined implementation session across the Phase 1 completion pass
- **Started:** 2026-06-09T11:51:47Z
- **Completed:** 2026-06-10T00:21:01+07:00
- **Tasks:** 3
- **Files modified:** 8+

## Accomplishments
- Built the main Compose topology with PostgreSQL, migration jobs, backend, frontend, Kong, and sandbox.
- Added DB-less Kong routing for frontend and API paths.
- Completed the walking-skeleton smoke path and proved register -> login -> me through the public edge.

## Task Commits

Implementation was delivered in the shared Phase 1 completion commit:

1. **Task 1: Create the audited Next.js account-access scaffold** - `bd9a2fd` (feat)
2. **Task 2: Implement the thinnest real registration, login, and me browser path** - `bd9a2fd` (feat)
3. **Task 3: Run the walking skeleton through the required same-origin topology** - `bd9a2fd` (feat)

**Plan metadata:** `bd9a2fd` (feat: complete account access foundation)

## Files Created/Modified
- `compose.yaml` - Main Phase 1 runtime graph and service ordering.
- `kong/kong.yml` - DB-less Kong services/routes for frontend and backend.
- `frontend/Dockerfile` - Frontend runtime image and dependency install flow.
- `frontend/app/layout.tsx` - Root layout with local font setup.
- `frontend/app/page.tsx` - Phase 1 public route entry.
- `frontend/app/globals.css` - Phase 1 visual token and layout baseline.
- `frontend/components/account-access/BrandLockup.tsx` - Product framing for the account-access page.
- `backend/tests/smoke/test_account_access_skeleton.py` - End-to-end walking-skeleton verification.

## Decisions Made
- Exposed only Kong on the host while keeping database/backend/sandbox private.
- Allowed the browser-origin and Kong-origin pair in backend settings so smoke traffic can exercise the intended flow.

## Deviations from Plan

### Auto-fixed Issues

**1. Runtime topology startup defects**
- **Found during:** Compose smoke verification
- **Issue:** PostgreSQL 18 volume mount target and inline sandbox server command caused startup failures.
- **Fix:** Switched the Postgres volume mount to `/var/lib/postgresql` and moved the sandbox server into `sandbox/server.py`.
- **Verification:** `docker compose up --build --wait`
- **Committed in:** `bd9a2fd`

---

**Total deviations:** 1 auto-fixed
**Impact on plan:** Required to make the planned topology boot reliably under PostgreSQL 18 and Docker Compose.

## Issues Encountered
- Local npm install from the host shell was unreliable in this environment, so the frontend image was made self-sufficient for dependency installation inside Docker.

## User Setup Required
None - no external service configuration required beyond the repo templates.

## Next Phase Readiness
- Browser session lifecycle and readiness/demo UI now have a stable assembled route to build on.
- Final topology smoke infrastructure exists for end-of-phase verification.

---
*Phase: 01-secure-platform-and-account-access*
*Completed: 2026-06-10*
