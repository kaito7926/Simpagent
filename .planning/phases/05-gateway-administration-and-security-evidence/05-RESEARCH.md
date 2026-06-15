# Phase 5: Final Product Hardening, OAuth, Gateway, Administration, and Security Evidence - Research

**Researched:** 2026-06-15
**Domain:** OAuth identity, Kong hardening, admin evidence redaction, and small-production profile
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Google and GitHub OAuth are in Phase 5 scope, not deferred. Phase 5 now includes `IDEN-03`, `IDEN-06`, `IDEN-07`, and `IDEN-08`.
- **D-02:** Small production-readiness for about 100 users/month is in Phase 5 scope, not deferred. Phase 5 now includes `PRODREADY-01` through `PRODREADY-05`.
- **D-03:** Phase 5 remains a maintainable prototype target. The product must not claim high availability, distributed rate limiting, enterprise edge protection, or production-grade sandbox guarantees.

### OAuth Login
- **D-04:** Google and GitHub login use OAuth2/OIDC-safe redirect flows with CSRF state protection and provider secrets stored only in environment configuration.
- **D-05:** OAuth sessions land in the same short-lived access JWT plus protected HttpOnly refresh-token session model as local email/password login.
- **D-06:** OAuth provider identity is stored by `(provider, provider_subject)` so future logins do not depend on mutable provider email values.
- **D-07:** Existing local accounts are auto-linked only when the provider returns a verified email that matches the normalized local account email.
- **D-08:** Missing, unverified, or conflicting provider email identity fails closed. Do not link or provision in ambiguous cases.
- **D-09:** First-time OAuth login with a verified new email auto-provisions a standard `user` account with the same standard scopes as local registration.
- **D-10:** Google/GitHub provider buttons appear only when the corresponding backend provider is configured; missing config hides or disables that provider without breaking local login.

### Gateway Evidence
- **D-11:** Kong enforces gateway behavior, while FastAPI stores redacted correlated evidence.
- **D-12:** DB-less Kong remains the ingress control point for strict CORS, request-size limits, validated or propagated correlation IDs, route exposure, and useful route-specific rate limits.
- **D-13:** FastAPI evidence covers requests that reach the backend: auth failures, admin denials, refresh replay, tool decisions, provider calls, sandbox violations, admin actions, and correlation IDs.
- **D-14:** Gateway-only `429` or request-size denials that never reach FastAPI are represented through Kong configuration and verification/test evidence, not fabricated admin database rows.

### Admin Evidence Surfaces
- **D-15:** Phase 5 wires all six admin surfaces as real product surfaces: metrics, users, security events, tool executions, gateway evidence, and orchestration.
- **D-16:** Properly scoped admins can page through bounded evidence; ordinary users and under-scoped admins are denied with recorded redacted evidence.
- **D-17:** User mutation and orchestration writes remain gated by `admin:write`; read-only evidence is gated by `admin:read`.

### Redaction Detail Policy
- **D-18:** Admin tables show summaries only.
- **D-19:** Evidence detail drawers may show short expandable sanitized snippets after recursive redaction.
- **D-20:** Forbidden in admin evidence: raw prompts, full request bodies, provider payload dumps, bearer tokens, cookies, passwords, API keys, raw Google grounding JSON/HTML, full sandbox output, container IDs, host paths, and unredacted secret-bearing identifiers.
- **D-21:** Tests must include canary-secret and redaction assertions for snippets, not only table summaries.

### Cloudflare and Small Production Profile
- **D-22:** Cloudflare is an optional documented edge path; the local app remains primary and must still run through `docker compose up --build`.
- **D-23:** Implement the trusted proxy/origin configuration hooks needed by app and Kong.
- **D-24:** Document Cloudflare Tunnel, WAF, Turnstile integration points, Bot Fight Mode, TLS, source-IP trust, and Free-plan limitations without requiring Cloudflare for local demo.
- **D-25:** Production-readiness includes environment hardening, secure cookies/origins, OAuth redirect URL guidance, migrations, admin bootstrap, backup/restore, smoke checks, and explicit limits for about 100 users/month.

### the agent's Discretion
- Choose the exact OAuth callback route names, service/module names, database model split, and provider adapter boundaries, as long as the locked security and account-linking behavior holds.
- Choose the exact standard OAuth-created user scope set by reusing the existing standard local user scope defaults.
- Choose the exact gateway evidence UI copy for Kong-only events, as long as it does not imply FastAPI stored rows for requests it never received.
- Choose the exact snippet length limits, metadata allowlist, and drawer layout, as long as recursive redaction and canary-secret tests cover them.
- Choose the exact smoke-test packaging for the 100 users/month profile, as long as local credentials, Google login, GitHub login, gateway routing, admin evidence, chat, Search, and Python paths are covered.

### Deferred Ideas (OUT OF SCOPE)
None — user explicitly promoted OAuth and small production-readiness into Phase 5 scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

Requirement descriptions below are copied from `.planning/REQUIREMENTS.md` verbatim. [VERIFIED: REQUIREMENTS.md]

