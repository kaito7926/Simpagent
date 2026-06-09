# Walking Skeleton - SimpAgent

**Phase:** 01
**Generated:** 2026-06-08

## Capability Proven End-to-End

A local user can open the Next.js account-access page, submit a real registration and login, and see the safe identity returned by FastAPI from PostgreSQL while the full development topology runs with `docker compose up --build`.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Frontend framework | Next.js 16.2 App Router, React 19.2, TypeScript 5.9, Tailwind CSS 4.3 | Required project stack and approved Phase 1 UI contract |
| Backend framework | FastAPI 0.136 with Pydantic 2 settings and schemas | Provides typed transport boundaries, dependency injection, and testable application factories |
| Data layer | PostgreSQL 18.4, SQLAlchemy 2.0 typed mappings, Psycopg 3, reviewed Alembic revisions | Required durable store; refresh locking and security tests must use PostgreSQL semantics |
| Authentication | Local email/password adapter using Argon2id, strict RS256 access JWTs, opaque hashed refresh-token families | Satisfies local v1 access while preserving a replaceable `IdentityProvider` boundary |
| Browser session | Access token in memory; `__Host-` HttpOnly refresh cookie plus family-bound CSRF cookie/header | Limits JavaScript exposure and supports rotation, revocation, and replay detection |
| Authorization authority | FastAPI reconstructs the current principal and rejects inactive or unknown account/policy state | Gateway checks remain coarse; application authorization fails closed |
| Deployment target | Local Docker Compose with DB-less Kong, private PostgreSQL, and a health-only sandbox foundation | Required startup path and Phase 1 trust-boundary demonstration |
| Directory layout | `frontend/`, `backend/`, `kong/`, `sandbox/`; backend split into API, identity, security, authorization, services, repositories, and models | Keeps security responsibilities explicit and supports later vertical slices |
| UI scope | One `/` route for readiness, registration, login, `/me`, logout, and session-expired states | Matches the approved account-access walking skeleton without pulling chat or admin UI forward |

## Stack Touched in Phase 1

- [ ] Project scaffold: container builds, package manifests, lint/type/test configuration
- [ ] Routing: `/`, `/health`, `/ready`, and `/api/auth/{register,login,refresh,logout,me}`
- [ ] Database: real account/session writes and current-user reads through PostgreSQL
- [ ] UI: registration, login, current identity, logout, readiness, and expired-session interactions
- [ ] Deployment: `docker compose up --build` starts frontend, backend, PostgreSQL, Kong, and sandbox foundation

## Walking Skeleton Sequence

1. `01-01` creates the PostgreSQL-only Wave 0 harness, injectable application boundaries, secret-canary checks, health-only sandbox, and failing full-stack account contract.
2. `01-02` implements the real PostgreSQL registration/login/`/me` API with D-01/D-02 fixed account authority.
3. `01-03` makes the earliest executable path pass through the real Next.js -> Kong -> FastAPI -> PostgreSQL topology.
4. `01-04` hardens provider-neutral identity, JWT semantics, current principals, and unknown-state denial.
5. `01-05` adds atomic refresh rotation, replay-family revocation, CSRF/Origin enforcement, and current-family logout.
6. `01-06` completes browser single-flight restoration, retry, expiry, logout, and the approved account-access UI states.
7. `01-07` completes the reviewed schema, production configuration invariants, readiness, and provider degradation.
8. `01-08` depends on every prior plan, enforces D-03 through D-05, completes readiness/demo UI, and runs the final fresh-volume assembled verification.

## Dependency Graph

```text
01-01
  -> 01-02
       -> 01-03
       -> 01-04 -> 01-05 -> 01-06
       -> 01-07

01-01 through 01-07 -> 01-08 final assembled gate
```

| Wave | Plans | Shared-write rule |
|---|---|---|
| 1 | 01-01 | Foundation only |
| 2 | 01-02 | Backend account slice |
| 3 | 01-03, 01-04, 01-07 | No overlapping `files_modified` |
| 4 | 01-05 | Follows auth-route/JWT writers |
| 5 | 01-06 | Follows backend session and initial frontend writers |
| 6 | 01-08 | Depends on all prior plans and owns final evidence |

## Out of Scope

- Conversation and message APIs or UI
- Direct LLM chat, streaming, Markdown rendering, or model controls
- Google Search execution, grounding, citations, or search controls
- Python execution; the sandbox service is health-only in this phase
- Admin evidence APIs or admin UI
- External OAuth2/OIDC login, discovery, ID tokens, UserInfo, or OP claims
- Password reset, email verification, MFA, session/device management, and logout-all
- Phase 5 gateway hardening, Cloudflare configuration, and distributed rate limiting

