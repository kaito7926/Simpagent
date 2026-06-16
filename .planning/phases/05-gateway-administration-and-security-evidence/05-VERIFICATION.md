---
phase: 05-gateway-administration-and-security-evidence
verified: 2026-06-16T10:48:05Z
status: human_needed
score: 7/7 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run real Google and GitHub OAuth login in a browser with provider credentials configured."
    expected: "Each provider starts from the auth shell, returns through /api/auth/oauth/{provider}/callback, sets the same protected session model as local login, and lands in the authenticated workspace without token material in the URL or browser storage."
    why_human: "External provider redirects, browser SameSite behavior, and real provider dashboards cannot be fully verified by static code inspection."
  - test: "Trigger gateway-only 429 or oversized-body denials, then inspect the admin Gateway evidence page."
    expected: "The UI distinguishes Kong-backed gateway evidence from FastAPI security-event rows and shows only bounded redacted snippets."
    why_human: "The exact user-visible wording and workflow require a running stack plus visual review."
  - test: "Review the small-production and Cloudflare README guidance against the local stack."
    expected: "Documentation is Vietnamese, keeps local Compose as primary, marks Cloudflare optional, states trusted-proxy/source-IP assumptions, and avoids HA, distributed rate-limit, enterprise edge, or production-grade sandbox claims."
    why_human: "Documentation truthfulness and overclaiming require operator review."
  - test: "Run the assembled smoke suite with SIMPAGENT_RUN_SMOKE=true against the full Compose topology."
    expected: "Startup/readiness, local login, OAuth readiness/start, gateway routing, admin evidence, chat, Search, and Python smoke paths complete or degrade exactly as documented."
    why_human: "Smoke tests are intentionally gated and require a live full-stack topology plus optional external credentials."
---

# Phase 5: Gateway Administration and Security Evidence Verification Report

**Phase Goal:** Users can sign in with local credentials, Google, or GitHub, while operators and authorized administrators can run the assembled application through hardened ingress, redacted correlated evidence, and a small production deployment profile sized for about 100 users/month without weakening backend authority.
**Verified:** 2026-06-16T10:48:05Z
**Status:** human_needed
**Re-verification:** No - initial verification

## MVP User Flow Coverage

User-story source used for MVP framing: the repeated Phase 05 plan goal, "As a user, operator, or authorized administrator, I want to use OAuth sign-in, hardened ingress, and redacted admin evidence through one protected application, so that the prototype supports safe access and small-scale deployment without weakening backend authority."

Note: ROADMAP marks Phase 05 as `mvp`, but the ROADMAP goal itself is not in strict "As a..., I want..., so that..." form. The plan artifacts do contain a valid user-story-formatted Phase Goal, so this report uses that for user-flow coverage while still verifying all ROADMAP success criteria as the binding contract.

