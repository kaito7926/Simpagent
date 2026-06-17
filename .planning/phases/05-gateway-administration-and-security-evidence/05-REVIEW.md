---
phase: 05-gateway-administration-and-security-evidence
reviewed: 2026-06-16T10:28:54Z
depth: standard
files_reviewed: 57
files_reviewed_list:
  - .env.example
  - README.md
  - backend/app/api/routes/__init__.py
  - backend/app/api/routes/admin.py
  - backend/app/api/routes/auth_oauth.py
  - backend/app/api/routes/health.py
  - backend/app/core/config.py
  - backend/app/core/provider_status.py
  - backend/app/db/repositories/accounts.py
  - backend/app/db/repositories/admin.py
  - backend/app/identity/oauth_service.py
  - backend/app/identity/providers/__init__.py
  - backend/app/identity/providers/github.py
  - backend/app/identity/providers/google.py
  - backend/app/identity/redaction.py
  - backend/app/main.py
  - backend/app/schemas/admin.py
  - backend/app/schemas/health.py
  - backend/app/security/access_tokens.py
  - backend/app/services/admin_evidence.py
  - backend/app/services/gateway_evidence.py
  - backend/pyproject.toml
  - backend/tests/integration/admin/test_admin_evidence.py
  - backend/tests/integration/admin/test_admin_write.py
  - backend/tests/integration/auth/test_github_oauth.py
  - backend/tests/integration/auth/test_google_oauth.py
  - backend/tests/integration/auth/test_oauth_account_linking.py
  - backend/tests/integration/auth/test_oauth_flows.py
  - backend/tests/integration/cli/test_provisioning.py
  - backend/tests/integration/gateway/test_cors.py
  - backend/tests/integration/gateway/test_production_profile.py
  - backend/tests/integration/gateway/test_rate_limits.py
  - backend/tests/integration/gateway/test_request_size_and_correlation.py
  - backend/tests/security/test_jwt_profile.py
  - backend/tests/security/test_secret_leakage.py
  - backend/tests/smoke/_helpers.py
  - backend/tests/smoke/test_admin_flow.py
  - backend/tests/smoke/test_oauth_github_flow.py
  - backend/tests/smoke/test_oauth_google_flow.py
  - backend/tests/smoke/test_topology.py
  - backend/tests/unit/test_admin_evidence_service.py
  - backend/tests/unit/test_logging.py
  - compose.yaml
  - frontend/components/account-access/AccountAccessShell.tsx
  - frontend/components/account-access/AuthCard.tsx
  - frontend/components/admin/EvidenceDetailDrawer.tsx
  - frontend/components/admin/EvidenceTable.tsx
  - frontend/components/admin/StatePanel.tsx
  - frontend/components/chat/ChatSidebar.tsx
  - frontend/components/chat/ChatWorkspace.tsx
  - frontend/components/settings/SettingsPage.tsx
  - frontend/lib/admin-api.ts
  - frontend/lib/auth-session.ts
  - frontend/lib/readiness.ts
  - frontend/tests/account-access-oauth.test.tsx
  - frontend/tests/admin-evidence.test.tsx
  - kong/kong.yml
findings:
  critical: 4
  warning: 2
  info: 0
  total: 6
status: issues_found
---

# Phase 05: Code Review Report

**Reviewed:** 2026-06-16T10:28:54Z
**Depth:** standard
**Files Reviewed:** 57
**Status:** issues_found

## Summary

Reviewed the listed backend, frontend, Compose, Kong, and test files for correctness, authorization regressions, secret leakage, and security boundary failures. The public OAuth and admin-write paths have blocking integration defects, and the sandbox Compose topology violates the project's isolation boundary by mounting the host Docker socket.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: Kong Does Not Route OAuth URLs Used By The Frontend

**File:** `kong/kong.yml:43`
**Issue:** The backend OAuth router is mounted at `/api/auth/oauth` and the frontend starts OAuth at `/api/auth/oauth/{provider}/start`, but Kong's OAuth route only matches `/api/oauth`. Requests to `/api/auth/oauth/google/start` and `/api/auth/oauth/github/start` through the public gateway fall through to the frontend route instead of FastAPI, so OAuth login is broken in the required Docker/Kong topology.
**Fix:**
```yaml
      - name: backend-oauth
        paths:
          - /api/auth/oauth
        strip_path: false
```