| ID | Description | Research Support |
|----|-------------|------------------|
| AUTHZ-02 | Admin APIs require the Admin role and the corresponding `admin:read` or `admin:write` scope. | Existing admin policy/service pattern already enforces role plus scope and records denials; Phase 5 should extend, not replace, that path. [VERIFIED: backend/app/authorization/policy.py][VERIFIED: backend/app/services/admin_evidence.py] |
| IDEN-03 | User can authenticate through real external OAuth2/OIDC providers using authorization-code redirect flows with CSRF state protection and provider-specific configuration. | Use backend-owned OAuth start/callback endpoints with Authlib’s documented redirect and token-exchange flow plus environment-only provider config. [CITED: https://docs.authlib.org/en/v1.6.2/client/starlette.html][VERIFIED: backend/app/core/config.py] |
| IDEN-06 | User can sign in with Google when `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and the configured redirect URI are present, while missing configuration hides or disables the provider without breaking local login. | Add Google OAuth settings/readiness flags; frontend already supports conditional shell rendering and should gate buttons from backend capability state. [VERIFIED: frontend/components/account-access/AccountAccessShell.tsx][VERIFIED: backend/app/core/config.py] |
| IDEN-07 | User can sign in with GitHub when `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, and the configured redirect URI are present, while missing configuration hides or disables the provider without breaking local login. | Same provider-capability pattern as Google; GitHub email retrieval requires `user:email` handling and fail-closed email verification logic. [CITED: https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps][CITED: https://docs.github.com/en/rest/users/emails?apiVersion=2022-11-28] |
| IDEN-08 | OAuth provisioning and account linking fail closed for missing, unverified, or conflicting email identity and never allow a provider login to take over an existing local account without an explicit safe match. | Store identity by provider subject, not email; link only verified email matches; existing identity table already supports unique `(issuer, subject)`. [CITED: https://developers.google.com/identity/openid-connect/openid-connect][VERIFIED: backend/app/models/account.py] |
| GATE-01 | Kong OSS runs in DB-less mode with declarative services and routes for approved `/api/*`, `/health`, and readiness traffic. | Keep DB-less Kong and harden the existing declarative file rather than switching control planes. [CITED: https://developer.konghq.com/gateway/db-less-mode/][VERIFIED: kong/kong.yml] |
| GATE-02 | Kong applies strict configured CORS origins, methods, and headers without using a wildcard credentialed origin. | Move from current broad global CORS to route-specific strict CORS aligned to frontend origin(s). [CITED: https://developer.konghq.com/plugins/cors/][VERIFIED: kong/kong.yml] |
| GATE-03 | Kong applies stricter limits to login, registration, and tool routes than to ordinary chat routes and returns useful `429` metadata. | Use Kong rate-limiting plugin per route with `policy=local` for single-node prototype. [CITED: https://developer.konghq.com/plugins/rate-limiting/][VERIFIED: compose.yaml] |
| GATE-04 | Kong applies request-size limits and propagates or creates a validated correlation ID. | Add request-size-limiting and correlation-id plugins at Kong; backend already emits/propagates `X-Correlation-Id`. [CITED: https://developer.konghq.com/plugins/request-size-limiting/][CITED: https://developer.konghq.com/plugins/correlation-id/][VERIFIED: backend/app/main.py] |
| GATE-05 | Kong may reject coarse invalid JWT traffic early, but FastAPI independently remains authoritative for complete token, account, role, scope, ownership, and tool-policy validation. | Keep Kong JWT validation coarse only; backend `resolve_principal` must remain authoritative. [CITED: https://developer.konghq.com/plugins/jwt/][VERIFIED: backend/app/authorization/principal.py] |
| GATE-06 | Kong Admin API, PostgreSQL, search worker, and sandbox control plane are not exposed as public application ports. | Public Compose ports already expose Kong proxy and Grafana only; Phase 5 must not add public control-plane ports. [VERIFIED: compose.yaml] |
| GATE-07 | Documentation defines the optional request path `Client -> Cloudflare -> Kong -> FastAPI -> PostgreSQL/LLM/Tools` and trusted proxy assumptions. | Document optional Cloudflare edge path and the trusted-header boundary explicitly. [CITED: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/][CITED: https://developers.cloudflare.com/support/troubleshooting/restoring-visitor-ips/restoring-original-visitor-ips/] |
| GATE-08 | Cloudflare documentation covers Tunnel, DNS, TLS, Free-plan WAF guidance, Turnstile integration points, Bot Fight Mode, limitations, and source-IP trust. | Treat Cloudflare as optional edge hardening only; keep local Compose as the primary path. [CITED: https://developers.cloudflare.com/waf/][CITED: https://developers.cloudflare.com/turnstile/][CITED: https://developers.cloudflare.com/bots/get-started/bot-fight-mode/] |
| OBS-01 | Every request receives a validated correlation ID propagated through Kong, FastAPI, provider calls, tool calls, audit records, and the response. | Backend already issues/echoes correlation IDs; Kong should validate/generate before FastAPI receives the request. [VERIFIED: backend/app/main.py][VERIFIED: backend/tests/smoke/test_logging_flow.py] |
| OBS-02 | Application logs are structured JSON with allowlisted fields and recursive redaction of credentials, tokens, cookies, API keys, secrets, and sensitive raw content. | Extend existing JSON logging/redaction rules into admin evidence serialization, not just logs. [VERIFIED: backend/app/core/logging.py][VERIFIED: backend/tests/unit/test_logging.py] |
| OBS-03 | Auth failures, forbidden access, refresh replay, rate-limit events, tool decisions, sandbox violations, and admin actions create typed redacted evidence. | Existing security-event sink covers admin denials and refresh replay; Phase 5 must add gateway representations and redacted snippets. [VERIFIED: backend/app/db/repositories/sessions.py][VERIFIED: backend/app/services/admin_evidence.py] |
| OBS-04 | Tool execution records contain actor, conversation, tool, safe input/output summaries, status, duration, and correlation ID. | Existing tool execution schema already matches most required fields. [VERIFIED: backend/app/models/domain.py][VERIFIED: backend/app/schemas/admin.py] |
| OBS-05 | Properly authorized admin can list users and paginated recent audit logs, security events, tool executions, failed logins, and available rate-limit evidence. | Backend has users/security-events/tool-executions/metrics/orchestration endpoints; frontend still needs real data wiring for all surfaces. [VERIFIED: backend/app/api/routes/admin.py][VERIFIED: frontend/components/chat/ChatWorkspace.tsx] |
| OBS-06 | Ordinary users and under-scoped admins cannot access administrative evidence endpoints. | Existing denial tests and policy path should be preserved and expanded to new gateway evidence endpoints. [VERIFIED: backend/tests/integration/admin/test_admin_evidence.py][VERIFIED: backend/app/authorization/policy.py] |
| OBS-07 | Admin metrics expose bounded aggregate operational/security counts without leaking user content or credentials. | Existing metrics endpoint is already bounded and aggregate-only. [VERIFIED: backend/app/services/admin_evidence.py][VERIFIED: backend/app/schemas/admin.py] |
| PRODREADY-01 | Operator can configure a small production deployment profile for about 100 users/month through environment variables without hardcoded origins, cookie settings, OAuth secrets, JWT keys, database credentials, or provider credentials. | Add OAuth env vars and production origin/proxy settings to the existing strict settings model. [VERIFIED: backend/app/core/config.py][VERIFIED: compose.yaml] |
| PRODREADY-02 | Production-mode cookies, CORS, trusted proxy handling, HTTPS assumptions, and frontend/backend public URLs are documented and enforced consistently for the selected deployment profile. | Current settings already enforce secure cookies in production; Phase 5 must add public URL/trusted-proxy/OAuth redirect alignment. [VERIFIED: backend/app/core/config.py][CITED: https://developers.cloudflare.com/support/troubleshooting/restoring-visitor-ips/restoring-original-visitor-ips/] |
| PRODREADY-03 | Database migrations, seed/admin bootstrap, backup, restore, and rollback guidance are documented and testable against the Compose-based deployment target. | Compose already has migrate/init-dev-secrets/seed-demo jobs; Phase 5 should add production bootstrap and operational playbook around them. [VERIFIED: compose.yaml] |
| PRODREADY-04 | Startup, readiness, smoke-test, and basic operational checks cover local credentials, Google login, GitHub login, gateway routing, admin evidence, chat, Search, and Python paths. | Existing smoke harness covers local login/admin/search/logging/python; add OAuth and gateway-hardening smoke coverage rather than inventing a second harness. [VERIFIED: backend/tests/smoke/test_admin_flow.py][VERIFIED: backend/tests/smoke/test_logging_flow.py] |
| PRODREADY-05 | Documentation states realistic capacity, reliability, security, rate-limit, observability, and external-provider limitations for a 100 users/month prototype and does not claim high availability or enterprise production guarantees. | Keep single-node DB-less Kong, optional Cloudflare, and prototype-grade sandbox language explicit. [VERIFIED: 05-CONTEXT.md][VERIFIED: AGENTS.md] |
</phase_requirements>

## Project Constraints (from AGENTS.md)

- Use Next.js, TypeScript, Tailwind CSS, Markdown rendering, and code-block rendering on the frontend. [VERIFIED: AGENTS.md]
- Use FastAPI, Python 3.11+, Pydantic, SQLAlchemy or SQLModel, PostgreSQL, and Alembic on the backend. [VERIFIED: AGENTS.md]
- Keep Google ADK and Gemini 2 for Google Search; Phase 5 must not weaken or replace that boundary. [VERIFIED: AGENTS.md]
- Preserve local email/password login while keeping identity code replaceable by a standards-based OAuth2/OIDC provider. [VERIFIED: AGENTS.md]
- RBAC, scopes, ownership, and tool permissions must fail closed and must keep negative-test coverage. [VERIFIED: AGENTS.md]
- User Python must continue to execute only in the isolated Docker worker, not in backend or host processes. [VERIFIED: AGENTS.md]
- `docker compose up --build` remains the required local startup command. [VERIFIED: AGENTS.md]
- Kong OSS should remain DB-less unless a database becomes demonstrably necessary. [VERIFIED: AGENTS.md]
- User-facing project documentation must remain in Vietnamese. [VERIFIED: AGENTS.md]
- Tokens, passwords, API keys, and secrets must never be logged or sent to tools or model context. [VERIFIED: AGENTS.md]
- Prefer a demonstrable, maintainable prototype over production-scale completeness. [VERIFIED: AGENTS.md]

## Summary

Phase 5 should be planned as an extension of the existing backend-owned security model, not as a front-end-led social-login add-on. The codebase already has the right seams: a provider-shaped identity contract, a normalized user/account repository, a unique `(issuer, subject)` identity table, RS256 access JWT issuance/validation, refresh-token family rotation, admin authorization gates, structured JSON logging, and persisted security/tool evidence. [VERIFIED: backend/app/identity/contracts.py][VERIFIED: backend/app/models/account.py][VERIFIED: backend/app/security/access_tokens.py][VERIFIED: backend/app/services/sessions.py][VERIFIED: backend/app/services/admin_evidence.py][VERIFIED: backend/app/core/logging.py]

The biggest planning insight is that most Phase 5 work is integration hardening, not greenfield invention. OAuth should terminate on backend start/callback routes, then immediately reuse the same local session issuance path and current-user model already used by password login. Kong should remain DB-less and become a coarse ingress policy layer for route exposure, strict CORS, correlation IDs, request-size limits, and per-route rate limits, while FastAPI stays authoritative for token semantics, account state, role/scope checks, ownership, and tool policy. [VERIFIED: backend/app/api/routes/auth.py][VERIFIED: backend/app/services/authentication.py][CITED: https://developer.konghq.com/gateway/db-less-mode/][CITED: https://developer.konghq.com/plugins/jwt/]

The highest-risk planning areas are account-linking safety, trusted-proxy handling, and evidence redaction boundaries. Google explicitly says not to use email as a unique identifier and to use `sub` instead; GitHub email retrieval is scope- and visibility-dependent; Cloudflare source-IP restoration is only trustworthy when Kong/app trust Cloudflare as a proxy; and the current admin schemas still expose raw metadata dicts, so Phase 5 must add recursive redaction before evidence leaves the backend. [CITED: https://developers.google.com/identity/openid-connect/openid-connect][CITED: https://docs.github.com/en/rest/users/emails?apiVersion=2022-11-28][CITED: https://developers.cloudflare.com/support/troubleshooting/restoring-visitor-ips/restoring-original-visitor-ips/][VERIFIED: backend/app/schemas/admin.py]

**Primary recommendation:** Implement Phase 5 around one backend-owned identity/session pipeline, one DB-less Kong policy file, and one redaction layer that sanitizes evidence before admin schemas serialize it. [VERIFIED: backend/app/api/routes/auth.py][VERIFIED: kong/kong.yml][VERIFIED: backend/app/core/logging.py]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Google/GitHub OAuth redirect start and callback handling | API / Backend | Browser / Client | Provider secrets, state/nonce validation, token exchange, and account linking must stay server-side. [CITED: https://docs.authlib.org/en/v1.6.2/client/starlette.html][VERIFIED: 05-CONTEXT.md] |
| Session issuance, refresh rotation, logout, and stale-token invalidation | API / Backend | Database / Storage | Existing access-token and refresh-family logic already lives in FastAPI plus PostgreSQL-backed session state. [VERIFIED: backend/app/services/authentication.py][VERIFIED: backend/app/services/sessions.py] |
| Provider availability UI and OAuth button rendering | Browser / Client | API / Backend | The frontend should reflect backend capability/config state, but the backend remains the source of truth for availability. [VERIFIED: frontend/components/account-access/AccountAccessShell.tsx][VERIFIED: backend/app/core/config.py] |
| CORS, request-size limits, route exposure, gateway JWT screening, rate limiting, and correlation header policy | Frontend Server (Gateway / ingress layer) | API / Backend | Kong should enforce coarse ingress rules before FastAPI, while the backend still validates semantics and authorization. [VERIFIED: kong/kong.yml][CITED: https://developer.konghq.com/plugins/cors/][CITED: https://developer.konghq.com/plugins/rate-limiting/] |
| Correlated security/tool/admin evidence persistence | API / Backend | Database / Storage | FastAPI already records security events and tool execution state; Phase 5 should extend this evidence model. [VERIFIED: backend/app/db/repositories/sessions.py][VERIFIED: backend/app/models/domain.py] |
| Evidence redaction and snippet shaping | API / Backend | Browser / Client | Redaction must happen before data reaches admin response schemas; the UI must only render already-sanitized payloads. [VERIFIED: backend/app/core/logging.py][VERIFIED: backend/app/schemas/admin.py] |
| Admin evidence pages, drawers, and orchestration controls | Browser / Client | API / Backend | Backend provides bounded pages and policy enforcement; frontend wires real pages into the existing shell. [VERIFIED: backend/app/api/routes/admin.py][VERIFIED: frontend/components/chat/ChatWorkspace.tsx] |
| Trusted proxy/IP restoration and optional Cloudflare edge documentation | Frontend Server (Gateway / ingress layer) | API / Backend | Kong/app must trust upstream headers correctly, and documentation must describe the edge path without making it mandatory. [CITED: https://developers.cloudflare.com/support/troubleshooting/restoring-visitor-ips/restoring-original-visitor-ips/][VERIFIED: 05-CONTEXT.md] |
| Backup/restore and production bootstrap guidance | Database / Storage | API / Backend | This is primarily an operational data responsibility with backend migration/bootstrap hooks. [VERIFIED: compose.yaml] |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `Authlib` [WARNING: flagged as suspicious — verify before using.] | `1.7.2` (PyPI page shows release date 2026-05-06). [CITED: https://pypi.org/project/Authlib/][VERIFIED: package-legitimacy check] | Backend OAuth/OIDC client for Google and GitHub redirect flows. [CITED: https://docs.authlib.org/en/v1.6.2/client/starlette.html] | Its Starlette client documents `authorize_redirect` and `authorize_access_token`, which maps cleanly onto the existing FastAPI routing model. [CITED: https://docs.authlib.org/en/v1.6.2/client/starlette.html] |
| `PyJWT[crypto]` | Existing repo range `>=2.13,<3`. [VERIFIED: backend/pyproject.toml] | Continue issuing first-party RS256 access JWTs after both local and OAuth login. [VERIFIED: backend/app/security/access_tokens.py] | Reuse the current token contract instead of introducing a second browser token system. [VERIFIED: backend/app/api/routes/auth.py][VERIFIED: backend/app/security/access_tokens.py] |
| Kong Gateway OSS | Current repo pin `3.9.1`. [VERIFIED: compose.yaml] | DB-less ingress hardening for CORS, rate limiting, correlation IDs, request-size control, and coarse JWT screening. [VERIFIED: kong/kong.yml] | The project already depends on Kong DB-less mode and the phase requirements map directly to built-in plugins. [VERIFIED: AGENTS.md][CITED: https://developer.konghq.com/gateway/db-less-mode/] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Built-in Kong `cors` plugin | Bundled with the repo’s Kong deployment. [VERIFIED: kong/kong.yml] | Exact origin/method/header policy for browser traffic. [CITED: https://developer.konghq.com/plugins/cors/] | Use on auth/chat/admin routes that are browser reachable. [CITED: https://developer.konghq.com/plugins/cors/] |
| Built-in Kong `correlation-id` plugin | Bundled with the repo’s Kong deployment. [VERIFIED: compose.yaml] | Generate or propagate a stable request reference into upstream requests and optionally back to clients. [CITED: https://developer.konghq.com/plugins/correlation-id/] | Use on all public routes so Kong and FastAPI share one correlation reference. [CITED: https://developer.konghq.com/plugins/correlation-id/][VERIFIED: backend/app/main.py] |
| Built-in Kong `rate-limiting` plugin | Bundled with the repo’s Kong deployment. [VERIFIED: compose.yaml] | Per-route `429` controls with client-visible limit/reset metadata. [CITED: https://developer.konghq.com/plugins/rate-limiting/] | Use stricter limits on login, registration, refresh, and tool routes than on ordinary chat reads/writes. [CITED: https://developer.konghq.com/plugins/rate-limiting/][VERIFIED: 05-CONTEXT.md] |
| Built-in Kong `request-size-limiting` plugin | Bundled with the repo’s Kong deployment. [VERIFIED: compose.yaml] | Block oversized request bodies before they hit FastAPI. [CITED: https://developer.konghq.com/plugins/request-size-limiting/] | Use on auth/chat/tool/admin write routes where large bodies are not expected. [CITED: https://developer.konghq.com/plugins/request-size-limiting/] |
| Built-in Kong `jwt` plugin | Bundled with the repo’s Kong deployment. [VERIFIED: compose.yaml] | Coarse RS256 screening at ingress. [CITED: https://developer.konghq.com/plugins/jwt/] | Use only as a front-door filter; keep full claim/account validation in FastAPI. [CITED: https://developer.konghq.com/plugins/jwt/][VERIFIED: backend/app/authorization/principal.py] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `Authlib` [WARNING: flagged as suspicious — verify before using.] | Provider-specific HTTPX code using raw OAuth/OIDC endpoints. [ASSUMED] | Raw HTTPX avoids a new dependency but forces custom state, nonce, discovery, callback, and token parsing code that this phase should not hand-roll. [CITED: https://docs.authlib.org/en/v1.6.2/client/starlette.html] |
| Kong `rate-limiting` with `policy=local` | Kong `rate-limiting` with Redis-backed policy. [CITED: https://developer.konghq.com/plugins/rate-limiting/] | Redis improves multi-node accuracy, but this phase is explicitly single-node prototype scope and should avoid a new operational dependency. [VERIFIED: 05-CONTEXT.md][CITED: https://developer.konghq.com/plugins/rate-limiting/] |
| Backend-owned OAuth callback routes | Next.js route handlers acting as OAuth middle tier. [ASSUMED] | A Next.js middle tier would duplicate secret handling and session issuance responsibilities already owned by FastAPI. [VERIFIED: backend/app/api/routes/auth.py][VERIFIED: backend/app/services/authentication.py] |

**Installation:**
```bash
python -m pip install "Authlib>=1.7,<2"
```

**Version verification:**
```bash
python -m pip index versions authlib
```
Verified in this session: `authlib (1.7.2)` was listed as latest by `pip index versions authlib`, and the PyPI project page shows release date `2026-05-06`. [CITED: https://pypi.org/project/Authlib/]

## Package Legitimacy Audit

> Required because this phase likely adds a backend OAuth client dependency.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `authlib` | PyPI [CITED: https://pypi.org/project/Authlib/] | 40 days old on 2026-06-15. [CITED: https://pypi.org/project/Authlib/] | Unknown in seam output. [VERIFIED: package-legitimacy check] | `github.com/authlib/authlib`. [VERIFIED: package-legitimacy check] | `SUS`. [VERIFIED: package-legitimacy check] | Flagged — planner must add `checkpoint:human-verify` before install. [VERIFIED: package-legitimacy check] |

**Packages removed due to [SLOP] verdict:** none. [VERIFIED: package-legitimacy check]
**Packages flagged as suspicious [SUS]:** `authlib` — planner must insert a human verification checkpoint before install. [VERIFIED: package-legitimacy check]

## Architecture Patterns

### System Architecture Diagram

```text
Optional edge path
Client
  -> Cloudflare (optional: Tunnel/WAF/Turnstile/Bot Fight Mode) [docs-only path]
  -> Kong OSS (DB-less)
       - strict route exposure
       - exact CORS
       - correlation-id policy
       - request-size limits
       - route-specific rate limits
       - coarse JWT screening
       -> FastAPI
            -> local login OR OAuth provider adapter (Google / GitHub)
                 -> provider authorization redirect + callback exchange
                 -> identity linking/provisioning by (issuer, subject)
                 -> issue RS256 access JWT + refresh-token family
                 -> set HttpOnly refresh cookie + CSRF cookie
            -> chat/search/python/admin APIs
                 -> security events + tool executions + admin metrics/evidence
                 -> PostgreSQL
       <- X-Correlation-Id + API responses

Kong-only denials (429 / oversized body / blocked route)
  -> represented by Kong config + verification evidence in admin UI
  -> not inserted as fabricated FastAPI database rows
```

This ownership split matches the current codebase and the locked Phase 5 decisions. [VERIFIED: backend/app/api/routes/auth.py][VERIFIED: backend/app/services/admin_evidence.py][VERIFIED: kong/kong.yml][VERIFIED: 05-CONTEXT.md]

### Recommended Project Structure
```text
backend/
├── app/
│   ├── api/routes/
│   │   ├── auth.py                  # existing local auth routes kept
│   │   └── auth_oauth.py            # Google/GitHub start + callback routes
│   ├── identity/
│   │   ├── providers/
│   │   │   ├── google.py            # provider-specific token/userinfo mapping
│   │   │   └── github.py            # provider-specific token/userinfo/email mapping
│   │   ├── oauth_service.py         # shared link/provision/fail-closed logic
│   │   └── redaction.py             # recursive admin evidence sanitization
│   ├── db/repositories/
│   │   └── accounts.py              # extend identity lookups by issuer/subject/email
│   └── services/
│       └── admin_evidence.py        # consume sanitized evidence views
├── tests/
│   ├── integration/auth/            # OAuth start/callback/linking tests
│   ├── integration/admin/           # gateway evidence paging + redaction tests
│   └── smoke/                       # full-stack login/gateway/admin flow tests
frontend/
├── components/account-access/       # provider buttons + capability-aware auth shell
├── components/admin/                # real overview/users/events/tools/gateway pages
└── lib/admin-api.ts                 # paged admin data wrappers
kong/
└── kong.yml                         # declarative routes + plugins as source of truth
```

### Pattern 1: Backend-Owned OAuth Start/Callback
**What:** Keep OAuth start and callback endpoints in FastAPI, then feed the verified provider identity into the existing token/session issuance path. [VERIFIED: backend/app/api/routes/auth.py][VERIFIED: backend/app/services/authentication.py]
**When to use:** Always for Google/GitHub login in this phase, because provider secrets and token exchange must stay off the browser. [VERIFIED: 05-CONTEXT.md][CITED: https://docs.authlib.org/en/v1.6.2/client/starlette.html]
**Example:**
```python
# Source: https://docs.authlib.org/en/v1.6.2/client/starlette.html
from authlib.integrations.starlette_client import OAuth

async def oauth_start(request):
    client = oauth.create_client("google")
    redirect_uri = request.url_for("oauth_callback")
    return await client.authorize_redirect(request, redirect_uri)

async def oauth_callback(request):
    client = oauth.create_client("google")
    token = await client.authorize_access_token(request)
    userinfo = token.get("userinfo")
```

### Pattern 2: Persist Provider Identity by Stable Subject, Not Email
**What:** Use provider subject (`sub` for Google, provider user id/subject equivalent for GitHub) as the durable identity key, with email treated as mutable linking data. [CITED: https://developers.google.com/identity/openid-connect/openid-connect][VERIFIED: backend/app/models/account.py]
**When to use:** On every OAuth callback before deciding whether to link to an existing local user or provision a new one. [VERIFIED: 05-CONTEXT.md]
**Example:**
```python
# Source: https://developers.google.com/identity/openid-connect/openid-connect
provider_subject = userinfo["sub"]
email = userinfo.get("email")
email_verified = bool(userinfo.get("email_verified"))

if not email or not email_verified:
    raise OAuthLinkDenied("missing_or_unverified_email")

# Persist (issuer, subject) and use normalized email only for safe linking.
```

### Pattern 3: Redact Before Admin Schema Serialization
**What:** Apply recursive redaction and snippet shaping in backend services/repositories before populating `SecurityEventItem.metadata` or drawer detail payloads. [VERIFIED: backend/app/core/logging.py][VERIFIED: backend/app/schemas/admin.py]
**When to use:** For every admin evidence response, not just logs. [VERIFIED: 05-CONTEXT.md]
**Example:**
```python
# Source pattern: backend/app/core/logging.py
SAFE_EVENT = {
    "event_type": event.event_type,
    "severity": event.severity,
    "correlation_id": event.correlation_id,
    "snippet": sanitize_log_value(event.event_metadata),
}
```

### Anti-Patterns to Avoid
- **Frontend-managed OAuth token exchange:** This duplicates secret handling and undermines the existing backend-owned session model. [VERIFIED: backend/app/api/routes/auth.py]
- **Linking by provider email alone:** Google explicitly warns that email is not a stable unique identifier. [CITED: https://developers.google.com/identity/openid-connect/openid-connect]
- **Treating Kong JWT validation as application authorization:** Kong only screens signatures and limited claims; backend still owns account/role/scope/ownership checks. [CITED: https://developer.konghq.com/plugins/jwt/][VERIFIED: backend/app/authorization/principal.py]
- **Rendering raw evidence metadata in admin drawers:** Current schema shape would leak too much without an explicit sanitization layer. [VERIFIED: backend/app/schemas/admin.py][VERIFIED: backend/app/core/logging.py]
- **Routes that rely only on `hosts` for browser CORS preflight:** Kong docs note that browser preflight handling is more reliable with path/method-based routes. [CITED: https://developer.konghq.com/plugins/cors/]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OAuth redirect/state/token exchange | Custom Google/GitHub auth-code client with manual state/nonce plumbing | `Authlib` Starlette client. [CITED: https://docs.authlib.org/en/v1.6.2/client/starlette.html] | The library already documents the exact redirect and callback flow this stack needs. [CITED: https://docs.authlib.org/en/v1.6.2/client/starlette.html] |
| Gateway correlation headers | Ad-hoc random header injection in multiple services | Kong `correlation-id` plugin plus existing FastAPI middleware. [CITED: https://developer.konghq.com/plugins/correlation-id/][VERIFIED: backend/app/main.py] | One ingress-owned correlation policy prevents split IDs and mismatched evidence. [VERIFIED: backend/tests/smoke/test_logging_flow.py] |
| Route throttling | Custom per-endpoint throttling middleware in FastAPI | Kong `rate-limiting` plugin. [CITED: https://developer.konghq.com/plugins/rate-limiting/] | Gateway throttling protects upstream resources earlier and emits standard limit metadata. [CITED: https://developer.konghq.com/plugins/rate-limiting/] |
| Oversized-body rejection | Manual request-size checks sprinkled across route handlers | Kong `request-size-limiting` plugin. [CITED: https://developer.konghq.com/plugins/request-size-limiting/] | Requests that should never hit the app are cheaper and clearer to block at ingress. [CITED: https://developer.konghq.com/plugins/request-size-limiting/] |
| Recursive secret redaction | One-off string replacements in each admin endpoint | Shared backend sanitizer/redaction service extending current logging sanitizer. [VERIFIED: backend/app/core/logging.py] | Evidence redaction must be consistent across logs, DB-backed events, and admin responses. [VERIFIED: 05-CONTEXT.md] |
| Trusted client-IP restoration | Blindly trusting `X-Forwarded-For` from any source | Explicit trusted-proxy config using Cloudflare/Kong headers only from trusted upstreams. [CITED: https://developers.cloudflare.com/support/troubleshooting/restoring-visitor-ips/restoring-original-visitor-ips/] | Untrusted forwarded headers become an authorization and audit-corruption vector. [CITED: https://developers.cloudflare.com/support/troubleshooting/restoring-visitor-ips/restoring-original-visitor-ips/] |

**Key insight:** Phase 5 is mostly about wiring existing, standardized security primitives together so they share one authority boundary; hand-rolled replacements would multiply failure modes exactly where this phase is most sensitive. [VERIFIED: backend/app/api/routes/auth.py][VERIFIED: backend/app/authorization/principal.py][VERIFIED: kong/kong.yml]

## Common Pitfalls

### Pitfall 1: Linking OAuth Accounts by Email Instead of Stable Provider Subject
**What goes wrong:** A provider email change or non-unique email causes account confusion or takeover risk. [CITED: https://developers.google.com/identity/openid-connect/openid-connect]
**Why it happens:** Email is convenient and already normalized in the local-account model. [VERIFIED: backend/app/db/repositories/accounts.py]
**How to avoid:** Persist `(issuer, subject)` as the durable identity key and use verified normalized email only as a safe-link signal. [VERIFIED: backend/app/models/account.py][VERIFIED: 05-CONTEXT.md]
**Warning signs:** OAuth code paths that search only by email, or migrations that add provider email fields without issuer/subject lookup indexes. [VERIFIED: backend/app/models/account.py]

### Pitfall 2: Trusting Kong to Replace Backend Authorization
**What goes wrong:** Requests with valid signatures but stale account state, missing scopes, or wrong ownership slip past edge checks. [CITED: https://developer.konghq.com/plugins/jwt/]
**Why it happens:** Kong can reject bad JWTs early, so it is tempting to move app auth there. [CITED: https://developer.konghq.com/plugins/jwt/]
**How to avoid:** Keep Kong as coarse screening only; continue using `resolve_principal` and service-level scope checks in FastAPI. [VERIFIED: backend/app/authorization/principal.py][VERIFIED: backend/app/services/admin_evidence.py]
**Warning signs:** Plans that remove backend role/scope validation after adding the JWT plugin. [VERIFIED: backend/app/authorization/policy.py]

### Pitfall 3: Spoofed Client IP Through Untrusted Proxy Headers
**What goes wrong:** Rate limiting, audit logs, or admin evidence attribute actions to attacker-supplied IP values. [CITED: https://developers.cloudflare.com/support/troubleshooting/restoring-visitor-ips/restoring-original-visitor-ips/]
**Why it happens:** `X-Forwarded-For` and similar headers look authoritative unless trusted proxies are configured carefully. [CITED: https://developers.cloudflare.com/support/troubleshooting/restoring-visitor-ips/restoring-original-visitor-ips/]
**How to avoid:** Accept forwarded client-IP headers only from trusted upstreams such as Cloudflare/Kong and document the trust chain explicitly. [CITED: https://developers.cloudflare.com/support/troubleshooting/restoring-visitor-ips/restoring-original-visitor-ips/]
**Warning signs:** Security events or gateway evidence storing client IP without recording which hop was trusted. [ASSUMED]

### Pitfall 4: Logging or Returning Raw Evidence Metadata
**What goes wrong:** Secrets, raw provider payloads, raw prompts, or sandbox internals appear in admin APIs or logs. [VERIFIED: 05-CONTEXT.md]
**Why it happens:** The current admin schema still accepts arbitrary metadata dicts for security events. [VERIFIED: backend/app/schemas/admin.py]
**How to avoid:** Add a shared allowlist/redaction layer before DB serialization and before admin response serialization. [VERIFIED: backend/app/core/logging.py][VERIFIED: backend/app/services/admin_evidence.py]
**Warning signs:** Admin endpoints returning nested metadata unchanged, or tests that only check summaries and not drawer snippets. [VERIFIED: backend/tests/integration/admin/test_admin_evidence.py][VERIFIED: 05-CONTEXT.md]

### Pitfall 5: Pretending Kong-Only Denials Were Stored by FastAPI
**What goes wrong:** Admin evidence becomes misleading because requests rejected at ingress are shown as if the app recorded them. [VERIFIED: 05-CONTEXT.md]
**Why it happens:** It is tempting to normalize all evidence into one table even when the backend never saw the request. [VERIFIED: 05-CONTEXT.md]
**How to avoid:** Represent gateway-only denials through Kong config, logs, and verification evidence; reserve DB rows for backend-seen requests. [VERIFIED: 05-CONTEXT.md][CITED: https://developer.konghq.com/gateway/db-less-mode/]
**Warning signs:** Planner tasks that propose inserting fake `security_events` rows for `429` responses emitted entirely by Kong. [VERIFIED: backend/app/models/evidence.py]

### Pitfall 6: Host-Only Kong Routes Breaking Browser Preflight
**What goes wrong:** Legitimate browser OPTIONS requests fail before the intended route/plugin chain runs. [CITED: https://developer.konghq.com/plugins/cors/]
**Why it happens:** Browser preflight cannot send arbitrary `Host` behavior the same way app code can. [CITED: https://developer.konghq.com/plugins/cors/]
**How to avoid:** Keep path-based route matching for browser-facing endpoints and test preflight explicitly. [CITED: https://developer.konghq.com/plugins/cors/][VERIFIED: kong/kong.yml]
**Warning signs:** CORS bugs that affect only OPTIONS requests or only browser traffic behind Kong. [CITED: https://developer.konghq.com/plugins/cors/]

## Code Examples

Verified patterns from official sources:

### OAuth Redirect + Callback
```python
# Source: https://docs.authlib.org/en/v1.6.2/client/starlette.html
async def google_start(request):
    client = oauth.create_client("google")
    return await client.authorize_redirect(request, request.url_for("google_callback"))

async def google_callback(request):
    client = oauth.create_client("google")
    token = await client.authorize_access_token(request)
    userinfo = token.get("userinfo")
```

### Google Identity Keying
```python
# Source: https://developers.google.com/identity/openid-connect/openid-connect
subject = userinfo["sub"]            # durable identity key
email = userinfo.get("email")        # mutable contact data
verified = userinfo.get("email_verified")
```

### Kong DB-less as Declarative Source of Truth
```yaml
# Source: https://developer.konghq.com/gateway/db-less-mode/
_format_version: "3.0"
services:
  - name: backend
    url: http://backend:8000
# Edit the declarative file, then reload the whole config; do not CRUD entities live.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Local-password-only auth with an OIDC-ready boundary | Real external OAuth/OIDC providers terminating into the same first-party session model. [VERIFIED: backend/app/api/routes/auth.py][VERIFIED: 05-CONTEXT.md] | Phase 5 scope promotion on 2026-06-15. [VERIFIED: 05-CONTEXT.md] | Planner must treat OAuth as identity extension work, not as a replacement auth stack. [VERIFIED: 05-CONTEXT.md] |
| Imperative gateway admin changes | Declarative DB-less Kong config plus whole-config reloads. [CITED: https://developer.konghq.com/gateway/db-less-mode/] | Current Kong DB-less guidance. [CITED: https://developer.konghq.com/gateway/db-less-mode/] | Kong hardening tasks belong in `kong/kong.yml`, not in ad-hoc admin mutations. [VERIFIED: kong/kong.yml] |
| Free-form logs plus scattered redaction | Structured JSON logging with centralized recursive sanitization. [VERIFIED: backend/app/core/logging.py] | Already shipped before Phase 5. [VERIFIED: backend/app/core/logging.py] | Phase 5 should extend the same sanitizer into admin evidence serialization. [VERIFIED: backend/tests/unit/test_logging.py][VERIFIED: backend/app/schemas/admin.py] |

**Deprecated/outdated:**
- Using provider email as the durable OAuth identity key is outdated and directly contradicted by Google’s OIDC documentation. [CITED: https://developers.google.com/identity/openid-connect/openid-connect]
- Using `decK sync` as the DB-less configuration mechanism is outdated for this phase; Kong’s DB-less page says `decK` requires a database and cannot be used in DB-less mode. [CITED: https://developer.konghq.com/gateway/db-less-mode/]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Kong gateway evidence can be presented cleanly in admin UI using config/log/test evidence without introducing a new backend persistence table. [ASSUMED] | Architecture Patterns / Common Pitfalls | Planner may under-scope backend work if the desired UX later requires persisted gateway snapshots. |
| A2 | A backend-only OAuth callback design is preferable to a Next.js callback handler for this codebase. [ASSUMED] | Architecture Patterns / Alternatives Considered | Planner could miss a frontend routing requirement if a different deployment topology is later chosen. |
| A3 | Recording trusted-hop provenance alongside restored client IP will be sufficient for gateway/admin evidence needs. [ASSUMED] | Common Pitfalls | Evidence schema may need more fields if operators require richer proxy-chain inspection. |

## Open Questions (RESOLVED)

1. **Should Phase 5 pin `Authlib 1.7.x` immediately or gate it behind a human package review?**
   - Resolution: Gate it behind a human package review, then pin `Authlib>=1.7,<2` only after that checkpoint passes. This aligns with the Phase 5 package legitimacy audit, keeps Authlib as the approved default implementation path, and satisfies the package-legitimacy rule without hand-rolling OAuth. [VERIFIED: package-legitimacy check][CITED: https://docs.authlib.org/en/v1.6.2/client/starlette.html]

2. **Does the team want to keep the repo’s current `kong:3.9.1` pin for Phase 5, or spend scope upgrading to a newer 3.9 patch/LTS line first?**
   - Resolution: Keep the existing `kong:3.9.1` pin for Phase 5 and plan hardening work against the current repo version. A Kong upgrade is not required by any locked decision or Phase 5 requirement, so it should remain out of this phase unless a later bounded upgrade task is explicitly introduced. [VERIFIED: compose.yaml][CITED: https://developer.konghq.com/gateway/version-support-policy/]

3. **How much gateway evidence should be persisted versus derived at request time?**
   - Resolution: Do not invent a new persistence table for Kong-only denials. Represent gateway-only `429` and oversized-body evidence from Kong config, read-only log evidence, and verification artifacts, while keeping FastAPI persistence limited to requests that actually reach the backend. This matches D-14 exactly and keeps the admin gateway surface truthful. [VERIFIED: 05-CONTEXT.md][CITED: https://developer.konghq.com/gateway/db-less-mode/]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Backend tooling / local scripts | ✓ | `3.12.5` | Use the backend container for project commands that require Python `>=3.13,<3.14`. [VERIFIED: backend/pyproject.toml] |
| Node.js | Frontend build/tests | ✓ | `v22.16.0` | — |
| npm | Frontend package scripts | ✓ | `10.9.2` | — |
| Docker Engine | Compose topology, Kong, backend, frontend, sandbox | ✓ | `27.2.0` | — |
| Docker Compose | Required local startup contract | ✓ | `v2.29.2-desktop.2` | — |
| `pip` | Python package verification / host install fallback | ✓ | `26.0.1` | Use container image installs for reproducibility. |
| `pytest` on host | Fast local backend test execution | ✗ | — | Run pytest inside the backend container or install backend dev dependencies locally. [VERIFIED: backend/pyproject.toml] |
| `cloudflared` | Optional Cloudflare Tunnel demo path | ✗ | — | Keep Cloudflare documentation-only for local demo; local Compose remains primary. [VERIFIED: 05-CONTEXT.md] |

**Missing dependencies with no fallback:**
- None for planning. [VERIFIED: compose.yaml]

**Missing dependencies with fallback:**
- Host `pytest` is missing; use containerized backend test runs or install dev dependencies. [VERIFIED: backend/pyproject.toml]
- `cloudflared` is missing; keep Cloudflare as an optional documented edge path only. [VERIFIED: 05-CONTEXT.md]

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Backend: `pytest` via `backend/pyproject.toml`; Frontend: Node/`tsx --test` via `frontend/package.json`. [VERIFIED: backend/pyproject.toml][VERIFIED: frontend/package.json] |
| Config file | Backend: `backend/pyproject.toml`; Frontend: no separate config file detected. [VERIFIED: backend/pyproject.toml][VERIFIED: frontend/package.json] |
| Quick run command | `docker compose run --rm backend python -m pytest tests/unit/test_logging.py -q && npm --prefix frontend test -- frontend/tests/auth-session.test.ts` [VERIFIED: compose.yaml][VERIFIED: backend/tests/unit/test_logging.py][VERIFIED: frontend/tests/auth-session.test.ts] |
| Full suite command | `docker compose run --rm backend python -m pytest && npm --prefix frontend test` [VERIFIED: compose.yaml][VERIFIED: backend/pyproject.toml][VERIFIED: frontend/package.json] |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTHZ-02 | Admin role/scope enforcement on all admin APIs | integration | `docker compose run --rm backend python -m pytest tests/integration/admin/test_admin_evidence.py -q` | ✅ |
| IDEN-03 | OAuth redirect/callback/state flow | integration | `docker compose run --rm backend python -m pytest tests/integration/auth/test_oauth_flows.py -q` | ❌ Wave 0 |
| IDEN-06 | Google provider enabled/disabled behavior | integration | `docker compose run --rm backend python -m pytest tests/integration/auth/test_google_oauth.py -q` | ❌ Wave 0 |
| IDEN-07 | GitHub provider enabled/disabled behavior | integration | `docker compose run --rm backend python -m pytest tests/integration/auth/test_github_oauth.py -q` | ❌ Wave 0 |
| IDEN-08 | Fail-closed link/provision rules for missing/unverified/conflicting email | integration | `docker compose run --rm backend python -m pytest tests/integration/auth/test_oauth_account_linking.py -q` | ❌ Wave 0 |
| GATE-01 | Approved Kong DB-less routes only | smoke | `docker compose run --rm backend python -m pytest tests/smoke/test_topology.py -q` | ✅ |
| GATE-02 | Strict CORS on allowed origins/methods/headers | integration | `docker compose run --rm backend python -m pytest tests/integration/gateway/test_cors.py -q` | ❌ Wave 0 |
| GATE-03 | Route-specific rate limits and `429` metadata | smoke | `docker compose run --rm backend python -m pytest tests/integration/gateway/test_rate_limits.py -q` | ❌ Wave 0 |
| GATE-04 | Request-size limit and correlation propagation | integration | `docker compose run --rm backend python -m pytest tests/integration/gateway/test_request_size_and_correlation.py -q` | ❌ Wave 0 |
| GATE-05 | Kong JWT screening without replacing backend authority | integration | `docker compose run --rm backend python -m pytest tests/security/test_jwt_profile.py -q` | ✅ |
| GATE-06 | No public exposure of control-plane ports | smoke | `docker compose run --rm backend python -m pytest tests/smoke/test_topology.py -q` | ✅ |
| GATE-07 | Documented Cloudflare -> Kong -> FastAPI path and trust assumptions | manual/doc review | `n/a` | ❌ Wave 0 |
| GATE-08 | Cloudflare optional-edge documentation and limits | manual/doc review | `n/a` | ❌ Wave 0 |
| OBS-01 | Correlation ID through gateway/app/evidence/response | smoke | `docker compose run --rm backend python -m pytest tests/smoke/test_logging_flow.py -q` | ✅ |
| OBS-02 | Structured JSON logs plus recursive redaction | unit | `docker compose run --rm backend python -m pytest tests/unit/test_logging.py -q` | ✅ |
| OBS-03 | Typed evidence for auth/admin/replay/rate-limit/tool/sandbox events | integration | `docker compose run --rm backend python -m pytest tests/integration/admin/test_admin_evidence.py -q` | ✅ (partial) |
| OBS-04 | Tool execution summaries remain bounded and correlated | integration | `docker compose run --rm backend python -m pytest tests/smoke/test_admin_flow.py -q` | ✅ |
| OBS-05 | Admin can page through all evidence surfaces | frontend+integration | `docker compose run --rm backend python -m pytest tests/smoke/test_admin_flow.py -q && npm --prefix frontend test -- frontend/tests/chat-workspace.test.ts` | ✅ (partial frontend placeholders) |
| OBS-06 | Ordinary users and under-scoped admins denied | integration | `docker compose run --rm backend python -m pytest tests/integration/admin/test_admin_evidence.py -q` | ✅ |
| OBS-07 | Bounded aggregate metrics only | integration | `docker compose run --rm backend python -m pytest tests/smoke/test_admin_flow.py -q` | ✅ |
| PRODREADY-01 | Environment-only production profile configuration | unit/integration | `docker compose run --rm backend python -m pytest tests/unit/test_config.py -q` | ✅ (OAuth vars missing) |
| PRODREADY-02 | Consistent secure cookies/CORS/trusted-proxy/public URL policy | integration | `docker compose run --rm backend python -m pytest tests/integration/gateway/test_production_profile.py -q` | ❌ Wave 0 |
| PRODREADY-03 | Migration/bootstrap/backup/restore guidance testability | integration/manual | `docker compose run --rm backend python -m pytest tests/integration/cli/test_provisioning.py -q` | ✅ (backup/restore docs gap) |
| PRODREADY-04 | Smoke checks across local, OAuth, gateway, admin, chat, Search, Python | smoke | `docker compose run --rm backend python -m pytest tests/smoke -q` | ✅ (OAuth/gateway gaps) |
| PRODREADY-05 | Explicit documented prototype limits for ~100 users/month | manual/doc review | `n/a` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `docker compose run --rm backend python -m pytest tests/unit/test_logging.py -q` plus the smallest touched frontend test file. [VERIFIED: backend/tests/unit/test_logging.py][VERIFIED: frontend/tests/auth-session.test.ts]
- **Per wave merge:** `docker compose run --rm backend python -m pytest tests/integration/admin tests/integration/auth tests/integration/gateway tests/smoke -q && npm --prefix frontend test` [VERIFIED: backend/pyproject.toml][VERIFIED: frontend/package.json]
- **Phase gate:** Full suite green plus manual verification of OAuth provider callbacks and Kong route behavior before `/gsd-verify-work`. [VERIFIED: 05-CONTEXT.md]

### Wave 0 Gaps
- [ ] `backend/tests/integration/auth/test_oauth_flows.py` — end-to-end redirect/callback/state handling for both providers.
- [ ] `backend/tests/integration/auth/test_oauth_account_linking.py` — verified email match, missing email, conflicting identity, and auto-provision cases.
- [ ] `backend/tests/integration/gateway/test_cors.py` — exact origins/methods/headers and browser preflight coverage through Kong.
- [ ] `backend/tests/integration/gateway/test_rate_limits.py` — route-specific `429` behavior and response headers.
- [ ] `backend/tests/integration/gateway/test_request_size_and_correlation.py` — oversized body rejection plus correlation propagation/validation.
- [ ] `backend/tests/integration/gateway/test_production_profile.py` — trusted proxy, secure-cookie, and public-URL profile checks.
- [ ] `backend/tests/smoke/test_oauth_google_flow.py` and `backend/tests/smoke/test_oauth_github_flow.py` — full-stack provider login smoke coverage.
- [ ] `frontend/tests/admin-evidence.test.tsx` — real admin page/data wiring and access-denied rendering.
- [ ] `frontend/tests/account-access-oauth.test.tsx` — configured/disabled provider button behavior.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Backend-owned auth-code redirect flows, RS256 first-party access JWTs, refresh-token families, and fail-closed provider linking. [VERIFIED: backend/app/security/access_tokens.py][VERIFIED: backend/app/services/sessions.py][CITED: https://docs.authlib.org/en/v1.6.2/client/starlette.html] |
| V3 Session Management | yes | Existing refresh rotation, replay revocation, HttpOnly refresh cookie, CSRF token, and Origin checks must continue across OAuth login. [VERIFIED: backend/app/services/sessions.py][VERIFIED: backend/app/security/csrf.py] |
| V4 Access Control | yes | FastAPI remains authoritative for role/scope/account-state enforcement even after gateway JWT screening. [VERIFIED: backend/app/authorization/principal.py][VERIFIED: backend/app/authorization/policy.py][CITED: https://developer.konghq.com/plugins/jwt/] |
| V5 Input Validation | yes | Pydantic request models, exact origin lists, allowed metadata fields, and route-level gateway limits. [VERIFIED: backend/app/schemas/auth.py][VERIFIED: backend/app/core/config.py][VERIFIED: backend/app/models/domain.py] |
| V6 Cryptography | yes | Existing RS256 JWT handling, HMAC-based refresh lookup, and HMAC CSRF tokens; do not replace with custom crypto. [VERIFIED: backend/app/security/access_tokens.py][VERIFIED: backend/app/security/refresh_tokens.py][VERIFIED: backend/app/security/csrf.py] |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| OAuth CSRF / callback swap | Spoofing | Provider `state` handling via OAuth client library plus backend-only callback handling. [CITED: https://docs.authlib.org/en/v1.6.2/client/starlette.html] |
| Account takeover by unverified or conflicting provider email | Elevation of Privilege | Link only verified normalized email matches; otherwise fail closed and provision only safe new-user cases. [VERIFIED: 05-CONTEXT.md][CITED: https://developers.google.com/identity/openid-connect/openid-connect] |
| Spoofed client IP through untrusted headers | Spoofing | Explicit trusted-proxy chain and Cloudflare/Kong header trust rules only from known upstreams. [CITED: https://developers.cloudflare.com/support/troubleshooting/restoring-visitor-ips/restoring-original-visitor-ips/] |
| Gateway bypass of backend authorization semantics | Elevation of Privilege | Keep Kong JWT plugin as coarse screening only and re-check token/account/scope/ownership in FastAPI. [CITED: https://developer.konghq.com/plugins/jwt/][VERIFIED: backend/app/authorization/principal.py] |
| Secret leakage in logs or admin evidence | Information Disclosure | Extend current recursive sanitizer into evidence serialization and test canary-secret non-leakage. [VERIFIED: backend/app/core/logging.py][VERIFIED: backend/tests/security/test_secret_leakage.py] |
| Admin evidence overexposure | Information Disclosure | Bounded paging, summary-first tables, sanitized snippets, and `admin:read` / `admin:write` separation. [VERIFIED: backend/app/services/admin_evidence.py][VERIFIED: 05-CONTEXT.md] |
| Brute-force or abuse bursts on login/tool endpoints | Denial of Service | Route-specific Kong rate limits, backend fail-closed auth responses, and smoke/integration verification. [CITED: https://developer.konghq.com/plugins/rate-limiting/][VERIFIED: backend/tests/integration/auth/test_login.py] |
| Oversized-body or malformed traffic hitting app workers | Denial of Service | Kong request-size limits at ingress before FastAPI. [CITED: https://developer.konghq.com/plugins/request-size-limiting/] |

## Sources

### Primary (HIGH confidence)
- `backend/app/api/routes/auth.py` - existing backend-owned session/cookie model. [VERIFIED: backend/app/api/routes/auth.py]
- `backend/app/security/access_tokens.py` - existing RS256 access-token contract and validation rules. [VERIFIED: backend/app/security/access_tokens.py]
- `backend/app/services/sessions.py` - existing refresh rotation and replay handling. [VERIFIED: backend/app/services/sessions.py]
- `backend/app/services/admin_evidence.py` - existing admin authorization/evidence patterns. [VERIFIED: backend/app/services/admin_evidence.py]
- `backend/app/core/logging.py` - existing structured logging and recursive sanitization. [VERIFIED: backend/app/core/logging.py]
- `backend/app/models/account.py` - existing identity persistence model and unique `(issuer, subject)` constraint. [VERIFIED: backend/app/models/account.py]
- `kong/kong.yml` and `compose.yaml` - current DB-less gateway shape and public port exposure. [VERIFIED: kong/kong.yml][VERIFIED: compose.yaml]

### Secondary (MEDIUM confidence)
- None collected at MEDIUM via the configured provider-confidence seam in this session. [VERIFIED: classify-confidence]

### Tertiary (LOW confidence)
- https://docs.authlib.org/en/v1.6.2/client/starlette.html - Authlib Starlette OAuth redirect/callback flow. [CITED: https://docs.authlib.org/en/v1.6.2/client/starlette.html]
- https://pypi.org/project/Authlib/ - Authlib release metadata. [CITED: https://pypi.org/project/Authlib/]
- https://developers.google.com/identity/openid-connect/openid-connect - stable Google identity claims and email guidance. [CITED: https://developers.google.com/identity/openid-connect/openid-connect]
- https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps - GitHub OAuth scopes. [CITED: https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps]
- https://docs.github.com/en/rest/users/emails?apiVersion=2022-11-28 - GitHub email retrieval semantics. [CITED: https://docs.github.com/en/rest/users/emails?apiVersion=2022-11-28]
- https://developer.konghq.com/gateway/db-less-mode/ - DB-less declarative configuration constraints. [CITED: https://developer.konghq.com/gateway/db-less-mode/]
- https://developer.konghq.com/plugins/cors/ - Kong CORS route/preflight guidance. [CITED: https://developer.konghq.com/plugins/cors/]
- https://developer.konghq.com/plugins/correlation-id/ - Kong correlation header generation/propagation. [CITED: https://developer.konghq.com/plugins/correlation-id/]
- https://developer.konghq.com/plugins/rate-limiting/ - Kong rate-limit headers/policies. [CITED: https://developer.konghq.com/plugins/rate-limiting/]
- https://developer.konghq.com/plugins/request-size-limiting/ - Kong request-size blocking behavior. [CITED: https://developer.konghq.com/plugins/request-size-limiting/]
- https://developer.konghq.com/plugins/jwt/ - Kong JWT plugin scope and caveats. [CITED: https://developer.konghq.com/plugins/jwt/]
- https://developer.konghq.com/gateway/version-support-policy/ - Kong lifecycle guidance. [CITED: https://developer.konghq.com/gateway/version-support-policy/]
- https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/ - Cloudflare Tunnel role. [CITED: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/]
- https://developers.cloudflare.com/waf/ - Cloudflare WAF as optional edge protection. [CITED: https://developers.cloudflare.com/waf/]
- https://developers.cloudflare.com/turnstile/ - Turnstile integration point. [CITED: https://developers.cloudflare.com/turnstile/]
- https://developers.cloudflare.com/bots/get-started/bot-fight-mode/ - Bot Fight Mode limits and scope. [CITED: https://developers.cloudflare.com/bots/get-started/bot-fight-mode/]
- https://developers.cloudflare.com/support/troubleshooting/restoring-visitor-ips/restoring-original-visitor-ips/ - trusted proxy and original client-IP restoration guidance. [CITED: https://developers.cloudflare.com/support/troubleshooting/restoring-visitor-ips/restoring-original-visitor-ips/]

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM - The core recommendation is anchored in existing repo seams plus official docs, but the new OAuth dependency carries a `SUS` legitimacy verdict and official web sources were classified LOW by the seam. [VERIFIED: backend/app/models/account.py][VERIFIED: package-legitimacy check]
- Architecture: HIGH - The recommended ownership split is strongly grounded in the current codebase and locked user decisions. [VERIFIED: backend/app/api/routes/auth.py][VERIFIED: backend/app/services/admin_evidence.py][VERIFIED: 05-CONTEXT.md]
- Pitfalls: MEDIUM - The major pitfalls are supported by official Google/Kong/Cloudflare docs plus concrete codebase exposure points. [CITED: https://developers.google.com/identity/openid-connect/openid-connect][VERIFIED: backend/app/schemas/admin.py]

**Research date:** 2026-06-15
**Valid until:** 2026-06-22