| Step | Expected | Evidence | Status |
| --- | --- | --- | --- |
| Auth shell provider choice | User sees truthful Google/GitHub CTAs above local credentials when backend readiness reports providers configured. | `frontend/lib/readiness.ts` maps `oauth_google`/`oauth_github`; `AuthCard.tsx` renders provider states; frontend test passed for configured/mixed/disabled states. | VERIFIED |
| OAuth start | Browser navigates to backend-owned OAuth start routes and does not store tokens in browser storage. | `frontend/lib/auth-session.ts` maps providers to `/api/auth/oauth/{provider}/start`; tests trap `localStorage`/`sessionStorage`; Kong routes `/api/auth/oauth`. | VERIFIED |
| Provider callback session | OAuth callback issues first-party access token plus HttpOnly refresh/CSRF cookies through the existing session model. | `backend/app/api/routes/auth_oauth.py` callback uses `OAuthService.complete_login`; `oauth_service.py` calls `issue_access_token`, `create_family`, and `create_token`; OAuth integration tests passed in Compose. | VERIFIED |
| Hardened ingress | Client traffic enters through approved DB-less Kong routes with strict CORS, request-size, rate-limit, and correlation behavior. | `kong/kong.yml` has `/api/auth/oauth`, strict CORS including `PATCH`, `request-size-limiting`, `rate-limiting`, and `correlation-id`; post-review regression tests passed. | VERIFIED |
| Admin evidence | Scoped admins can open real admin surfaces; ordinary and under-scoped users get explicit denial states. | `ChatSidebar.tsx` lists six admin surfaces; `ChatWorkspace.tsx` fetches backend pages; `admin.py` exposes protected routes; frontend/admin and backend/admin tests passed. | VERIFIED |
| Operator profile | Operator has env-only small-production and optional Cloudflare guidance without hardcoded production secrets. | `.env.example`, `compose.yaml`, and Vietnamese `README.md` include public origins, trusted proxies, OAuth variables, backup/restore/rollback, smoke matrix, and explicit 100 users/month limits. | VERIFIED |
| Outcome | Prototype supports safe access and small-scale deployment without weakening backend authority. | Backend remains authoritative for OAuth/session/admin checks; Kong is coarse ingress; Compose no longer mounts Docker socket; redaction is backend-owned. | VERIFIED, pending human UAT |

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Users can authenticate with Google or GitHub through OAuth2/OIDC-safe redirect flows, provider secrets remain environment-only, and OAuth sessions land in the same short-lived JWT plus protected refresh-token model as local login. | VERIFIED | `auth_oauth.py` defines Google/GitHub start/callback routes under `/api/auth/oauth`; state cookies use explicit `SameSite=lax`; provider config lives in `Settings`; `OAuthService` reuses `issue_access_token` and refresh-family creation. Compose OAuth/auth tests passed (`33 passed`). |
| 2 | OAuth account linking and provisioning prevent takeover by failing closed on missing, unverified, or conflicting provider email identity and preserving local-account semantics. | VERIFIED | `OAuthService.complete_login` rejects missing subject/issuer/email verification, resolves by stored provider subject first, and checks conflicting identities before linking/provisioning. Account-linking tests passed in Compose. |
| 3 | Client traffic reaches only approved app/health/API routes through DB-less Kong with strict CORS, request-size controls, validated correlation IDs, and tighter useful rate limits on auth/tool endpoints. | VERIFIED | `kong/kong.yml` is DB-less and route-specific; CORS includes `PATCH`; rate-limit/request-size/correlation plugins are declared. `backend/app/main.py` validates correlation IDs and trusted proxies. Regression subset passed (`28 passed, 4 skipped`). |
| 4 | FastAPI remains authoritative for complete token, account, role, scope, ownership, and tool-policy decisions even when Kong is coarse, and no database, worker control plane, or Kong Admin API is publicly exposed. | VERIFIED | Admin read/write checks are enforced in `AdminEvidenceService`; JWT profile tests verify backend authority; Compose public-port tests passed; no `/var/run/docker.sock` mount remains in `compose.yaml`. |
| 5 | Requests, provider calls, tool calls, denials, replay, rate limits, sandbox violations, and admin actions produce correlated structured evidence with recursive secret and sensitive-content redaction; gateway-only rate-limit evidence is represented through Kong-backed evidence rather than fabricated admin rows. | VERIFIED | `identity/redaction.py` provides recursive sanitizer; `AdminEvidenceService` sanitizes security/tool rows; `GatewayEvidenceService` derives gateway evidence from Kong-backed sources; redaction and admin-evidence tests passed. |
| 6 | Properly scoped administrators can page through bounded users, audits, security events, tool executions, failed logins, rate-limit evidence, aggregate metrics, and orchestration controls, while ordinary and under-scoped users are denied. | VERIFIED | `admin.py` exposes users/security/tool/gateway/metrics/orchestration routes; `frontend/lib/admin-api.ts` uses `authorizedJson`; `ChatWorkspace.tsx` renders six surfaces and explicit forbidden states. Frontend tests passed (`19 passed`). |
| 7 | Operator can follow a documented small-production profile for about 100 users/month, including Cloudflare-to-Kong routing, trusted-proxy assumptions, secure cookies/origins, migrations, backup/restore, smoke checks, and explicit limits without overclaiming. | VERIFIED | `.env.example` and `compose.yaml` expose env-only profile keys; README is Vietnamese and documents local primary path, optional Cloudflare path, backup/restore/rollback, smoke commands, and prototype limitations. Profile/provisioning regression tests passed. |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `backend/app/api/routes/auth_oauth.py` | Google/GitHub OAuth start/callback routes with state and safe redirects | VERIFIED | Router prefix `/api/auth/oauth`; Google/GitHub start/callback routes present; `OAUTH_STATE_SAMESITE = "lax"`; registered in `main.py`. |
| `backend/app/identity/oauth_service.py` | Stable-subject OAuth completion and first-party session issuance | VERIFIED | Uses issuer/subject lookup, verified email checks, local account linking guardrails, `issue_access_token`, refresh family, and refresh token creation. |
| `backend/app/identity/providers/google.py` and `github.py` | Provider adapters mapping external identity to stable subject and verified email | VERIFIED | Both expose issuer/subject/email verification handling; GitHub requires verified primary email. |
| `kong/kong.yml` | Hardened DB-less gateway routes/plugins | VERIFIED | `/api/auth/oauth` route, strict CORS, request-size, rate-limit, and correlation-id plugins present. |
| `backend/app/main.py` and `backend/app/core/config.py` | CORS, trusted proxy, public-origin, and correlation enforcement hooks | VERIFIED | FastAPI CORS includes `PATCH`; correlation ID validation and trusted-proxy-only forwarded IP handling are implemented; production validation rejects missing public origins/trusted proxies. |
| `backend/app/identity/redaction.py` and `backend/app/services/gateway_evidence.py` | Recursive redaction and Kong-backed gateway evidence contracts | VERIFIED | Service layer sanitizes before schema serialization; gateway evidence is read-only and config-backed. |
| `backend/app/api/routes/admin.py` and `backend/app/services/admin_evidence.py` | Admin route exposure and RBAC/scope enforcement | VERIFIED | Users, security events, tool executions, gateway evidence, metrics, and orchestration routes delegate to `AdminEvidenceService`; read/write scopes enforced. |
| `frontend/lib/auth-session.ts`, `frontend/lib/readiness.ts`, `AuthCard.tsx`, `AccountAccessShell.tsx` | Readiness-driven OAuth CTAs and backend-owned start navigation | VERIFIED | Provider state helpers and `beginOAuth` route mapping present; frontend tests verify no browser token storage. |
| `frontend/lib/admin-api.ts`, `ChatSidebar.tsx`, `ChatWorkspace.tsx`, admin components | Real shared-shell admin evidence surfaces | VERIFIED | All six admin destinations, bounded tables, sanitized drawers, and explicit state panels are wired to backend APIs. |
| `.env.example`, `compose.yaml`, `README.md` | Small-production profile and Vietnamese operator runbook | VERIFIED | Env-only OAuth/public-origin/trusted-proxy/secret-file settings; optional Cloudflare documentation; no Docker socket mount. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| Frontend auth shell | Backend OAuth routes | `beginOAuth()` navigates to `/api/auth/oauth/google/start` or `/api/auth/oauth/github/start` | WIRED | Frontend tests assert route mapping and no storage writes; Kong routes the same prefix. |
| OAuth routes | OAuth service/session issuance | `OAuthService.complete_login()` from callback handlers | WIRED | Callback handlers call service and redirect without placing tokens in URL. |
| OAuth service | Account repository | issuer/subject lookup and verified-email linking/provisioning | WIRED | Repository has `get_user_bundle_by_identity_subject`, identity creation, and passwordless user creation. |
| Readiness | Auth shell | `oauth_google` / `oauth_github` components | WIRED | Backend health schema exposes both components; frontend readiness maps them to CTA states. |
| Kong | FastAPI | approved `/api/*`, `/health`, `/ready`, `/api/auth/oauth` routes plus correlation header | WIRED | Static grep and regression tests confirm route/plugin shape. |
| Admin API | Admin service | route handlers delegate to `AdminEvidenceService` | WIRED | Gateway evidence, metrics, orchestration, users, events, and tool executions go through backend service gates. |
| Admin frontend | Admin API | `authorizedJson` wrappers | WIRED | `frontend/lib/admin-api.ts` wraps all `/api/admin/*` calls; frontend tests assert endpoints and methods. |
| Redaction | Evidence serialization | sanitizer called before schemas/drawers | WIRED | `AdminEvidenceService` and `GatewayEvidenceService` call sanitizer/summarizer; drawer renders snippets only. |
| Production docs | Compose/env profile | README references actual `compose.yaml` and env keys | WIRED | Profile tests validate `.env.example`, Compose profile, and provisioning behavior. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `AuthCard.tsx` / `AccountAccessShell.tsx` | OAuth provider states | Backend `/ready` `components.oauth_google` / `oauth_github` through `frontend/lib/readiness.ts` | Yes, readiness is derived from backend config status | FLOWING |
| `auth_oauth.py` | OAuth identity and session outcome | Provider adapter token/userinfo exchange to `OAuthService.complete_login` | Yes, integration tests mock valid/invalid provider identities and verify DB/session effects | FLOWING |
| `ChatWorkspace.tsx` admin pages | Metrics/users/security/tool/gateway/orchestration pages | `frontend/lib/admin-api.ts` authorized calls to `/api/admin/*` | Yes, backend routes return repository/service data and frontend tests render it | FLOWING |
| `AdminEvidenceService` | Security/tool/gateway evidence | Admin repository plus `GatewayEvidenceService.from_kong_config` | Yes, tests verify DB-backed evidence and separate Kong-backed gateway evidence | FLOWING |
| `GatewayEvidenceService` | Gateway evidence records | Parsed Kong config and fallback config evidence | Yes, config-backed records are generated without fabricated DB rows | FLOWING |
| `README.md` / `.env.example` / `compose.yaml` | Production profile settings | Environment variables and Compose profile | Yes, tests assert required keys/profile wiring and no Docker socket | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Frontend OAuth/admin/chat workspace wiring | `npm --prefix frontend test -- tests/account-access-oauth.test.tsx tests/admin-evidence.test.tsx tests/chat-workspace.test.ts` | 19 passed | PASS |
| Frontend type safety | `npm --prefix frontend run typecheck` | passed | PASS |
| Backend OAuth/admin/redaction integration | `docker compose run --rm backend python -m pytest tests/integration/auth/test_oauth_flows.py tests/integration/auth/test_google_oauth.py tests/integration/auth/test_github_oauth.py tests/integration/auth/test_oauth_account_linking.py tests/integration/admin/test_admin_evidence.py tests/integration/admin/test_admin_write.py tests/security/test_secret_leakage.py -q` | 33 passed | PASS |
| Post-review gateway/sandbox/profile regression subset | `docker compose run --rm backend python -m pytest tests/unit/test_oauth_state_cookie.py tests/integration/gateway/test_cors.py ... -q` | 28 passed, 4 skipped due backend-container static Kong context/smoke gate | PASS |
| Compose config validity | `docker compose config -q` | passed | PASS |
| Schema drift | `node .codex/gsd-core/bin/gsd-tools.cjs query verify.schema-drift 05` | `drift_detected: false` | PASS |
| Host-side backend pytest attempt | `py -3.13 -m pytest ... -q` from `backend/` | failed resolving Compose-only hostname `postgres-test`; rerun inside Compose passed | INFO |

