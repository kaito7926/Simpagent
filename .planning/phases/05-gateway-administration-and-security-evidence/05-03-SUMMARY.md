---
phase: 05-gateway-administration-and-security-evidence
plan: "03"
subsystem: auth
tags: [fastapi, oauth, github, authlib, jwt, refresh-token, readiness]

requires:
  - phase: 05-gateway-administration-and-security-evidence
    provides: Google OAuth backend routes, Authlib dependency approval, OAuth service/session pattern, and readiness capability pattern
provides:
  - Backend-owned GitHub OAuth start and callback routes
  - GitHub provider adapter with stable subject and verified primary email resolution
  - Subject-first OAuth login completion for GitHub identities
  - Fail-closed local account linking and provisioning coverage for unsafe GitHub identity states
  - GitHub OAuth readiness state for downstream auth-shell wiring
affects: [auth-shell, readiness, oauth, identity, phase-05]

tech-stack:
  added: []
  patterns:
    - Backend-owned OAuth authorization-code routes shared across Google and GitHub
    - Per-provider signed temporary OAuth state cookie
    - Provider identity persisted by issuer and subject before email-based linking
    - OAuth login completion reuses existing first-party session issuance

key-files:
  created:
    - backend/app/identity/providers/github.py
    - backend/tests/integration/auth/test_github_oauth.py
    - backend/tests/integration/auth/test_oauth_account_linking.py
    - backend/tests/smoke/test_oauth_github_flow.py
    - .planning/phases/05-gateway-administration-and-security-evidence/05-03-USER-SETUP.md
  modified:
    - backend/app/api/routes/auth_oauth.py
    - backend/app/identity/oauth_service.py
    - backend/app/db/repositories/accounts.py
    - backend/app/core/config.py
    - backend/app/core/provider_status.py
    - backend/app/schemas/health.py
    - backend/app/api/routes/health.py
    - backend/tests/security/test_secret_leakage.py

key-decisions:
  - "GitHub OAuth reuses the existing backend OAuth service and first-party refresh-cookie session model."
  - "GitHub provider identity is resolved by stable GitHub user ID before any verified-email linking attempt."
  - "GitHub email linking requires a verified primary email; missing, unverified, or conflicting identity fails closed."
  - "GitHub readiness is exposed as `components.oauth_github` for the later auth-shell plan instead of wiring frontend CTA behavior here."

patterns-established:
  - "OAuth route extension: add provider-specific start/callback endpoints while sharing signed state-cookie and redirect helpers."
  - "OAuth provider adapter: map external provider token/user/email responses into stable issuer/subject/email identity objects."
  - "Account-linking safety: subject lookup happens first; verified normalized email is used only for first-link or provisioning cases."

requirements-completed: [IDEN-03, IDEN-07, IDEN-08]

duration: 13 min
completed: 2026-06-16
---

# Phase 05 Plan 03: GitHub OAuth Backend Summary

**Backend-owned GitHub OAuth login with verified primary-email resolution, stable subject persistence, fail-closed account linking, and existing refresh-cookie session issuance**

## Performance

- **Duration:** 13 min
- **Started:** 2026-06-16T04:24:56Z
- **Completed:** 2026-06-16T04:38:00Z
- **Tasks:** 2 completed
- **Files modified:** 14

## Accomplishments

- Added RED coverage for GitHub start/callback behavior, safe auto-linking, new-user provisioning, subject-first login resolution, unsafe identity denial, secret leakage, and assembled-stack smoke exposure.
- Implemented `GitHubOAuthProvider` using Authlib to exchange an auth code, fetch GitHub user identity, and require a verified primary email from the GitHub emails API before linking or provisioning.
- Extended backend OAuth routes with `/api/auth/oauth/github/start` and `/api/auth/oauth/github/callback`, including per-provider state cookies and the same HttpOnly refresh cookie plus CSRF cookie session model as local and Google login.
- Exposed `components.oauth_github` in readiness so Plan 05-09 can wire provider CTA availability from backend truth.

## Task Commits

Each task was committed atomically:

1. **Task 1: Write RED tests for GitHub and fail-closed account linking** - `208db98` (test)
2. **Task 2: Implement GitHub OAuth and fail-closed linking rules** - `f9a0938` (feat)

**Plan metadata:** committed after this summary.

## Files Created/Modified