### CR-02: OAuth State Cookie Uses SameSite Strict And Fails Real Provider Callbacks

**File:** `backend/app/api/routes/auth_oauth.py:50`
**Issue:** `_issue_state_cookie` reuses `settings.cookie_samesite`, which is `strict` in the checked-in Compose and default settings. A Google/GitHub callback is a cross-site top-level navigation from the provider back to `/api/auth/oauth/{provider}/callback`, so Strict cookies are not sent and `_validate_state_cookie` rejects otherwise valid logins. The current tests use one HTTP client for start and callback, so they do not simulate browser SameSite behavior.
**Fix:**
```python
response.set_cookie(
    key=OAUTH_STATE_COOKIE_NAMES[provider],
    value=f"{state}.{_state_signature(state, settings)}",
    max_age=OAUTH_STATE_MAX_AGE_SECONDS,
    path=f"/api/auth/oauth/{provider}",
    secure=settings.cookie_secure,
    httponly=True,
    samesite="lax",
)
```
Use the same explicit `samesite="lax"` when deleting the state cookie.

### CR-03: Browser Admin Writes Are Blocked By CORS

**File:** `backend/app/main.py:89`, `kong/kong.yml:90`
**Issue:** Admin mutations are exposed as `PATCH` in FastAPI and the frontend calls them with `PATCH`, but both FastAPI CORS and Kong CORS only allow `GET`, `POST`, `DELETE`, and `OPTIONS`. In any cross-origin deployment path, browser preflight for user access and orchestration writes fails before authorization reaches FastAPI.
**Fix:**
```python
allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"]
```
```yaml
      methods:
        - GET
        - POST
        - PATCH
        - DELETE
        - OPTIONS
```

### CR-04: Sandbox Service Mounts The Host Docker Socket

**File:** `compose.yaml:309`
**Issue:** The sandbox container bind-mounts `/var/run/docker.sock`, giving that service control over the host Docker daemon. This collapses the intended user-code isolation boundary and directly violates the project security constraint that the sandbox must not use privileged host execution paths or Docker socket access.
**Fix:** Remove the socket mount and move execution to an isolated worker boundary that does not grant daemon control to the request-facing sandbox service, for example a locked-down worker API with no host mounts and strict CPU, memory, process, filesystem, and network limits.

## Warnings

### WR-01: Development Python Capability Secret Is Hardcoded In Runtime Paths

**File:** `backend/app/core/config.py:371`, `compose.yaml:125`, `compose.yaml:307`
**Issue:** The Python capability secret falls back to the literal value `sandbox-dev-secret`, and Compose passes the same literal into backend and sandbox services. Even though production requires a configured secret, the local security prototype ships with forgeable capability material by default.
**Fix:** Generate the development capability secret through `init-dev-secrets` like the JWT and HMAC keys, pass it via `SIMPAGENT_PYTHON_CAPABILITY_SECRET_FILE`, and remove the literal fallback from `Settings.python_capability_secret_value`.

### WR-02: Gateway/OAuth Tests Miss The Broken Browser And Public Gateway Cases

**File:** `backend/tests/integration/gateway/test_cors.py:32`, `backend/tests/integration/auth/test_google_oauth.py:49`, `backend/tests/integration/auth/test_github_oauth.py:49`
**Issue:** The CORS config test asserts only `GET`, `POST`, `DELETE`, and `OPTIONS`, so it locks in the missing `PATCH` bug. The OAuth integration tests complete start and callback with a single HTTP client and do not simulate the provider-to-callback SameSite transition or assert that Kong routes `/api/auth/oauth/*` to FastAPI. These gaps allowed CR-01 through CR-03.
**Fix:** Add `PATCH` to the expected CORS methods and add gateway/static tests that assert `/api/auth/oauth` appears in `kong/kong.yml`. For OAuth callbacks, add a browser-behavior test that starts OAuth, drops Strict cookies for the cross-site callback simulation, and verifies a Lax state cookie is required.

---

_Reviewed: 2026-06-16T10:28:54Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
