---
phase: 05-gateway-administration-and-security-evidence
plan: "09"
subsystem: auth
tags: [frontend, oauth, google, github, readiness, account-access]

requires:
  - phase: 05-gateway-administration-and-security-evidence
    provides: Google OAuth backend start routes and `components.oauth_google` readiness
  - phase: 05-gateway-administration-and-security-evidence
    provides: GitHub OAuth backend start routes and `components.oauth_github` readiness
provides:
  - Shared auth-shell Google and GitHub CTA states derived from backend readiness
  - Browser-side OAuth start helper for backend-owned provider routes
  - Mixed provider readiness coverage preserving local login/register
affects: [auth-shell, readiness, oauth, phase-05]

tech-stack:
  added: []
  patterns:
    - Readiness-derived provider CTA state
    - Redirect-only browser OAuth start helper
    - Provider CTAs above local credentials divider

key-files:
  created:
    - frontend/tests/account-access-oauth.test.tsx
  modified:
    - frontend/lib/auth-session.ts
    - frontend/lib/readiness.ts
    - frontend/components/account-access/AuthCard.tsx
    - frontend/components/account-access/AccountAccessShell.tsx

key-decisions:
  - "OAuth provider buttons are derived from backend readiness components instead of hardcoded frontend assumptions."
  - "OAuth starts by browser navigation to backend-owned start routes and does not persist session material in browser storage."
  - "Unconfigured Google or GitHub providers remain visible as factual disabled states while local credentials stay available."

patterns-established:
  - "Frontend OAuth provider state: `oauthProviderState(readiness, provider)` maps backend readiness into CTA label, enabled state, and unavailable copy."
  - "Browser OAuth start: `beginOAuth(provider)` redirects to `/api/auth/oauth/{provider}/start` without token storage."

requirements-completed: [IDEN-06, IDEN-07]

duration: 7 min
completed: 2026-06-16
---

# Phase 05 Plan 09: Shared OAuth Auth-Shell CTA Summary

**Readiness-driven Google and GitHub sign-in CTAs with backend-owned OAuth starts and preserved local credentials**

## Performance

- **Duration:** 7 min
- **Started:** 2026-06-16T09:51:39Z
- **Completed:** 2026-06-16T09:58:50Z
- **Tasks:** 2 completed
- **Files modified:** 5

## Accomplishments

- Added RED frontend coverage for configured, unconfigured, mixed, and all-disabled Google/GitHub OAuth readiness states.
- Added `OAuthProviderId`, `beginOAuth(provider)`, and provider-state helpers for readiness-derived frontend CTA behavior.
- Replaced the permanently disabled placeholder social buttons with factual Google/GitHub CTAs above the local credentials divider.
- Preserved local login/register availability in every provider readiness state and kept OAuth session material out of browser storage.

## Task Commits

Each task was committed atomically:

1. **Task 1: Write RED tests for shared auth-shell OAuth CTA and readiness states** - `f826f99` (test)
2. **Task 2: Wire the shared auth shell to backend readiness and OAuth start routes** - `3684537` (feat)

**Plan metadata:** committed after this summary.

## Files Created/Modified

- `frontend/tests/account-access-oauth.test.tsx` - Covers provider CTA ordering, mixed readiness states, local credential preservation, and storage-free backend OAuth start navigation.
- `frontend/lib/auth-session.ts` - Adds OAuth provider types and `beginOAuth(provider)` route mapping for backend-owned start endpoints.
- `frontend/lib/readiness.ts` - Adds OAuth readiness labels and `oauthProviderState(readiness, provider)`.
- `frontend/components/account-access/AuthCard.tsx` - Renders provider-state driven Google/GitHub CTAs above the local credentials divider.
- `frontend/components/account-access/AccountAccessShell.tsx` - Computes OAuth provider states from readiness and starts provider navigation from the shared shell.

## Decisions Made

- Provider CTA availability is based on `components.oauth_google` and `components.oauth_github`; frontend code does not infer provider configuration from environment variables or hardcoded assumptions.
- Unconfigured providers render factual disabled copy (`Google sign-in is not configured`, `GitHub sign-in is not configured`) instead of fake placeholder controls.
- OAuth start is a browser redirect to backend-owned routes only; access and refresh tokens remain outside browser storage.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Used frontend-relative test paths for the npm test runner**
- **Found during:** Task 1 (Write RED tests for shared auth-shell OAuth CTA and readiness states)
- **Issue:** The literal plan command with `frontend/tests/...` paths failed before executing tests because `npm --prefix frontend` runs the script from the `frontend/` package directory.
- **Fix:** Used the equivalent frontend-relative paths `tests/account-access-oauth.test.tsx tests/auth-session.test.ts tests/readiness.test.ts` for RED and GREEN verification.
- **Files modified:** None
- **Verification:** The frontend-relative command produced the expected RED failures before implementation and passed after implementation.
- **Committed in:** N/A

---

**Total deviations:** 1 auto-fixed (1 blocking workflow issue).
**Impact on plan:** No product scope change. The same test files and behavioral gates were verified.

## Issues Encountered

- The exact plan command form failed due package-relative path resolution under `npm --prefix frontend`; the equivalent frontend-relative command was used for actual verification.

## Authentication Gates

None.

## Known Stubs

None. Placeholder attributes in local email/password inputs are normal form hints, not disconnected UI stubs. Storage-trap references in tests assert that OAuth start does not use `localStorage` or `sessionStorage`.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: browser_redirect | `frontend/lib/auth-session.ts` | Added browser OAuth redirects to backend-owned start routes; covered by storage-trap tests and backend route allowlist. |

## Verification

- RED gate: `npm --prefix frontend test -- tests/account-access-oauth.test.tsx tests/auth-session.test.ts tests/readiness.test.ts` failed before implementation with missing `oauthProviderState` and `beginOAuth`.
- GREEN gate: `npm --prefix frontend test -- tests/account-access-oauth.test.tsx tests/auth-session.test.ts tests/readiness.test.ts` passed with `14 passed`.
- TypeScript: `npm --prefix frontend run typecheck` passed.
- Acceptance checks: `rg` confirmed `beginOAuth`, `oauthProviderState`, `oauth_google`, `oauth_github`, `Continue with Google`, `Continue with GitHub`, and `Or use local credentials` are present in the intended frontend files.

## User Setup Required

None - no new external service configuration required. Google and GitHub credential setup remains documented in the 05-02 and 05-03 user setup notes.

## Next Phase Readiness

The shared auth shell can now truthfully expose Google and GitHub sign-in based on backend readiness. Phase 05 still has 05-08 production profile and smoke evidence work outstanding.

## Self-Check: PASSED

- Summary file path is present in this close-out.
- Task commits exist: `f826f99`, `3684537`.
- Key created file exists: `frontend/tests/account-access-oauth.test.tsx`.
- Key modified files exist: `frontend/lib/auth-session.ts`, `frontend/lib/readiness.ts`, `frontend/components/account-access/AuthCard.tsx`, and `frontend/components/account-access/AccountAccessShell.tsx`.
- Plan-level verification passed with the frontend-relative path form required by the package runner.

---
*Phase: 05-gateway-administration-and-security-evidence*
*Completed: 2026-06-16*
