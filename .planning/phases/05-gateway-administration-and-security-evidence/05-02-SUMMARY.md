---
phase: 05-gateway-administration-and-security-evidence
plan: "02"
subsystem: auth
tags: [fastapi, oauth, google, authlib, jwt, refresh-token, readiness]

requires:
  - phase: 01-secure-platform-and-account-access
    provides: Local account model, identity table, RS256 access tokens, refresh families, and CSRF cookies
  - phase: 05-gateway-administration-and-security-evidence
    provides: Authlib provenance approval checkpoint
provides:
  - Backend-owned Google OAuth start and callback routes
  - Verified Google identity linking and auto-provisioning by stable issuer/subject
  - Existing first-party access-token plus HttpOnly refresh-cookie session issuance for OAuth login
  - Google OAuth readiness state for downstream auth-shell wiring
affects: [auth-shell, readiness, oauth, identity, phase-05]

tech-stack:
  added: [Authlib>=1.7,<2]
  patterns:
    - Backend-owned OAuth authorization-code routes
    - Signed temporary OAuth state cookie
    - Provider identity persisted by issuer and subject
    - OAuth login completion reuses existing first-party session issuance

key-files:
  created:
    - backend/app/api/routes/auth_oauth.py
    - backend/app/identity/oauth_service.py
    - backend/app/identity/providers/__init__.py
    - backend/app/identity/providers/google.py
    - backend/tests/integration/auth/test_oauth_flows.py
    - backend/tests/integration/auth/test_google_oauth.py
    - backend/tests/smoke/test_oauth_google_flow.py
    - .planning/phases/05-gateway-administration-and-security-evidence/05-02-USER-SETUP.md
  modified:
    - backend/pyproject.toml
    - backend/app/api/routes/__init__.py
    - backend/app/main.py
    - backend/app/core/config.py
    - backend/app/core/provider_status.py
    - backend/app/schemas/health.py
    - backend/app/api/routes/health.py
    - backend/app/db/repositories/accounts.py

key-decisions:
  - "Authlib was added only after explicit human provenance approval."
  - "Google OAuth uses a backend-signed temporary state cookie instead of storing provider state in frontend code."
  - "OAuth login reuses the existing RS256 access-token and refresh-family session model rather than creating a second browser session type."
  - "Google identities are linked by issuer and subject; verified email is used only for safe linking/provisioning."

patterns-established:
  - "OAuth provider adapter: provider classes map external provider responses into stable issuer/subject/email identity objects."
  - "OAuth callback completion: service layer handles account linking/provisioning and session issuance inside one transaction."
  - "Readiness capability: `components.oauth_google` reports configured/unconfigured backend truth without exposing secrets."

requirements-completed: [IDEN-03, IDEN-06]

duration: 18 min
completed: 2026-06-15
---

# Phase 05 Plan 02: Google OAuth Backend Summary

**Backend-owned Google OAuth login with Authlib, signed state validation, stable provider identity persistence, and existing refresh-cookie session issuance**

## Performance

- **Duration:** 18 min
- **Started:** 2026-06-15T16:44:51Z
- **Completed:** 2026-06-15T17:02:37Z
- **Tasks:** 3 completed
- **Files modified:** 17

## Accomplishments

- Added the approved `Authlib>=1.7,<2` backend dependency after the required package-legitimacy checkpoint.
- Implemented `GET /api/auth/oauth/google/start` and `/callback` with backend-owned state validation, token exchange adapter, and safe error envelopes.
- Added `OAuthService` to link or provision verified Google identities and issue the same access token, refresh token family, refresh cookie, and CSRF cookie used by local login.
- Exposed `components.oauth_google` in readiness so Plan 05-09 can wire a truthful Google CTA without hardcoding frontend availability.

## Task Commits

Each task was committed atomically:

1. **Task 1: Verify Authlib provenance before any OAuth dependency change** - checkpoint approved by user (`approved authlib`), no code commit
2. **Task 2: Create Google OAuth contracts, config fields, and RED tests** - `c98180f` (test)
3. **Task 3: Implement backend-owned Google OAuth redirect and callback slice** - `3f06116` (feat)

**Plan metadata:** committed after this summary

## Files Created/Modified