## Subsequent Slice Plan

- Phase 2: private direct chat and owner-only conversation history
- Phase 3: policy-controlled Google Search with grounded evidence
- Phase 4: isolated bounded Python execution
- Phase 5: hardened gateway, administration, and correlated security evidence
- Phase 6: adversarial verification and Vietnamese delivery documentation

## Source Coverage Audit

| Source | ID | Feature or constraint | Plan | Status |
|---|---|---|---|---|
| GOAL | - | Developers can run the security foundation and users can maintain protected local sessions | 01-01 through 01-08 | COVERED |
| REQ | PLAT-01 | Required Compose startup command | 01-03, 01-08 | COVERED |
| REQ | PLAT-02 | Frontend, backend, PostgreSQL, Kong, and sandbox health topology | 01-01, 01-03, 01-08 | COVERED |
| REQ | PLAT-03 | Reviewed complete Alembic schema foundation | 01-07, 01-08 | COVERED |
| REQ | PLAT-04 | Environment-only secret and security configuration | 01-01, 01-07, 01-08 | COVERED |
| REQ | PLAT-05 | Distinct liveness and readiness | 01-02, 01-07, 01-08 | COVERED |
| REQ | PLAT-06 | Sanitized closed/degraded provider state | 01-07, 01-08 | COVERED |
| REQ | AUTH-01 | Non-enumerating normalized registration | 01-02, 01-04, 01-06 | COVERED |
| REQ | AUTH-02 | Local login with short access token and protected refresh session | 01-02 through 01-06 | COVERED |
| REQ | AUTH-03 | Argon2id and no plaintext leakage | 01-01, 01-02, 01-04 | COVERED |
| REQ | AUTH-04 | Strict access-JWT profile | 01-02, 01-04 | COVERED |
| REQ | AUTH-05 | Opaque hashed atomic refresh rotation | 01-05 | COVERED |
| REQ | AUTH-06 | Replay revokes family and records evidence | 01-05 | COVERED |
| REQ | AUTH-07 | Current-family logout | 01-05, 01-06 | COVERED |
| REQ | AUTH-08 | Safe current identity | 01-02, 01-04, 01-06 | COVERED |
| REQ | AUTH-09 | HttpOnly refresh plus CSRF/Origin/browser protection | 01-03, 01-05, 01-06 | COVERED |
| REQ | AUTH-10 | OIDC-ready identity boundary without OP claims | 01-04 | COVERED |
| REQ | AUTHZ-01 | Missing and inactive principals fail closed | 01-04, 01-06 | COVERED |
| REQ | AUTHZ-08 | Unknown role, scope, tool, and policy states fail closed | 01-04, 01-06 | COVERED |
| CONTEXT | D-01 | Full default User scope bundle | 01-02, 01-04, 01-08 | COVERED |
| CONTEXT | D-02 | Fixed active User registration with no role/scope input | 01-02, 01-04, 01-06 | COVERED |
| CONTEXT | D-03 | Explicit one-time production Admin bootstrap | 01-08 | COVERED |
| CONTEXT | D-04 | Automatic development demo User and Admin | 01-08 | COVERED |
| CONTEXT | D-05 | Demo provisioning blocked outside explicit development mode | 01-08 | COVERED |
| RESEARCH | Patterns 1-4, 7 | Identity boundary, registration, Argon2id, strict JWT, principal reload | 01-02, 01-04 | COVERED |
| RESEARCH | Patterns 5-6 | Refresh family state machine and CSRF/Origin contract | 01-05, 01-06 | COVERED |
| RESEARCH | Patterns 8-9, 11-12 | Schema, Compose topology, readiness, configuration invariants | 01-01, 01-03, 01-07, 01-08 | COVERED |
| RESEARCH | Pattern 10 | One-time production Admin bootstrap | 01-08 | COVERED |
| RESEARCH | Resolved Q1 | Same-origin public Kong route and browser cookie/CSRF smoke | 01-03, 01-05, 01-08 | COVERED |
| RESEARCH | Resolved Q2 | Configured sanitized model status; live grounding check remains Phase 3 | 01-07 | COVERED |
| RESEARCH | Resolved Q3 | Canonical secret files plus development initializer | 01-01, 01-07, 01-08 | COVERED |

No source item is unplanned. Research items explicitly assigned to later phases remain outside this skeleton.
