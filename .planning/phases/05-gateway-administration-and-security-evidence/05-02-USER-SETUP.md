# Phase 05 Plan 02: User Setup Required

**Generated:** 2026-06-15
**Phase:** 05-gateway-administration-and-security-evidence
**Plan:** 05-02
**Status:** Incomplete

Complete these items for real Google OAuth login to function. The backend routes, session issuance, and tests are automated; the remaining work requires access to Google Cloud Console and real OAuth credentials.

## Environment Variables

| Status | Variable | Source | Add to |
|--------|----------|--------|--------|
| [ ] | `GOOGLE_CLIENT_ID` | Google Cloud Console -> APIs & Services -> Credentials -> OAuth client ID | Local shell or Compose environment |
| [ ] | `GOOGLE_CLIENT_SECRET` | Google Cloud Console -> APIs & Services -> Credentials -> OAuth client secret | Local shell or Compose secret/environment |
| [ ] | `GOOGLE_REDIRECT_URI` | Authorized redirect URI configured for the OAuth client | Local shell or Compose environment |

## Dashboard Configuration

- [ ] **Create or update the Google OAuth client**
  - Location: Google Cloud Console -> APIs & Services -> Credentials
  - Application type: Web application
  - Authorized redirect URI for local backend: `http://localhost:8000/api/auth/oauth/google/callback`
  - If running through Kong locally, also add: `http://localhost:8000/api/auth/oauth/google/callback`
  - For any deployed domain, add the exact HTTPS backend callback URL used by the deployment.

## Verification

After completing setup, the backend should expose Google OAuth as ready through `/ready`, and `GET /api/auth/oauth/google/start` should redirect to Google instead of returning `oauth_provider_unconfigured`.

Expected results:
- `/ready` includes `components.oauth_google: "ready"`.
- Google start route redirects to `accounts.google.com`.
- Callback lands in the existing SimpAgent refresh-cookie session model.

---

**Once all items complete:** Mark status as "Complete" at top of file.