- `backend/app/identity/providers/github.py` - GitHub OAuth adapter with authorization URL generation, token exchange, user lookup, and verified primary email resolution.
- `backend/app/api/routes/auth_oauth.py` - Added GitHub start/callback routes and generalized OAuth state cookie handling by provider.
- `backend/app/identity/oauth_service.py` - Widened OAuth completion to GitHub identities while keeping subject-first account resolution and shared session issuance.
- `backend/app/db/repositories/accounts.py` - Added explicit `get_user_bundle_by_identity_subject` helper for stable `(issuer, subject)` lookup.
- `backend/app/core/config.py` - Added GitHub client ID, secret, and redirect URI settings plus `github_oauth_configured`.
- `backend/app/core/provider_status.py`, `backend/app/schemas/health.py`, `backend/app/api/routes/health.py` - Added `oauth_github` readiness state.
- `backend/tests/integration/auth/test_github_oauth.py` - Covers configured/unconfigured GitHub routes, successful provisioning, subject reuse, and missing/unverified denial.
- `backend/tests/integration/auth/test_oauth_account_linking.py` - Covers safe auto-linking, new-user provisioning, subject-first resolution, ambiguous denial, and conflicting identity denial.
- `backend/tests/security/test_secret_leakage.py` - Adds GitHub OAuth failure canary assertions.
- `backend/tests/smoke/test_oauth_github_flow.py` - Adds assembled-stack smoke coverage for GitHub OAuth route exposure.
- `.planning/phases/05-gateway-administration-and-security-evidence/05-03-USER-SETUP.md` - Documents GitHub OAuth dashboard and environment setup that requires human account access.

## Decisions Made

- GitHub login uses the same OAuth service and refresh-cookie session issuance path as Google and local login; no second browser session model was introduced.
- GitHub account resolution uses the stable GitHub user ID as the provider subject. Provider email is treated only as linking/provisioning evidence.
- The GitHub adapter requires a verified primary email from GitHub's email endpoint. Missing, unverified, or conflicting identities return safe generic OAuth failure responses and create no new session.
- Frontend provider CTA wiring remains out of scope for this backend plan; readiness exposes `oauth_github` for Plan 05-09.

## Deviations from Plan

None - plan executed exactly as written.

**Total deviations:** 0 auto-fixed.
**Impact on plan:** No scope change.

## Issues Encountered

- The backend Compose image copies source during build, so the RED tests were initially invisible in the stale image. Rebuilding `backend` made the failing tests visible and then made the implemented suite green.
- `python -m ruff check ...` could not run in the backend container because `ruff` is not installed there. This was not part of the plan verification gate; the required pytest checks passed.

## Authentication Gates

None.

## Known Stubs

None. Empty-list assertions in the new tests are negative security assertions, not runtime stubs.

## Verification

- RED gate: `docker compose run --rm backend python -m pytest tests/integration/auth/test_github_oauth.py tests/integration/auth/test_oauth_account_linking.py tests/security/test_secret_leakage.py tests/smoke/test_oauth_github_flow.py -q` failed before implementation with `ModuleNotFoundError: No module named 'app.identity.providers.github'`.
- GREEN gate: `docker compose run --rm backend python -m pytest tests/integration/auth/test_github_oauth.py tests/integration/auth/test_oauth_account_linking.py tests/security/test_secret_leakage.py tests/smoke/test_oauth_github_flow.py -q` passed with `16 passed, 1 skipped`; the skipped smoke test requires `SIMPAGENT_RUN_SMOKE=true`.
- Readiness regression: `docker compose run --rm backend python -m pytest tests/integration/test_health.py -q` passed with `2 passed`.
- Lint attempt: `docker compose run --rm backend python -m ruff check ...` could not run because `ruff` is not installed in the backend image.

## TDD Gate Compliance

- RED commit present: `208db98` (`test(05-03): add failing GitHub OAuth linking tests`)
- GREEN commit present: `f9a0938` (`feat(05-03): implement GitHub OAuth backend flow`)
- Refactor commit: not needed.

## User Setup Required

External GitHub OAuth credentials require manual dashboard configuration. See `.planning/phases/05-gateway-administration-and-security-evidence/05-03-USER-SETUP.md` for:

- `GITHUB_CLIENT_ID`
- `GITHUB_CLIENT_SECRET`
- `GITHUB_REDIRECT_URI`
- GitHub OAuth app callback configuration

## Next Phase Readiness

Backend GitHub OAuth is ready for Plan 05-09 auth-shell CTA/readiness wiring. Remaining Phase 05 work can depend on `components.oauth_github` and the GitHub backend routes without adding placeholder frontend behavior.

## Self-Check: PASSED

- Summary file path is present in this close-out.
- User setup file exists for the plan frontmatter `user_setup`.
- Task commits exist: `208db98`, `f9a0938`.
- Key created files exist: `github.py`, GitHub integration tests, account-linking tests, smoke test, and setup note.
- Plan-level verification passed.

---
*Phase: 05-gateway-administration-and-security-evidence*
*Completed: 2026-06-16*