### Probe Execution

No `scripts/**/probe-*.sh` files or phase-declared probe scripts were found for Phase 05.

| Probe | Command | Result | Status |
| --- | --- | --- | --- |
| None | N/A | No probes declared or discovered | SKIPPED |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| AUTHZ-02 | 05-04, 05-07 | Admin APIs require Admin role and `admin:read`/`admin:write`. | SATISFIED | `AdminEvidenceService._require_admin_scope`; admin write/read tests passed. |
| IDEN-03 | 05-02, 05-03 | External OAuth authorization-code flows with CSRF state. | SATISFIED | Google/GitHub start/callback routes; state cookie tests and integration tests passed. |
| IDEN-06 | 05-02, 05-09 | Google sign-in when configured; disabled/unconfigured state preserves local login. | SATISFIED | Backend `oauth_google` readiness and frontend CTA state tests passed. |
| IDEN-07 | 05-03, 05-09 | GitHub sign-in when configured; disabled/unconfigured state preserves local login. | SATISFIED | Backend `oauth_github` readiness and frontend CTA state tests passed. |
| IDEN-08 | 05-03 | OAuth linking/provisioning fails closed for unsafe provider identity. | SATISFIED | Account-linking integration tests passed in Compose. |
| GATE-01 | 05-05 | Kong DB-less approved routes. | SATISFIED | `kong/kong.yml` route/plugin shape; compose config valid. |
| GATE-02 | 05-05 | Strict configured CORS without wildcard credentialed origin. | SATISFIED | Kong/FastAPI CORS include explicit origins/methods/headers; CORS regression passed. |
| GATE-03 | 05-05, 05-08 | Tighter auth/tool rate limits with useful 429 metadata. | SATISFIED | Kong route-specific rate-limiting declarations; tests and README smoke matrix. |
| GATE-04 | 05-05 | Request-size limits and validated correlation ID. | SATISFIED | Kong `request-size-limiting`; FastAPI correlation validation; regression passed. |
| GATE-05 | 05-05 | FastAPI remains authoritative despite coarse gateway screening. | SATISFIED | JWT profile tests passed; admin/service policies remain backend-side. |
| GATE-06 | 05-05 | No public DB, worker control plane, or Kong Admin API exposure. | SATISFIED | Compose public-port/proxy tests passed; no Docker socket mount. |
| GATE-07 | 05-08 | Optional Cloudflare-to-Kong path and trusted proxy assumptions documented. | SATISFIED | Vietnamese README and `.env.example` include Cloudflare/trusted proxy path. |
| GATE-08 | 05-08 | Cloudflare Tunnel/DNS/TLS/WAF/Turnstile/Bot Fight limits documented. | SATISFIED | README documents optional edge and limitations without overclaiming. |
| OBS-01 | 05-05 | Correlation IDs propagated through gateway/FastAPI/evidence. | SATISFIED | Kong correlation plugin and FastAPI correlation middleware; tests passed. |
| OBS-02 | 05-06 | Structured logs/evidence recursively redact secrets. | SATISFIED | `sanitize_admin_evidence`; logging/secret leakage tests passed. |
| OBS-03 | 05-06, 05-07 | Typed redacted evidence for denials/rate limits/admin actions. | SATISFIED | Admin evidence/gateway evidence service and route exposure verified. |
| OBS-04 | 05-06 | Tool execution evidence stays correlated and bounded. | SATISFIED | Admin service maps tool rows with sanitized summaries/snippets; unit tests passed. |
| OBS-05 | 05-04, 05-06, 05-07 | Authorized admin can list evidence and rate-limit evidence. | SATISFIED | All six admin surfaces wired; admin backend/frontend tests passed. |
| OBS-06 | 05-04, 05-07 | Ordinary/under-scoped users denied from admin evidence. | SATISFIED | Backend denial checks and explicit frontend forbidden state tests passed. |
| OBS-07 | 05-04 | Admin metrics expose bounded aggregate counts only. | SATISFIED | Metrics schemas/service and frontend cards use aggregate fields; tests passed. |
| PRODREADY-01 | 05-08 | Env-only small production profile without hardcoded secrets. | SATISFIED | `.env.example`, Compose profile, secret-file wiring; provisioning tests passed. |
| PRODREADY-02 | 05-05, 05-08 | Production cookies/CORS/proxy/public URLs documented and enforced. | SATISFIED | Config validation and profile tests passed. |
| PRODREADY-03 | 05-08 | Migration/bootstrap/backup/restore/rollback guidance documented and testable. | SATISFIED | README runbook and bootstrap CLI provisioning test. |
| PRODREADY-04 | 05-08 | Startup/readiness/smoke/ops checks cover local/OAuth/gateway/admin/chat/Search/Python. | SATISFIED, human UAT pending | Smoke tests and commands exist; many are gated by `SIMPAGENT_RUN_SMOKE=true`, requiring live-stack UAT. |
| PRODREADY-05 | 05-08 | Documentation states realistic prototype limits and avoids unsupported production claims. | SATISFIED, human review pending | README states 100 users/month, single-node/local rate limit, no HA/distributed rate limiting/enterprise protection/production-grade sandbox. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| Phase 05 modified files | N/A | `TBD`, `FIXME`, `XXX` | None | No blocker debt markers found in Phase 05 implementation files. |
| Frontend form components | Various | `placeholder=` | Info | Normal input hints, not disconnected implementation stubs. |
| `backend/app/services/chat_turns.py` | 38 | `DIRECT_CHAT_PLACEHOLDER` | Info | Pre-existing `/api/conversations/{id}/turns` direct-chat branch, not the normal `/api/conversations` chat route used by the current app shell. Normal chat remains wired through `backend/app/api/routes/chat.py`, `ChatCoordinator`, and `OpenAIChatAdapter`. |

