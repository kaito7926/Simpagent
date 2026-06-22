# Phase 05 Plan 03: User Setup Required

**Generated:** 2026-06-16
**Phase:** 05-gateway-administration-and-security-evidence
**Status:** Incomplete

Complete these items for real GitHub OAuth login to function. The backend flow, tests, readiness field, and secret-safe failure paths are implemented; these remaining steps require access to a GitHub account and deployment-specific callback URL.

## Environment Variables

| Status | Variable | Source | Add to |
|--------|----------|--------|--------|
| [ ] | `GITHUB_CLIENT_ID` | GitHub Developer Settings -> OAuth Apps -> Client ID | runtime environment / `.env` |
| [ ] | `GITHUB_CLIENT_SECRET` | GitHub Developer Settings -> OAuth Apps -> Client secrets | secret store / `.env` |
| [ ] | `GITHUB_REDIRECT_URI` | Authorized callback URL configured for the OAuth app | runtime environment / `.env` |

## Account Setup

- [ ] **Create or reuse a GitHub OAuth app**
  - URL: https://github.com/settings/developers
  - Skip if: A GitHub OAuth app already exists for this backend callback.

## Dashboard Configuration

- [ ] **Register the backend callback URI**
  - Location: GitHub Developer Settings -> OAuth Apps -> selected app -> Authorization callback URL
  - Set to: `http://localhost:8000/api/auth/oauth/github/callback` for local Kong access, or the deployed backend callback origin for production.
  - Notes: The backend requests `read:user user:email` and requires a verified primary email before linking or provisioning an account.

## Verification

After completing setup, verify with:

```bash
docker compose up --build
docker compose run --rm backend python -m pytest tests/integration/auth/test_github_oauth.py tests/integration/auth/test_oauth_account_linking.py -q
```

Expected results:
- `/ready` includes `components.oauth_github: "ready"` when all GitHub OAuth variables are present.
- `GET /api/auth/oauth/github/start` redirects to GitHub instead of returning `oauth_provider_unconfigured`.
- A successful callback creates the same HttpOnly refresh-cookie session used by local and Google login.

---

**Once all items complete:** Mark status as "Complete" at top of file.