- `backend/app/api/routes/auth_oauth.py` - Google OAuth start/callback route module with signed state cookie validation and safe redirects.
- `backend/app/identity/oauth_service.py` - OAuth login completion service that links/provisions identities and reuses first-party session issuance.
- `backend/app/identity/providers/google.py` - Google provider adapter backed by Authlib's async OAuth2 client.
- `backend/app/db/repositories/accounts.py` - Added identity lookup and OAuth user provisioning helpers.
- `backend/app/core/config.py` - Added Google OAuth client ID, secret, and redirect URI settings.
- `backend/app/core/provider_status.py`, `backend/app/schemas/health.py`, `backend/app/api/routes/health.py` - Added `oauth_google` readiness state.
- `backend/tests/integration/auth/test_oauth_flows.py` - Covers provider readiness, safe errors, state failure, and configured start redirect behavior.
- `backend/tests/integration/auth/test_google_oauth.py` - Covers verified provisioning, identity reuse, first-party cookies, and fail-closed missing/unverified email behavior.
- `backend/tests/smoke/test_oauth_google_flow.py` - Adds assembled-stack smoke coverage for the Google OAuth start route.
- `.planning/phases/05-gateway-administration-and-security-evidence/05-02-USER-SETUP.md` - Documents Google Cloud Console and environment setup still requiring human credentials.

## Decisions Made

- Authlib was accepted after explicit human approval and pinned as `Authlib>=1.7,<2`.
- Backend state validation uses a signed HttpOnly cookie scoped to `/api/auth/oauth/google`; access tokens are never placed in callback or frontend redirect URLs.
- OAuth-created accounts have no local password credential and receive the same standard user scopes as normal users.
- Existing local accounts can be linked only through verified matching email; conflicting provider identities fail closed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added account repository helpers for OAuth linking/provisioning**
- **Found during:** Task 3 (Implement backend-owned Google OAuth redirect and callback slice)
- **Issue:** The task file list omitted `backend/app/db/repositories/accounts.py`, but stable-subject lookup and passwordless standard-user provisioning were required for correct D-06/D-09 behavior.
- **Fix:** Added `get_user_bundle_by_identity` and `create_user_without_local_credentials` so OAuth completion can safely reuse the existing identity table and standard scope defaults.
- **Files modified:** `backend/app/db/repositories/accounts.py`
- **Verification:** `docker compose run --rm backend python -m pytest tests/integration/auth/test_oauth_flows.py tests/integration/auth/test_google_oauth.py tests/smoke/test_oauth_google_flow.py -q`
- **Committed in:** `3f06116`

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** The deviation was necessary to satisfy the planned security behavior without introducing a new table or alternate account model.

## Issues Encountered

- The backend Compose service copies source into the image rather than bind-mounting `backend/`, so the image had to be rebuilt before new tests and route code were visible. Rebuilds completed successfully.

## Authentication Gates

None.

## Known Stubs

None. Empty lists found in repository/test code are real relationship defaults or negative assertions, not UI-facing placeholders.

## Verification

- `python -m pip index versions authlib` - passed; latest listed version was `1.7.2`.
- `docker compose build backend` - passed after adding Authlib and after route implementation.
- `docker compose run --rm backend python -m pytest tests/integration/auth/test_oauth_flows.py tests/integration/auth/test_google_oauth.py tests/smoke/test_oauth_google_flow.py -q` - passed with `7 passed, 1 skipped`; smoke skip is expected unless `SIMPAGENT_RUN_SMOKE=true`.
- `docker compose run --rm backend python -m pytest tests/integration/test_health.py -q` - passed with `2 passed`.

## User Setup Required

External Google OAuth credentials require manual dashboard configuration. See `.planning/phases/05-gateway-administration-and-security-evidence/05-02-USER-SETUP.md` for:

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI`
- Google Cloud Console OAuth client callback configuration

## Next Phase Readiness

Backend Google OAuth is ready for Plan 05-09 auth-shell CTA/readiness wiring. GitHub OAuth, gateway hardening, admin evidence, and production-readiness remain in later Phase 05 plans.

## Self-Check: PASSED

- Summary file path is present in this close-out.
- Task commits exist: `c98180f`, `3f06116`.
- Key created files exist: `auth_oauth.py`, `oauth_service.py`, `google.py`, OAuth integration tests, smoke test, and user setup note.
- Plan-level verification passed.

---
*Phase: 05-gateway-administration-and-security-evidence*
*Completed: 2026-06-15*