### Human Verification Required

### 1. Real OAuth Provider Login

**Test:** Configure real Google and GitHub OAuth credentials, start the stack, click each provider CTA in the auth shell, and complete provider login.
**Expected:** Each provider returns to `/api/auth/oauth/{provider}/callback`, creates/reuses the correct account, sets the same protected refresh-cookie session as local login, and lands in the authenticated workspace.
**Why human:** Real provider dashboards, browser cookie behavior, and external redirects cannot be fully validated by static inspection.

### 2. Gateway Evidence UX

**Test:** Trigger Kong-only 429 and oversized-body denials, then inspect the Admin -> Gateway evidence page and drawer.
**Expected:** Gateway denials are represented as Kong/config-backed evidence, not fabricated FastAPI security-event rows; drawer snippets remain bounded and redacted.
**Why human:** Requires a running gateway path and review of user-visible wording.

### 3. Small-Production Documentation Review

**Test:** Read the Vietnamese README small-production and Cloudflare sections against `.env.example` and `compose.yaml`.
**Expected:** Local Compose is primary, Cloudflare is optional, trusted proxy/source-IP assumptions are explicit, and limitations avoid HA/distributed-rate-limit/enterprise/prod-sandbox claims.
**Why human:** Operator documentation truthfulness and overclaiming are judgment-based.

### 4. Full Assembled Smoke

**Test:** Run the smoke suite with `SIMPAGENT_RUN_SMOKE=true` against the full local Compose topology and configured optional providers where available.
**Expected:** Startup/readiness, local login, OAuth readiness/start, gateway routing, admin evidence, chat, Search, and Python paths pass or degrade exactly as documented.
**Why human:** The smoke harness is intentionally gated and may need live credentials and local stack supervision.

### Gaps Summary

No automated blocker gaps were found. All seven ROADMAP success criteria are verified by live code, wiring, and targeted tests. The phase cannot be marked `passed` because Phase 05 validation explicitly includes human-only OAuth/browser, gateway-evidence UX, documentation, and full smoke checks.

---

_Verified: 2026-06-16T10:48:05Z_
_Verifier: the agent (gsd-verifier)_
