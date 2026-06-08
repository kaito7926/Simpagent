# Phase 1: Secure Platform and Account Access - Research

**Researched:** 2026-06-08
**Domain:** Secure local identity, strict access tokens, rotating browser sessions, PostgreSQL persistence, and Docker Compose platform startup
**Confidence:** HIGH for platform/auth/session design; MEDIUM for live external-provider availability because no provider credentials were available for a capability probe

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Every newly registered `User` receives the complete standard user scope bundle: `chat:read`, `chat:write`, `tool:websearch`, and `tool:python`.
- **D-02:** Normal registration always creates an active `User` with the fixed standard scope bundle. Clients cannot request, select, or modify roles or scopes during registration.
- **D-03:** The first production Admin is created or promoted only through an explicit one-time bootstrap command. Production must not ship or automatically create default administrator credentials.
- **D-04:** Development mode automatically provisions demo User and Admin accounts when the Compose environment starts.
- **D-05:** Automatic demo provisioning must be gated by an explicit development-mode setting and must not run in production mode.

### the agent's Discretion
- Choose access-token and refresh-session lifetimes, multi-device session behavior, logout scope, and the exact replay-response UX while preserving strict rotation, revocation, and replay detection.
- Choose password policy details, validation error structure, and duplicate-account messaging while preventing account enumeration and following the locked Argon2id requirement.
- Choose demo-account credential values, idempotent reseeding behavior, and how credentials are surfaced in development documentation. Do not commit real secrets, reuse demo credentials outside development, or allow the seed path in production.
- Choose whether absent LLM credentials produce startup failure or a documented degraded provider state. Authentication and database readiness must remain diagnosable, and secret-bearing errors are forbidden.
- Choose module layout, schema details, migration structure, configuration library, test fixtures, and bootstrap command syntax using the project stack and security requirements.

### Deferred Ideas (OUT OF SCOPE)

None - discussion stayed within phase scope.
</user_constraints>

## Summary

Phase 1 should establish one authoritative FastAPI security boundary, not merely a set of auth routes. The implementation should separate account state, provider identities, local password credentials, access-token issuance/validation, and refresh-session persistence so a future OIDC adapter can return the same internal verified-identity object without turning this application into an OpenID Provider. The browser receives a ten-minute RS256 access JWT in the response body and one opaque refresh token in a host-only `Secure`, `HttpOnly`, `SameSite=Strict` cookie. Every protected request must validate the complete token profile and reload the current user so inactive accounts and stale/unknown roles or scopes fail closed. [CITED: https://www.rfc-editor.org/rfc/rfc9068; https://www.rfc-editor.org/rfc/rfc8725; VERIFIED: .planning/phases/01-secure-platform-and-account-access/01-CONTEXT.md]

Refresh handling is the highest-risk implementation area. Use a 32-byte random opaque token, store only an HMAC-SHA-256 lookup digest, represent each login/device as a refresh-token family, and retain every token's parent/replacement state. Rotate under a PostgreSQL row lock in one short transaction. A second concurrent use of the same old token must observe the committed `used_at`/replacement state, revoke the family, persist a security event in that same committed transaction, clear the cookie, and return a generic `401 session_invalid`. Browser code must use a single-flight refresh mutex because strict replay semantics intentionally treat concurrent reuse as compromise. [CITED: https://www.rfc-editor.org/rfc/rfc9700; https://www.postgresql.org/docs/current/explicit-locking.html]

Use Compose one-shot services for migrations and development provisioning, with `service_healthy` and `service_completed_successfully` dependencies. `/health` should be dependency-free liveness. `/ready` should return `503` only when core dependencies such as PostgreSQL or the migration head are not ready; missing/unavailable model providers should produce a sanitized `200` degraded component state so authentication remains operable, while provider-backed feature guards later return `503`. A minimal model-existence checker can use `google-genai` without implementing Google Search; the actual search-grounding capability test remains Phase 3. The official Gemini deprecation page places `gemini-2.5-flash` in its earliest shutdown month in June 2026, so no Phase 1 plan should hardcode or assume that model is available on June 8, 2026. [CITED: https://docs.docker.com/compose/how-tos/startup-order/; https://ai.google.dev/gemini-api/docs/deprecations; https://googleapis.github.io/python-genai/]

**Primary recommendation:** Plan Phase 1 in this order: contracts/configuration and test harness; full reviewed schema and Compose dependency chain; local identity/password/JWT/current-principal flow; refresh/CSRF/logout concurrency flow; then provisioning, provider degradation, and assembled-topology smoke verification.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| Registration and login policy | API / Backend | Database / Storage | FastAPI fixes role/scope defaults and emits generic responses; PostgreSQL enforces uniqueness and stores credential state. [VERIFIED: .planning/REQUIREMENTS.md AUTH-01 through AUTH-03] |
| Password hashing | API / Backend | - | Hashing and verification are trusted backend operations using `pwdlib`/Argon2id; plaintext never crosses into storage or logs. [CITED: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/; https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html] |
| Access-token profile | API / Backend | Kong Gateway | FastAPI issues and fully validates token semantics; Kong is only a later coarse signature/time rejection layer. [CITED: https://www.rfc-editor.org/rfc/rfc9068; VERIFIED: AGENTS.md] |
| Browser refresh session | API / Backend | Browser / Client | Backend owns opaque-token state and rotation; browser stores only the HttpOnly cookie and serializes refresh calls. [CITED: https://www.rfc-editor.org/rfc/rfc9700; https://developer.mozilla.org/en-US/docs/Web/Security/Practical_implementation_guides/Cookies] |
| CSRF and Origin defense | API / Backend | Browser / Client | Backend validates exact Origin plus session-bound CSRF token; browser reads only the non-HttpOnly CSRF cookie and sends a custom header. [CITED: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html] |
| Refresh concurrency and replay | Database / Storage | API / Backend | PostgreSQL row locks serialize state transitions; service logic commits revocation and evidence before mapping the outcome to HTTP. [CITED: https://www.postgresql.org/docs/current/explicit-locking.html] |
| Current principal and fail-closed authorization | API / Backend | Database / Storage | Each protected request validates the token, loads the current user/scopes, rejects inactive or mismatched state, then constructs a typed principal. [VERIFIED: .planning/REQUIREMENTS.md AUTHZ-01 and AUTHZ-08] |
| Local/OIDC-ready identity boundary | API / Backend | Database / Storage | Provider adapters return `(issuer, subject, claims)`; account linking uses a unique issuer-subject record rather than email as external identity. [CITED: https://openid.net/specs/openid-connect-core-1_0-18.html; https://www.rfc-editor.org/rfc/rfc8725] |
| Schema and migration application | Database / Storage | Compose orchestration | Alembic revisions are reviewed artifacts; a one-shot migration service upgrades before seed/backend startup. [CITED: https://alembic.sqlalchemy.org/en/latest/autogenerate.html; https://docs.docker.com/compose/how-tos/startup-order/] |
| Demo provisioning | Compose orchestration | API CLI / Database | Compose invokes an idempotent CLI, but the CLI hard-checks development mode and performs transactional upserts. [VERIFIED: CONTEXT.md D-04 and D-05] |
| Production Admin bootstrap | Operator CLI | API service / Database | A deliberate interactive command creates or promotes the first Admin; normal startup never supplies production Admin credentials. [VERIFIED: CONTEXT.md D-03] |
| Liveness/readiness/provider state | API / Backend | Compose orchestration | The application computes component states; Compose health checks consume stable endpoints without learning secrets. [VERIFIED: .planning/REQUIREMENTS.md PLAT-05 and PLAT-06] |
| Frontend, Kong, and sandbox foundation | Compose orchestration | Individual services | Phase 1 starts health-checkable foundations; chat UI, gateway hardening, and code execution remain later phases. [VERIFIED: .planning/ROADMAP.md Phase 1 boundary] |

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|---|---|---|
| PLAT-01 | Developer can start the required local system with `docker compose up --build`. | Compose dependency graph, one-shot migration/seed services, environment audit, and smoke-test command. |
| PLAT-02 | Compose starts frontend, backend, PostgreSQL, Kong, and Python sandbox foundation with health checks. | Explicit service/network topology and liveness probes; sandbox remains a non-executing foundation. |
| PLAT-03 | Backend applies reviewed Alembic migrations for all required durable models. | Prescriptive schema/index inventory, naming conventions, one-shot migration service, and schema verification tests. |
| PLAT-04 | Operator configures secrets, endpoints, models, origins, and security settings through documented environment configuration. | Pydantic Settings model, Docker secrets support, production invariants, and `.env.example` contract. |
| PLAT-05 | Services distinguish liveness from dependency readiness without exposing secrets. | `/health` and `/ready` response/status contract plus migration-head and DB checks. |
| PLAT-06 | Missing credentials or unavailable configured model produces fail-closed/degraded behavior without secret-bearing errors. | Provider-state enum, sanitized reason codes, optional model getter, feature guard, and negative log/API tests. |
| AUTH-01 | Registration uses normalized unique email and avoids account enumeration. | `email-validator`, product-specific case-insensitive email key, generic `202`, equal-work duplicate path, and unique-race handling. |
| AUTH-02 | Valid local login returns short-lived access token plus protected refresh session. | Local provider adapter, ten-minute JWT, cookie profile, family creation, and generic failure path. |
| AUTH-03 | Passwords use Argon2id and never appear in storage, responses, or logs. | NIST-aligned password policy, `pwdlib[argon2]`, SecretStr/redaction rules, and canary tests. |
| AUTH-04 | JWT contains and validates required strict claims and policies. | Complete header/claim profile, PyJWT validation call, semantic post-validation, and negative token corpus. |
| AUTH-05 | Refresh uses opaque server-side-hashed token families with atomic rotation. | Family/token schema, HMAC lookup digest, row-lock algorithm, and real-PostgreSQL integration tests. |
| AUTH-06 | Reuse revokes family, denies request, and records security event. | State machine, commit-before-denial rule, replay response, and concurrent two-request test. |
| AUTH-07 | Logout invalidates active refresh session. | Current-family revocation, idempotent generic `204`, cookie clearing, Origin/CSRF checks, and side-effect tests. |
| AUTH-08 | Authenticated user retrieves safe identity attributes. | `/api/auth/me` response schema and principal reload without credential/session material. |
| AUTH-09 | Refresh token is unavailable to JavaScript and cookie endpoints have CSRF/Origin protection. | `__Host-` cookie profile, signed session-bound double-submit token, exact Origin allowlist, and CORS tests. |
| AUTH-10 | Identity code has an OIDC-ready provider boundary without claiming local auth is an OP. | `IdentityProvider` protocol, issuer-subject identity table, local adapter, fake OIDC contract test, and documentation language. |
| AUTHZ-01 | Protected endpoints reject inactive users and missing principals. | Authoritative principal dependency reloads user and denies missing/inactive state. |
| AUTHZ-08 | Unknown roles, scopes, tools, and policy states fail closed and create redacted evidence. | Closed enums/allowlists, signed-invalid-claim tests, policy result enum, and security-event contract. |
</phase_requirements>

## Project Constraints (from AGENTS.md)

- Use Next.js/TypeScript/Tailwind for the frontend foundation and FastAPI/Python/Pydantic/SQLAlchemy/PostgreSQL/Alembic for the backend/data foundation. [VERIFIED: AGENTS.md]
- Use local email/password authentication in v1 behind a replaceable standards-based identity boundary. Do not describe local authentication as an OAuth2 Authorization Server or OpenID Provider. [VERIFIED: AGENTS.md]
- Use `PyJWT[crypto]` with an explicit RS256 policy and `pwdlib[argon2]`; do not introduce `python-jose`, Passlib, or long-lived JWT refresh tokens. [VERIFIED: AGENTS.md]
- Keep the access token in browser memory and the refresh token in a protected cookie; never put either token in `localStorage`. [VERIFIED: AGENTS.md]
- Validate tokens and enforce account/role/scope state in FastAPI even if Kong later performs coarse rejection. [VERIFIED: AGENTS.md]
- Use PostgreSQL and reviewed Alembic migrations; use SQLAlchemy 2.0 typed APIs and Psycopg 3. [VERIFIED: AGENTS.md]
- Configure secrets and provider settings externally; never hardcode, log, or send them to model/tool context. [VERIFIED: AGENTS.md]
- `docker compose up --build` is the required startup path; Kong remains DB-less and its Admin API is not host-exposed. [VERIFIED: AGENTS.md]
- Phase 1 must create the sandbox service foundation without executing user Python in FastAPI, on the host, or through a mounted Docker socket. [VERIFIED: AGENTS.md]
- Security-sensitive allow and deny paths need negative tests, and unknown policy states fail closed. [VERIFIED: AGENTS.md]
- User-facing documentation produced later is Vietnamese; Phase 1 code/config names remain English and typed. [VERIFIED: AGENTS.md]
- Prefer a maintainable prototype over production-scale completeness; do not add organizations, external OIDC, session-management UI, or production distributed infrastructure in this phase. [VERIFIED: AGENTS.md; .planning/REQUIREMENTS.md v2/out-of-scope]

## Standard Stack

### Core

| Library / Runtime | Version for Phase 1 | Purpose | Why Standard |
|---|---:|---|---|
| Python | `>=3.13,<3.14` | Backend/runtime baseline | Project stack selects Python 3.13; the local host is 3.12.5, so container builds must supply the required runtime. [VERIFIED: AGENTS.md; local environment probe 2026-06-08] |
| FastAPI | `>=0.136,<0.137` (registry latest `0.136.3`) | API, dependency injection, OpenAPI | Current selected minor and current PyPI release on 2026-05-23. [VERIFIED: PyPI registry 2026-06-08; https://fastapi.tiangolo.com/] |
| Pydantic | `>=2.12,<3` (registry latest `2.13.4`) | Request/response validation and strict domain DTOs | Matches project compatibility range; current PyPI release was uploaded 2026-05-06. [VERIFIED: PyPI registry 2026-06-08; https://docs.pydantic.dev/] |
| pydantic-settings | `>=2.14,<2.15` (registry latest `2.14.1`) | Typed environment and secrets-file configuration | Official settings package reads environment and secrets directories and validates startup invariants. [VERIFIED: PyPI registry 2026-06-08; https://docs.pydantic.dev/latest/concepts/pydantic_settings/] |
| Uvicorn | `>=0.49,<0.50` (registry latest `0.49.0`) | ASGI server | Current PyPI release was uploaded 2026-06-03; pin the tested minor. [VERIFIED: PyPI registry 2026-06-08; https://www.uvicorn.org/] |
| SQLAlchemy | `>=2.0.50,<2.1` | Typed ORM, transactions, row locking | Stable 2.0 line; 2.1 documentation identified by search was still beta, so do not widen the phase to 2.1. [VERIFIED: PyPI registry 2026-06-08; https://docs.sqlalchemy.org/en/20/] |
| Alembic | `>=1.18.4,<1.19` | Reviewed schema migrations | Current stable release; official docs explicitly require manual review/correction of generated candidates. [VERIFIED: PyPI registry 2026-06-08; https://alembic.sqlalchemy.org/en/latest/autogenerate.html] |
| psycopg | `>=3.3,<3.4` with binary extra in containers | PostgreSQL driver for SQLAlchemy sync/async paths | Current registry release is `3.3.4`; use Psycopg 3 and one driver family. [VERIFIED: PyPI registry 2026-06-08; https://www.psycopg.org/psycopg3/docs/] |
| PostgreSQL | `18.4`, image pinned by digest in resolved deployment | Durable security/application state | Current official image lists `18.4`; PostgreSQL 18 uses the changed `/var/lib/postgresql/18/docker` data path beneath the `/var/lib/postgresql` volume. [CITED: https://hub.docker.com/_/postgres] |
| PyJWT with crypto extra | `>=2.13,<3` (registry latest `2.13.0`) | RS256 issuance and verification | Current docs support explicit algorithms, audience, issuer, required claims, and leeway. [VERIFIED: PyPI registry 2026-06-08; https://pyjwt.readthedocs.io/en/latest/usage.html] |
| pwdlib with Argon2 extra | `>=0.3,<0.4` | Password hashing and upgrade checks | `PasswordHash.recommended()` currently selects Argon2 with default parameters; `verify_and_update` supports future rehashing. [VERIFIED: PyPI registry 2026-06-08; https://frankie567.github.io/pwdlib/reference/pwdlib/] |
| email-validator | `>=2.3,<3` | Email syntax and Unicode/domain normalization | Official project returns a normalized address intended for database use and supports disabling DNS checks for login. [VERIFIED: PyPI registry 2026-06-08; https://github.com/JoshData/python-email-validator] |
| Docker Compose | `>=2.35,<3` target | Local topology and one-shot jobs | `service_healthy` and `service_completed_successfully` provide the required dependency ordering. The installed Compose is `2.29.2`, below the project target. [CITED: https://docs.docker.com/compose/how-tos/startup-order/; VERIFIED: local environment probe 2026-06-08] |

### Supporting

| Library | Version | Purpose | When to Use |
|---|---:|---|---|
| google-genai | `>=2.8,<2.9` (registry latest `2.8.0`) | Minimal configured Gemini model-existence check | Use only in the provider health adapter/one-shot check; do not implement Google Search in Phase 1. [VERIFIED: PyPI registry 2026-06-08; https://googleapis.github.io/python-genai/] |
| pytest | `>=9,<10` (registry latest `9.0.3`) | Unit/integration/security tests | All backend validation layers. [VERIFIED: PyPI registry 2026-06-08; https://docs.pytest.org/en/9.0.x/] |
| pytest-asyncio | `>=1.4,<2` (registry latest `1.4.0`) | Explicit async test loop/fixture control | Async SQLAlchemy and ASGI tests. [VERIFIED: PyPI registry 2026-06-08; https://pytest-asyncio.readthedocs.io/] |
| HTTPX | `>=0.28,<1` (registry latest `0.28.1`) | ASGI client and bounded provider probes | API tests via `ASGITransport`; provider probes with explicit timeouts and no redirects. [VERIFIED: PyPI registry 2026-06-08; https://www.python-httpx.org/] |
| Python stdlib `secrets`, `hmac`, `hashlib` | Python 3.13 | Opaque tokens, lookup digests, constant-time comparisons | Generate 32-byte random values and compute keyed digests; do not create a custom cipher or JWT implementation. [CITED: https://docs.python.org/3/library/secrets.html; https://docs.python.org/3/library/hmac.html] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|---|---|---|
| Separate `identities` and `local_credentials` tables | Put `password_hash` directly on `users` | Direct storage is shorter, but creates nullable/provider-specific account fields and makes future `(issuer, subject)` linking a migration rather than an adapter addition. Use the separate tables. [CITED: https://openid.net/specs/openid-connect-core-1_0-18.html] |
| Signed session-bound double-submit CSRF token | Synchronizer token stored in the family row | Both are valid stateful designs. Signed double-submit avoids an additional mutable CSRF column while binding the token to the family; use exact Origin checks as a second control. [CITED: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html] |
| Strict concurrent replay revocation | Small refresh-token grace window | A grace window improves multi-tab UX but conflicts with AUTH-06's required family revocation on reuse and requires storing/recovering replacement material. Use strict revocation plus browser single-flight refresh. [VERIFIED: .planning/REQUIREMENTS.md AUTH-06] |
| One family per login/device and current-family logout | One global family per user | Per-login families avoid logging out every device when one user chooses logout; v2 session-management UI can later enumerate/revoke families. [VERIFIED: .planning/REQUIREMENTS.md IDEN-04 deferred] |
| Provider degraded state | Fail the whole backend startup when LLM credentials are missing | Whole-process failure makes auth/database readiness undiagnosable. Use degraded provider components and fail provider-backed routes closed. [VERIFIED: CONTEXT.md discretion and PLAT-06] |
| Real PostgreSQL integration tests | SQLite test database | SQLite cannot prove PostgreSQL row-lock, partial-index, JSONB, transaction, and migration behavior needed by this phase. Use real PostgreSQL for integration/security tests. [CITED: https://www.postgresql.org/docs/current/explicit-locking.html; https://www.postgresql.org/docs/current/indexes-partial.html] |

**Installation shape:**

```bash
pip install \
  "fastapi>=0.136,<0.137" \
  "uvicorn>=0.49,<0.50" \
  "pydantic>=2.12,<3" \
  "pydantic-settings>=2.14,<2.15" \
  "sqlalchemy>=2.0.50,<2.1" \
  "alembic>=1.18.4,<1.19" \
  "psycopg[binary]>=3.3,<3.4" \
  "PyJWT[crypto]>=2.13,<3" \
  "pwdlib[argon2]>=0.3,<0.4" \
  "email-validator>=2.3,<3" \
  "google-genai>=2.8,<2.9"

pip install \
  "pytest>=9,<10" \
  "pytest-asyncio>=1.4,<2" \
  "httpx>=0.28,<1"
```

[VERIFIED: PyPI registry version checks and slopcheck scans performed 2026-06-08]

## Package Legitimacy Audit

PyPI's JSON API does not expose download counts, so that column is recorded honestly rather than filled from a third-party estimator. Release dates and source links were queried from the primary registry on 2026-06-08. [VERIFIED: https://pypi.org/pypi/]

| Package | Registry | First release / latest checked | Downloads | Source Repo | slopcheck | Disposition |
|---|---|---|---|---|---|---|
| fastapi | PyPI | 2018-12 / `0.136.3` on 2026-05-23 | Not exposed by PyPI JSON | `github.com/fastapi/fastapi` | OK | Approved |
| pydantic | PyPI | 2017-05 / `2.13.4` on 2026-05-06 | Not exposed | `github.com/pydantic/pydantic` | OK | Approved |
| pydantic-settings | PyPI | 2019-08 / `2.14.1` on 2026-05-08 | Not exposed | `github.com/pydantic/pydantic-settings` | OK | Approved |
| sqlalchemy | PyPI | 2006-02 / `2.0.50` on 2026-05-24 | Not exposed | `sqlalchemy.org` | OK | Approved |
| alembic | PyPI | 2011-11 / `1.18.4` on 2026-02-10 | Not exposed | `github.com/sqlalchemy/alembic` | OK | Approved |
| psycopg | PyPI | 2021-08 / `3.3.4` on 2026-05-01 | Not exposed | `github.com/psycopg/psycopg` | OK | Approved |
| PyJWT | PyPI | 2011-02 / `2.13.0` on 2026-05-21 | Not exposed | `github.com/jpadilla/pyjwt` | OK | Approved |
| pwdlib | PyPI | 2024-02 / `0.3.0` on 2025-10-25 | Not exposed | `github.com/frankie567/pwdlib` | OK | Approved |
| email-validator | PyPI | 2015-04 / `2.3.0` on 2025-08-26 | Not exposed | `github.com/JoshData/python-email-validator` | OK | Approved |
| uvicorn | PyPI | 2017-06 / `0.49.0` on 2026-06-03 | Not exposed | `github.com/Kludex/uvicorn` | OK | Approved |
| google-genai | PyPI | 2024-12 / `2.8.0` on 2026-06-03 | Not exposed | `github.com/googleapis/python-genai` | OK | Approved |
| pytest | PyPI | 2010-11 / `9.0.3` on 2026-04-07 | Not exposed | `github.com/pytest-dev/pytest` | OK | Approved |
| pytest-asyncio | PyPI | 2015-04 / `1.4.0` on 2026-05-26 | Not exposed | `github.com/pytest-dev/pytest-asyncio` | OK | Approved |
| httpx | PyPI | 2019-07 / `0.28.1` on 2024-12-06 | Not exposed | `github.com/encode/httpx` | OK | Approved |

**Packages removed due to slopcheck [SLOP] verdict:** none.

**Packages flagged as suspicious [SUS]:** none.

## Architecture Patterns

### System Architecture Diagram

```text
Browser
  |
  | HTTPS/localhost HTTP, Bearer access JWT, refresh + CSRF cookies
  v
Kong (minimal Phase 1 routes and health; DB-less)
  |
  v
FastAPI
  |-- configuration/startup invariants
  |-- IdentityProvider protocol
  |     `-- LocalIdentityProvider (email + Argon2id)
  |-- AccessTokenService (RS256 strict profile)
  |-- PrincipalResolver (JWT + current DB user)
  |-- RefreshSessionService (family state machine)
  |-- AuthorizationPolicy (deny by default)
  |-- ProviderStatusRegistry (ready/degraded/unavailable)
  |
  v
PostgreSQL
  |-- accounts/identities/credentials/scopes
  |-- refresh families/tokens
  |-- future domain tables required by PLAT-03
  `-- audit/security event foundations

Compose startup:
postgres healthy
  -> migrate completes
  -> dev-init/seed completes (no-op unless explicit development gate)
  -> backend healthy/ready
  -> kong and frontend become healthy
  -> sandbox foundation healthy (no execution API yet)
```

[CITED: https://docs.docker.com/compose/how-tos/startup-order/; VERIFIED: .planning/ROADMAP.md Phase 1]

### Recommended Project Structure

```text
backend/
|-- app/
|   |-- api/
|   |   |-- routes/auth.py
|   |   `-- routes/health.py
|   |-- authorization/
|   |   |-- principal.py
|   |   `-- policy.py
|   |-- core/
|   |   |-- config.py
|   |   |-- errors.py
|   |   `-- provider_status.py
|   |-- db/
|   |   |-- base.py
|   |   |-- session.py
|   |   `-- repositories/
|   |-- identity/
|   |   |-- contracts.py
|   |   |-- local_provider.py
|   |   `-- account_linker.py
|   |-- models/
|   |-- schemas/
|   |-- security/
|   |   |-- passwords.py
|   |   |-- access_tokens.py
|   |   |-- refresh_tokens.py
|   |   `-- csrf.py
|   |-- services/
|   |   |-- registration.py
|   |   |-- authentication.py
|   |   `-- sessions.py
|   |-- cli/
|   |   |-- bootstrap_admin.py
|   |   |-- seed_demo.py
|   |   `-- init_dev_secrets.py
|   `-- main.py
|-- alembic/
|-- tests/
|   |-- unit/
|   |-- integration/
|   |-- security/
|   `-- smoke/
|-- pyproject.toml
`-- Dockerfile

frontend/                 # Phase 1 health-checkable shell; auth/chat UI is Phase 2
kong/kong.yml             # Minimal routes only; hardening is Phase 5
sandbox/                  # Health-checkable non-executing foundation
compose.yaml
compose.test.yaml
.env.example
```

### Pattern 1: Provider-Neutral Identity Assertion

Define an internal result that is independent of passwords and OIDC token formats:

```python
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class VerifiedIdentity:
    issuer: str
    subject: str
    email: str | None
    email_verified: bool
    authentication_method: str


class IdentityProvider(Protocol):
    async def authenticate(self, request: object) -> VerifiedIdentity: ...
```

The local adapter verifies email/password and returns a stable local issuer plus a non-email subject. A future OIDC adapter validates an external ID token and returns the external issuer/subject through the same contract. Account linking must query the unique `(issuer, subject)` pair; email is profile data, not an external principal key. [CITED: https://openid.net/specs/openid-connect-core-1_0-18.html; https://www.rfc-editor.org/rfc/rfc8725]

Do not expose authorization-server discovery, authorization endpoints, ID tokens, or UserInfo in Phase 1. Doing so would falsely imply the local password service is an OpenID Provider. [VERIFIED: .planning/REQUIREMENTS.md AUTH-10]

### Pattern 2: Registration Without Role/Scope Input or Enumeration

Registration request schema contains only `email` and `password`. Normalize with `email-validator`, then derive a product login key with `normalized.casefold()` because this product deliberately treats email as a case-insensitive login identifier. Store both the normalized display/login email and the unique case-folded key. Disable deliverability DNS checks because the phase does not send verification mail and must remain deterministic offline. [CITED: https://github.com/JoshData/python-email-validator] [VERIFIED: design choice made under CONTEXT.md discretion]

Perform password normalization/policy validation and Argon2 hashing before deciding whether the account exists. Attempt insertion in a transaction, catch the unique-constraint race, discard the computed hash on duplicates, and return the same `202` status/body for newly created and pre-existing accounts. This keeps HTTP shape and expensive-work path similar. Do not return a user ID from registration because that would distinguish creation. [CITED: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html]

Recommended generic response:

```json
{
  "status": "accepted",
  "message": "If this address can be registered, you can continue to sign in."
}
```

The implementation cannot guarantee perfectly identical network timing, so add a statistical/tolerance test and rate limiting later at Kong rather than claiming timing equality. [CITED: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html]

### Pattern 3: Password Policy and Hash Lifecycle

Use this Phase 1 policy:

- Minimum 15 Unicode code points because the password is the only authentication factor. [CITED: https://pages.nist.gov/800-63-4/sp800-63b.html]
- Maximum 128 Unicode code points and a separate UTF-8 byte ceiling (for example 1024 bytes) before Argon2 to prevent pathological memory/time input. The 128 choice is a project limit above NIST's requirement to permit at least 64. [CITED: https://pages.nist.gov/800-63-4/sp800-63b.html] [VERIFIED: design choice made under CONTEXT.md discretion]
- Apply Unicode NFC before hashing and verification; count code points after normalization. [CITED: https://pages.nist.gov/800-63-4/sp800-63b.html]
- Allow spaces and printable Unicode; impose no uppercase/lowercase/digit/symbol composition rule and no periodic expiry. [CITED: https://pages.nist.gov/800-63-4/sp800-63b.html]
- Reject a bounded local blocklist of common/context-specific passwords, including project name and demo account identifiers; do not make registration call a third-party breach API. [CITED: https://pages.nist.gov/800-63-4/sp800-63b.html]
- Use `PasswordHash.recommended()` and `verify_and_update`; assert generated hashes begin with `$argon2id$`. Benchmark on the target container and keep normal verification below an operationally acceptable threshold without weakening below OWASP's minimum Argon2id baseline. [CITED: https://frankie567.github.io/pwdlib/reference/pwdlib/; https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html]
- For unknown emails, verify against one precomputed dummy Argon2id hash so login avoids a quick-exit timing oracle. Return the same generic `401` for unknown email, wrong password, inactive account, and invalid local identity state. [CITED: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html]

### Pattern 4: Strict Project Access-JWT Profile

Issue only access tokens with:

```text
Header:
  alg = "RS256"
  typ = "at+jwt"
  kid = configured active signing-key id

Claims:
  iss    = exact configured issuer
  aud    = exact configured API audience
  sub    = user UUID as canonical string
  role   = "user" | "admin"
  scopes = sorted unique JSON array
  iat    = integer NumericDate
  nbf    = iat
  exp    = iat + 600 seconds
  jti    = random UUID
```

AUTH-04 names `scopes`, so use that project-specific array rather than introducing a second conflicting `scope` claim. The profile borrows explicit `at+jwt` typing and exact issuer/audience validation from RFC 9068 without claiming full OAuth Authorization Server conformance. [CITED: https://www.rfc-editor.org/rfc/rfc9068; VERIFIED: .planning/REQUIREMENTS.md AUTH-04]

Validation order:

1. Parse the protected header only to select a preconfigured `kid`; reject missing/unknown `kid`, unexpected `typ`, and any `alg` except RS256 before claim use.
2. Call PyJWT with `algorithms=["RS256"]`, exact issuer, exact audience, 30-second leeway, and required `iss`, `aud`, `sub`, `role`, `scopes`, `exp`, `iat`, `nbf`, `jti`.
3. Enforce exact Python/JSON types, UUID formats, `exp > iat`, `nbf <= iat + 30`, `iat <= now + 30`, and maximum lifetime `exp - iat <= 600`.
4. Reject duplicate/unknown scopes and unknown role. Sort scopes at issuance so deterministic tests can compare them.
5. Load the user and current scope rows. Reject inactive/missing users and reject if token role/scopes do not exactly match current account state; issue a fresh token through refresh after legitimate changes.
6. Emit a redacted security event for signature-valid tokens containing unknown role/scope or impossible policy state. Do not create high-volume database events for every random invalid signature.

[CITED: https://www.rfc-editor.org/rfc/rfc8725; https://www.rfc-editor.org/rfc/rfc9068; https://pyjwt.readthedocs.io/en/latest/usage.html]

### Pattern 5: Refresh-Token Family State Machine

Recommended lifetime and device behavior:

- One family per successful login/device.
- Access token: 10 minutes.
- Refresh idle window: 7 days.
- Family absolute lifetime: 30 days.
- Each child expiry is `min(now + 7 days, family.absolute_expires_at)`.
- Logout revokes only the current family. v2 can add a session list and "logout all".
- Optionally cap a user at 10 active families and revoke the oldest inside the login transaction to bound storage/abuse.

[VERIFIED: design choice made under CONTEXT.md discretion] [CITED: https://www.rfc-editor.org/rfc/rfc9700]

State transitions:

```text
ACTIVE token
  -> rotate once -> USED token + ACTIVE child
  -> presented again -> REPLAY -> family REVOKED
  -> logout -> family REVOKED
  -> idle/absolute expiry -> EXPIRED
  -> inactive/missing user -> family REVOKED or denied
```

Generate `secrets.token_bytes(32)`, encode base64url without padding for the cookie, and store `HMAC-SHA-256(refresh_pepper, raw_token)` as a fixed 32-byte unique lookup digest. Keep the pepper in a secrets file separate from PostgreSQL. A keyed lookup hash meets the project requirement and leaves no bearer material in storage. [VERIFIED: AGENTS.md; CITED: https://docs.python.org/3/library/secrets.html; https://docs.python.org/3/library/hmac.html]

Atomic algorithm:

```python
async with session.begin():
    token = await repository.get_token_for_update(token_digest)
    if token is None:
        return RotationOutcome.INVALID

    family = await repository.get_family_for_update(token.family_id)

    if family.revoked_at or family.absolute_expires_at <= now:
        return RotationOutcome.INVALID

    if token.used_at or token.revoked_at or token.replaced_by_id:
        family.revoke(now, reason="refresh_reuse")
        session.add(SecurityEvent.refresh_reuse(family=family, token=token))
        outcome = RotationOutcome.REPLAY_REVOKED
    elif token.expires_at <= now:
        outcome = RotationOutcome.INVALID
    else:
        child, raw_child = issue_child(family, parent=token, now=now)
        token.mark_used(now, replacement=child)
        session.add(child)
        outcome = RotationOutcome.ROTATED(raw_child)

# Map outcome to HTTP only after the transaction commits.
```

Lock token then family in the same order everywhere. PostgreSQL `FOR UPDATE` blocks a competing locker and returns the updated row after the first transaction commits under normal `READ COMMITTED` behavior. [CITED: https://www.postgresql.org/docs/current/explicit-locking.html]

Do not raise the HTTP exception inside a transaction context after mutating replay state; exception-driven rollback is a common way to silently undo the required family revocation and security event. Return a typed outcome, commit, then map to HTTP. [VERIFIED: design requirement derived from AUTH-06]

Concurrent expected result:

```text
request A: locks old token -> creates child -> commits -> may return 200
request B: waits -> reads old token as used -> revokes family + event -> commits -> returns 401
child from A: unusable because its family is now revoked
```

This deliberately forces reauthentication after a duplicate concurrent refresh. The frontend must maintain one in-memory refresh promise/mutex shared by API callers and retry original requests only once after that promise resolves. [CITED: https://www.rfc-editor.org/rfc/rfc9700; VERIFIED: AUTH-06]

### Pattern 6: Cookie, CSRF, Origin, and CORS Contract

Set:

```text
__Host-simpagent_refresh=<opaque>
  Secure; HttpOnly; SameSite=Strict; Path=/; Max-Age=<idle seconds>
  no Domain

__Host-simpagent_csrf=<nonce>.<hmac>
  Secure; SameSite=Strict; Path=/; Max-Age=<family remaining seconds>
  no Domain; intentionally not HttpOnly
```

`Secure` is supported for localhost by modern browsers even over local HTTP, and the `__Host-` prefix requires Secure, host-only scope, and `Path=/`. Test the target browser used for evaluation. [CITED: https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie; https://developer.mozilla.org/en-US/docs/Web/Security/Practical_implementation_guides/Cookies]

Bind the CSRF HMAC to `family_id || nonce`, compare in constant time, and require the browser to copy the readable cookie into `X-CSRF-Token`. For `/refresh` and `/logout`, require:

1. `POST` with JSON/no simple form content.
2. Exact `Origin` member of `ALLOWED_ORIGINS`; reject absent, `null`, suffix matches, and untrusted same-site subdomains.
3. Matching CSRF cookie/header and valid session-bound HMAC.
4. FastAPI CORS configured with explicit origins, credentials enabled, explicit methods, and explicit headers; never `*` with credentials.
5. Optional defense-in-depth rejection of `Sec-Fetch-Site: cross-site`, while Origin remains the required fallback/control.

[CITED: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html; https://fastapi.tiangolo.com/tutorial/cors/]

Apply exact Origin checks to login and registration as login-CSRF defense even before a session exists. Their JSON/custom-header shape can provide preflight protection; they do not need a family-bound token before authentication. [CITED: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html]

On refresh failure/replay/logout, clear both cookies with matching name/path/security attributes. Return a generic `401` code such as `session_invalid`; do not tell an unauthenticated caller whether the cause was expiry, replay, revocation, user inactivity, or CSRF failure. Internally record typed redacted reasons. [VERIFIED: design choice made under CONTEXT.md discretion]

### Pattern 7: Fail-Closed Principal Resolution

Use one dependency pipeline:

```text
Authorization header
  -> strict JWT validator
  -> typed AccessTokenClaims
  -> load user + scopes by sub
  -> verify active, known role, known scopes, token snapshot == current state
  -> AuthenticatedPrincipal
  -> endpoint-specific authorization
```

`/api/auth/me` returns only:

```json
{
  "id": "uuid",
  "email": "normalized@example.com",
  "role": "user",
  "scopes": ["chat:read", "chat:write", "tool:python", "tool:websearch"],
  "is_active": true
}
```

Never return password hash, identity-provider subject, refresh family/token IDs, CSRF material, JWT `jti`, signing metadata, or internal policy reasons. [VERIFIED: AUTH-08]

Represent policy evaluation as a closed enum such as `ALLOW`, `DENY_MISSING_PRINCIPAL`, `DENY_INACTIVE`, `DENY_ROLE`, `DENY_SCOPE`, `DENY_UNKNOWN_STATE`. Any unrecognized role/scope/tool/state maps to `DENY_UNKNOWN_STATE`, not a permissive default branch. [VERIFIED: AUTHZ-01 and AUTHZ-08]

### Pattern 8: PostgreSQL Schema and Index Contract

Use UUID primary keys generated by the application, `timestamptz` timestamps, named foreign keys/checks/uniques, and UTC-aware Python datetimes. Use text plus named CHECK constraints for closed roles/statuses rather than PostgreSQL enum types in the first migration; this keeps review and later value migration explicit. [VERIFIED: design choice made under CONTEXT.md discretion] [CITED: https://alembic.sqlalchemy.org/en/latest/autogenerate.html]

Core identity/session tables:

| Table | Required columns | Key constraints/indexes |
|---|---|---|
| `users` | `id`, `email`, `email_key`, `role`, `is_active`, `is_demo`, `created_at`, `updated_at` | unique `email_key`; role CHECK `user/admin`; index `(created_at, id)` for later admin pagination |
| `user_scopes` | `user_id`, `scope`, `created_at` | PK `(user_id, scope)`; scope CHECK for six known scopes; FK cascade from user |
| `identities` | `id`, `user_id`, `issuer`, `subject`, `email_at_provider`, `email_verified`, `created_at` | unique `(issuer, subject)`; index `user_id`; no password fields |
| `local_credentials` | `user_id`, `password_hash`, `password_updated_at` | PK/FK `user_id`; no plaintext/reversible credential |
| `refresh_token_families` | `id`, `user_id`, `created_at`, `last_rotated_at`, `absolute_expires_at`, `revoked_at`, `revoke_reason` | index `(user_id, created_at desc)`; partial index on active rows `WHERE revoked_at IS NULL`; expiry index |
| `refresh_tokens` | `id`, `family_id`, `jti`, `token_hash`, `parent_token_id`, `replaced_by_id`, `created_at`, `expires_at`, `used_at`, `revoked_at` | unique `token_hash`; unique `jti`; unique nullable `parent_token_id`; indexes `(family_id, created_at)` and `expires_at` |

The unique nullable parent constraint ensures one replacement lineage per token; PostgreSQL allows multiple NULLs while enforcing uniqueness for non-NULL parents. Partial indexes can target active rows, but query predicates must match the index predicate closely to be usable. [CITED: https://www.postgresql.org/docs/current/indexes-partial.html]

PLAT-03 future-domain foundations:

| Table | Phase 1 schema minimum | Important indexes/notes |
|---|---|---|
| `conversations` | `id`, `user_id`, `title`, `created_at`, `updated_at`, optional `deleted_at` | `(user_id, updated_at desc, id)` for stable owner pagination; FK user |
| `messages` | `id`, `conversation_id`, `sequence_no`, `role`, `content`, `metadata` JSONB, `created_at` | unique `(conversation_id, sequence_no)`; index `(conversation_id, sequence_no)`; role CHECK |
| `tool_executions` | `id`, `user_id`, nullable `conversation_id`, `tool_name`, summaries, `status`, `duration_ms`, `correlation_id`, `created_at` | `(user_id, created_at desc)`, `(status, created_at desc)`, correlation index; closed tool/status checks |
| `audit_logs` | `id`, nullable `user_id`, action/resource fields, network/user-agent safe fields, `correlation_id`, `metadata` JSONB, `created_at` | `(created_at desc, id)`, `(user_id, created_at desc)`, correlation index; user FK `SET NULL` |
| `security_events` | `id`, event type/severity, nullable `user_id`, safe network/description/metadata, `correlation_id`, `created_at` | `(event_type, created_at desc)`, `(user_id, created_at desc)`, `(created_at desc, id)` |

Map Python attributes named `event_metadata`/`message_metadata` to SQL column `"metadata"` because SQLAlchemy Declarative reserves `metadata` on mapped classes. [CITED: https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html]

Apply one initial reviewed migration or a small dependency-ordered set:

1. Base identity/account/scope/credential tables.
2. Refresh families/tokens and evidence tables.
3. Conversation/message/tool foundation tables and indexes.

Autogenerate may draft revisions, but manually verify named constraints, CHECKs, partial indexes, JSONB defaults, FK delete behavior, downgrade order, and the exact SQL produced. Add `alembic check` after models and migration agree. [CITED: https://alembic.sqlalchemy.org/en/latest/autogenerate.html]

### Pattern 9: Compose Startup and Network Topology

Recommended services:

```text
postgres       private data network; named volume; no host port
migrate        app image; data network; `alembic upgrade head`; one-shot
dev-init       app image; creates dev signing/HMAC files if selected; one-shot
seed-demo      app image; transactional dev-only demo upsert; one-shot
backend        app + data networks; no direct public host port
frontend       edge/app network; health-checkable shell in Phase 1
kong           edge/app network; DB-less; only public API/health port
sandbox        sandbox-control network only; health endpoint; no Docker socket/execution
```

Dependency chain:

```yaml
services:
  migrate:
    depends_on:
      postgres:
        condition: service_healthy

  seed-demo:
    depends_on:
      migrate:
        condition: service_completed_successfully

  backend:
    depends_on:
      migrate:
        condition: service_completed_successfully
      seed-demo:
        condition: service_completed_successfully
      postgres:
        condition: service_healthy

  kong:
    depends_on:
      backend:
        condition: service_healthy
```

[CITED: https://docs.docker.com/compose/how-tos/startup-order/]

The seed service should always be present so the required command remains exactly `docker compose up --build`, but its CLI must:

- return success without mutation when `DEMO_SEED_ENABLED=false`;
- require both `APP_ENV=development` and `DEMO_SEED_ENABLED=true` before mutation;
- hard-fail on the dangerous combination `APP_ENV!=development` plus enabled seed;
- take a transaction-level advisory lock or deterministic row lock so duplicate Compose starts cannot race;
- upsert only the two fixed demo emails, roles, active state, and exact scope bundles;
- verify the configured password against the existing Argon2 hash and rehash only when it does not match, then revoke that demo account's active refresh families;
- never print or log the password.

[VERIFIED: CONTEXT.md D-04/D-05 and design choice made under its discretion]

Recommended public demo identities are `demo.user@simpagent.test` and `demo.admin@simpagent.test`. Their known development-only passwords may be documented in `.env.example`/Vietnamese README as explicitly public demo values, but real provider keys, JWT private keys, refresh peppers, CSRF keys, and production database passwords must remain placeholders or secret files. [VERIFIED: design choice made under CONTEXT.md discretion] [CITED: https://github.com/JoshData/python-email-validator test environment behavior]

### Pattern 10: One-Time Production Admin Bootstrap

Expose an explicit command:

```bash
docker compose run --rm backend \
  python -m app.cli bootstrap-admin --email admin@example.com
```

The command should use an interactive `getpass` prompt when it must create a local credential; never accept the password as a command-line argument because process listings and shell history can expose arguments. [CITED: https://docs.python.org/3/library/getpass.html]

Transactional rules:

1. Require `APP_ENV=production` or an explicit operator mode; never run from backend startup.
2. Acquire a PostgreSQL transaction advisory lock for the bootstrap operation.
3. If any Admin already exists, fail without mutation.
4. Normalize the email. If a User exists, promote it and replace scopes with the full Admin bundle. If no user exists, create one with a prompted password.
5. Admin bundle should be all standard scopes plus `admin:read` and `admin:write`.
6. Set `is_demo=false`, emit a redacted bootstrap audit/security record, commit, and print only safe identity/result information.
7. A second invocation fails with a safe "admin already bootstrapped" result.

[VERIFIED: CONTEXT.md D-03 and design choice made under its discretion]

### Pattern 11: Health, Readiness, and Provider Degradation

Use stable response contracts:

```json
GET /health -> 200
{"status":"alive"}
```

No database/provider calls and no configuration details. [VERIFIED: design contract selected for PLAT-05]

```json
GET /ready -> 200 or 503
{
  "status": "ready|degraded|not_ready",
  "components": {
    "database": "ready|unavailable",
    "migrations": "ready|out_of_date|unknown",
    "llm": "ready|unconfigured|unavailable",
    "search": "ready|unconfigured|model_unavailable|unavailable",
    "sandbox": "foundation_ready|unavailable"
  }
}
```

Return `503 not_ready` when database connectivity or Alembic head is wrong. Return `200 degraded` when core auth/storage is ready but an external provider is missing/unavailable. Do not include endpoints, model-response bodies, exception strings, keys, credential filenames, DSNs, or stack traces. [VERIFIED: design contract selected for PLAT-05/PLAT-06 under CONTEXT.md discretion]

Provider registry rules:

- Closed state/reason enums; unknown values map to unavailable and create a redacted security/configuration event. [VERIFIED: AUTHZ-08]
- Settings validation catches missing credential/model configuration locally.
- A bounded startup/background check may call `client.models.get(model=...)` through `google-genai` to distinguish configured-but-missing models. It must use short timeout/retry ceilings and cache only the status/reason/timestamp. [CITED: https://googleapis.github.io/python-genai/]
- Do not call a billable generation operation or Google Search in Phase 1. Phase 3 must replace/extend the model getter with a real search-grounding capability smoke test. [VERIFIED: phase boundary in CONTEXT.md]
- Provider-backed feature dependencies later inspect the registry and return sanitized `503 provider_unavailable`; they never silently fall back to an unconfigured model.
- As of June 8, 2026, the last available official deprecation page says `gemini-2.5-flash` has an earliest shutdown date in June 2026 and gives no replacement on that row. Treat the configured Gemini 2 ID as time-sensitive and require a live check rather than a default constant. [CITED: https://ai.google.dev/gemini-api/docs/deprecations]

### Pattern 12: Configuration Invariants

Use one cached immutable `Settings` object and nested settings groups. Load non-secret values from environment and secret values from `/run/secrets` or explicit `*_FILE` paths. Pydantic Settings supports environment and secrets-directory sources; Docker recommends secrets instead of ordinary environment variables for sensitive values. [CITED: https://docs.pydantic.dev/latest/concepts/pydantic_settings/; https://docs.docker.com/compose/how-tos/environment-variables/set-environment-variables/]

Required startup validation:

- `APP_ENV` is exactly `development`, `test`, or `production`.
- Production rejects `DEBUG=true`, `DEMO_SEED_ENABLED=true`, wildcard origins, insecure cookie mode, placeholder secrets, loopback provider URLs, and missing JWT/refresh/CSRF keys.
- `ALLOWED_ORIGINS` is a non-empty parsed list of exact origins and contains no path/query/fragment.
- JWT algorithm is code-fixed to RS256; issuer/audience/kid and key paths are configured. Do not let an environment variable select arbitrary algorithms.
- RSA key size is at least 2048 bits; use 3072 bits for newly generated development keys.
- Refresh pepper and CSRF HMAC key are independent random secrets of at least 32 bytes.
- Database URL is represented as a secret and never included in settings dumps or validation errors.
- Provider base URLs are operator configuration, never request input; production requires HTTPS.
- Settings `repr` and structured validation errors redact `SecretStr`/secret file values.

[CITED: https://www.rfc-editor.org/rfc/rfc8725; https://docs.pydantic.dev/latest/concepts/pydantic_settings/; VERIFIED: AGENTS.md]

`.env.example` should list every variable with safe comments and placeholders, including:

```text
APP_ENV
DEMO_SEED_ENABLED
DEMO_USER_EMAIL / DEMO_USER_PASSWORD
DEMO_ADMIN_EMAIL / DEMO_ADMIN_PASSWORD
DATABASE_* or DATABASE_URL_FILE
JWT_ISSUER / JWT_AUDIENCE / JWT_ACTIVE_KID
JWT_PRIVATE_KEY_FILE / JWT_PUBLIC_KEY_FILE
REFRESH_HMAC_KEY_FILE / CSRF_HMAC_KEY_FILE
ACCESS_TOKEN_TTL_SECONDS
REFRESH_IDLE_TTL_SECONDS / REFRESH_ABSOLUTE_TTL_SECONDS
ALLOWED_ORIGINS
COOKIE_SECURE / COOKIE_SAMESITE
LLM_PROVIDER / LLM_API_BASE / LLM_API_KEY_FILE / LLM_MODEL
GOOGLE_API_KEY_FILE / SEARCH_MODEL
PROVIDER_CHECK_TIMEOUT_SECONDS
```

## Implementation Order

1. **Wave 0: repository/test/config contracts.** Create backend package, `pyproject.toml`, pytest configuration, app factory, typed settings, stable error envelope, fake clock/key fixtures, and real-PostgreSQL test harness. This lets all security logic be tested before routes expand.
2. **Platform persistence and Compose.** Define all PLAT-03 models, naming convention, reviewed migrations, schema verification, private networks, PostgreSQL health, one-shot migration, minimal frontend/Kong/sandbox foundations, and liveness/readiness skeleton.
3. **Identity and account creation.** Implement email normalization/key policy, password policy/Argon2id, identity-provider protocol, local provider, fixed registration defaults, non-enumerating registration/login responses, and development-safe logging.
4. **Access tokens and principals.** Implement RS256 key loading/issuance, strict decoder, negative token corpus, principal reload, `/me`, inactive-user rejection, exact role/scope checks, and unknown-state security events.
5. **Refresh sessions and browser defenses.** Implement family/token schema repositories, login family issuance, signed CSRF cookie, exact Origin/CORS checks, atomic rotation, concurrent replay revocation, current-family logout, cookie clearing, and single-flight frontend utility contract.
6. **Provisioning and provider states.** Implement dev-only idempotent demo seed, one-time production bootstrap command, provider status registry/model getter, sanitized degraded readiness, and production startup invariants.
7. **Assembled verification.** Run fresh-database migration, Compose config, `up --build --wait`, API auth lifecycle, concurrent replay, restart/idempotent seed, no-secret scans, and direct database side-effect assertions.

This order keeps high-level HTTP tasks from depending on an untested schema or ambiguous security contracts and ensures the replay algorithm is tested against PostgreSQL rather than mocked locking. [VERIFIED: research-derived dependency/risk ordering]

### Anti-Patterns to Avoid

- **Password hash on `users` with a nullable future OIDC field:** separates poorly from external identities; use identities plus local credentials.
- **Email regex and lowercase-domain-only uniqueness:** creates equivalent-address or Unicode handling gaps; use the validator's normalized output plus an explicit case-insensitive product key.
- **Client-selected role/scopes:** directly violates D-02; request schemas must not contain those fields.
- **Returning `409 email exists`:** creates an account oracle; return the same registration status/body and similar work path.
- **Trusting a decoded JWT before complete verification:** header/payload data is attacker-controlled until signature and profile validation complete.
- **Using token header `alg` as the decoder allowlist:** enables algorithm confusion; code-fix `["RS256"]`.
- **Treating access-token claims as current authorization forever:** reload current user/scope state and reject stale/inactive principals.
- **Refresh token as JWT:** does not provide the required opaque server-side family state.
- **Plain SHA-256 refresh lookup without a separate key:** random tokens are high entropy, but the project explicitly requires keyed hashing; use HMAC and keep the key outside PostgreSQL.
- **Deleting used refresh rows:** destroys lineage and replay detection; retain them through the family lifetime plus bounded cleanup retention.
- **Grace-period duplicate refresh:** conflicts with mandatory family revocation on rotated-token reuse.
- **Raising before replay revocation commits:** rolls back the security control/evidence.
- **Relying only on SameSite:** OWASP treats it as defense in depth; require exact Origin and CSRF.
- **Naive double-submit cookie:** bind the CSRF token to the authenticated family with HMAC.
- **Applying Alembic migrations in every web worker startup:** creates startup races; use one one-shot migration service.
- **Automatic production Admin environment credentials:** violates D-03 and leaves reusable bootstrap secrets.
- **Seed script that only checks an environment flag:** also require `APP_ENV=development` and fail on dangerous combinations.
- **Readiness that fails all auth when an LLM is absent:** expose degraded provider state and fail only provider features.
- **Readiness that always returns 200:** database/migration failure must return 503.
- **Raw provider exceptions in readiness/logs:** map to bounded reason codes.
- **SQLite integration tests:** cannot prove PostgreSQL locking/index/migration semantics.
- **Sandbox foundation with Docker socket or execution endpoint:** Phase 1 only proves service topology/health.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Password hashing | Custom salt/KDF wrapper | `pwdlib[argon2]` | Encoded parameters, salts, verification, and upgrade behavior are security-sensitive. [CITED: https://frankie567.github.io/pwdlib/] |
| JWT parsing/signature | Base64/cryptography glue | `PyJWT[crypto]` with explicit profile | JOSE parsing and algorithm/key checks have known confusion hazards. [CITED: https://www.rfc-editor.org/rfc/rfc8725] |
| Email syntax/Unicode normalization | Regex | `email-validator` | Internationalized domains/local parts and unsafe Unicode are non-trivial. [CITED: https://github.com/JoshData/python-email-validator] |
| Database migration diff | Startup `create_all()` as migration system | Alembic reviewed revisions | Schema history, indexes, constraints, and downgrade/upgrade behavior need inspectable artifacts. [CITED: https://alembic.sqlalchemy.org/en/latest/autogenerate.html] |
| Refresh concurrency | In-memory locks | PostgreSQL transaction + `FOR UPDATE` | Multiple workers/processes require shared serialization and committed state. [CITED: https://www.postgresql.org/docs/current/explicit-locking.html] |
| Random tokens | Timestamp/UUID concatenation | `secrets.token_bytes(32)` | Use the operating system CSPRNG. [CITED: https://docs.python.org/3/library/secrets.html] |
| Constant-time comparisons | `==` for MACs/digests | `hmac.compare_digest` | Avoid data-dependent comparison behavior. [CITED: https://docs.python.org/3/library/hmac.html] |
| Secret delivery | Committed `.env` values | Compose secrets/files + Pydantic secrets source | Docker explicitly advises against ordinary environment variables for sensitive values. [CITED: https://docs.docker.com/compose/how-tos/environment-variables/set-environment-variables/] |
| Provider capability state | Raw exception passthrough | Typed provider status adapter | Keeps readiness stable, redacted, and testable without coupling auth to providers. [VERIFIED: PLAT-06] |

**Key insight:** the custom work in Phase 1 is the application state machine and policy composition, not cryptographic primitives, parsers, password KDFs, or migration machinery.

## Common Pitfalls

### Pitfall 1: JWT Signature Valid, Token Meaning Invalid
**What goes wrong:** Tokens with wrong issuer, audience, type, lifetime, role, scope, subject, or algorithm are accepted after a successful signature check.

**Why it happens:** Framework examples often demonstrate only `exp` and signature, and callers let the token choose `alg`.

**How to avoid:** Freeze one access-token profile, require every claim, check header `typ`/`kid`, code-fix RS256, enforce claim types/lifetime, then reload current account state.

**Warning signs:** Decoder has no `issuer`/`audience`; tests only cover expired/bad signature; ID-token-shaped JWT reaches an endpoint.

[CITED: https://www.rfc-editor.org/rfc/rfc8725; https://www.rfc-editor.org/rfc/rfc9068]

### Pitfall 2: Refresh Replay Mutation Rolls Back
**What goes wrong:** Code marks the family revoked and inserts an event, then raises `HTTPException`; transaction middleware rolls everything back.

**Why it happens:** HTTP control flow is mixed with transaction control.

**How to avoid:** Service returns a typed outcome, transaction commits, router maps outcome after commit.

**Warning signs:** Replay response is 401 but database still shows active family or no event.

[VERIFIED: derived from AUTH-06 atomic evidence requirement]

### Pitfall 3: Two Browser Tabs Revoke a Legitimate Session
**What goes wrong:** Both send the same cookie; one rotates, the second correctly triggers family revocation.

**Why it happens:** Strict rotation cannot distinguish attacker from legitimate concurrent reuse.

**How to avoid:** Shared browser single-flight refresh promise; one retry maximum; tests document forced reauthentication if concurrency still occurs.

**Warning signs:** Intermittent logout during parallel page loads; multiple refresh calls in network trace.

[CITED: https://www.rfc-editor.org/rfc/rfc9700]

### Pitfall 4: Replay Event Exists but Active Child Still Works
**What goes wrong:** Only the reused token is revoked, not the family, or feature queries ignore family revocation.

**Why it happens:** Token and family status are checked independently/incompletely.

**How to avoid:** Every refresh lookup joins/checks family state; replay sets family revocation; test the child issued by the winning concurrent request.

**Warning signs:** Concurrent test returns one 200 and one 401, but the 200 response token refreshes successfully later.

[VERIFIED: AUTH-06]

### Pitfall 5: Registration Enumeration Through Status, Body, or Work
**What goes wrong:** Duplicate returns `409`, different body, immediate response, or a different validation path.

**Why it happens:** Unique constraints are surfaced directly or existence is checked before hashing.

**How to avoid:** Generic `202`, hash before insert decision, catch unique races, same response envelope, rate limit later.

**Warning signs:** Existing email can be classified reliably from response code/body or large timing gap.

[CITED: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html]

### Pitfall 6: "Normalized" Email Is Not the Product's Unique Key
**What goes wrong:** Validator normalizes domain/Unicode but two local-part case variants create two accounts.

**Why it happens:** SMTP local-part rules and login-identifier UX are conflated.

**How to avoid:** Explicitly define case-insensitive product login semantics and unique `normalized.casefold()` key; use that same function on register/login/bootstrap/seed.

**Warning signs:** Different code paths normalize differently or query raw email.

[CITED: https://github.com/JoshData/python-email-validator] [VERIFIED: design choice made under CONTEXT.md discretion]

### Pitfall 7: SameSite Is Treated as Complete CSRF Protection
**What goes wrong:** Same-site sibling origins, legacy behavior, or cookie injection bypass the only control.

**Why it happens:** "Site" is broader than "origin", and naive double-submit is easy.

**How to avoid:** `__Host-` cookies, exact Origin, session-bound signed double-submit token, custom header, explicit CORS.

**Warning signs:** Refresh succeeds with missing Origin/header or from an unlisted origin.

[CITED: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html]

### Pitfall 8: Demo Seed Escapes into Production
**What goes wrong:** Environment typo creates known Admin credentials in a production database.

**Why it happens:** Seed checks one truthy flag or startup always upserts defaults.

**How to avoid:** Require exact development environment plus explicit enable flag; dangerous mismatch is fatal; production startup never calls a production seed path.

**Warning signs:** Demo emails/password fields appear in production environment or generic startup hooks.

[VERIFIED: CONTEXT.md D-04/D-05]

### Pitfall 9: Production Bootstrap Is Repeatable or Leaks Password
**What goes wrong:** Multiple operators create several Admins, or password appears in shell history/process list/logs.

**Why it happens:** Bootstrap is a normal seed or accepts `--password`.

**How to avoid:** Transaction advisory lock, fail if Admin exists, interactive `getpass`, safe output only.

**Warning signs:** Admin credentials in Compose environment or bootstrap runs on every restart.

[VERIFIED: CONTEXT.md D-03]

### Pitfall 10: Alembic Revision Omits Security Constraints
**What goes wrong:** Models look correct but migration lacks CHECK, partial index, FK action, or unique lineage constraint.

**Why it happens:** Autogenerate is treated as authoritative.

**How to avoid:** Review generated SQL, name every constraint, introspect fresh DB, run `alembic check`.

**Warning signs:** Unnamed constraints, `create_all()` in runtime, or schema tests use only ORM metadata.

[CITED: https://alembic.sqlalchemy.org/en/latest/autogenerate.html]

### Pitfall 11: Compose Starts Containers, Not Ready Services
**What goes wrong:** Backend races PostgreSQL/migrations or Kong routes to an unready backend.

**Why it happens:** Short `depends_on` only orders process start.

**How to avoid:** PostgreSQL health check, `service_healthy`, and one-shot `service_completed_successfully`.

**Warning signs:** First startup fails but restart succeeds; backend logs missing tables.

[CITED: https://docs.docker.com/compose/how-tos/startup-order/]

### Pitfall 12: Degraded Provider State Leaks Secrets or Breaks Auth
**What goes wrong:** Missing key crashes settings with raw value/DSN, `/ready` returns provider exception, or the orchestrator removes backend from service while auth is healthy.

**Why it happens:** All dependencies are treated as equally mandatory.

**How to avoid:** Separate core readiness and feature provider status, use redacted reason enums, and test canary secrets across settings errors/API/logs.

**Warning signs:** Readiness includes URLs with embedded credentials or stack traces; login fails because Gemini is absent.

[VERIFIED: PLAT-05/PLAT-06; AGENTS.md secret policy]

### Pitfall 13: Gemini 2 Model Is Assumed Stable in Its Earliest Shutdown Month
**What goes wrong:** A hardcoded `gemini-2.5-flash` passes planning but is unavailable during implementation/demo.

**Why it happens:** A stale stable-model label is mistaken for a current availability guarantee.

**How to avoid:** Configure the model, call a live model getter in the deployment environment, expose `model_unavailable`, and recheck before Phase 3/demo.

**Warning signs:** No capability check or fallback silently changes model generation.

[CITED: https://ai.google.dev/gemini-api/docs/deprecations; https://ai.google.dev/models/gemini]

## Code Examples

### Strict PyJWT Decode

```python
import jwt


def decode_access_token(token: str, public_key: str, settings: JwtSettings) -> dict:
    claims = jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        audience=settings.audience,
        issuer=settings.issuer,
        leeway=30,
        options={
            "require": [
                "iss",
                "aud",
                "sub",
                "role",
                "scopes",
                "exp",
                "iat",
                "nbf",
                "jti",
            ],
            "verify_signature": True,
            "verify_exp": True,
            "verify_iat": True,
            "verify_nbf": True,
            "verify_aud": True,
            "verify_iss": True,
        },
    )
    # Follow with project-specific type, UUID, role, scope, and lifetime checks.
    return claims
```

[CITED: https://pyjwt.readthedocs.io/en/latest/usage.html; https://www.rfc-editor.org/rfc/rfc8725]

### SQLAlchemy Row Lock

```python
from sqlalchemy import select


stmt = (
    select(RefreshToken)
    .where(RefreshToken.token_hash == token_digest)
    .with_for_update()
)
token = (await session.execute(stmt)).scalar_one_or_none()
```

Use the same lock order in refresh, logout, and administrative revocation paths. Do not share one `AsyncSession` across concurrent tasks. [CITED: https://docs.sqlalchemy.org/en/20/orm/session_basics.html; https://www.postgresql.org/docs/current/explicit-locking.html]

### Pydantic Production Invariant

```python
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SIMPAGENT_",
        secrets_dir="/run/secrets",
        extra="forbid",
    )

    app_env: str
    demo_seed_enabled: bool = False
    cookie_secure: bool = True
    allowed_origins: list[str]

    @model_validator(mode="after")
    def validate_security_mode(self) -> "Settings":
        if self.app_env == "production":
            if self.demo_seed_enabled:
                raise ValueError("demo seed is forbidden in production")
            if not self.cookie_secure:
                raise ValueError("secure cookies are required in production")
            if "*" in self.allowed_origins:
                raise ValueError("wildcard origins are forbidden")
        return self
```

[CITED: https://docs.pydantic.dev/latest/concepts/pydantic_settings/]

### Cookie Setting

```python
response.set_cookie(
    key="__Host-simpagent_refresh",
    value=raw_refresh_token,
    max_age=refresh_idle_seconds,
    path="/",
    secure=True,
    httponly=True,
    samesite="strict",
)
```

Do not set `domain`. Set/clear the CSRF cookie with the same host/path/security shape but `httponly=False`. [CITED: https://developer.mozilla.org/en-US/docs/Web/Security/Practical_implementation_guides/Cookies]

### Signed Session-Bound CSRF Token

```python
import base64
import hashlib
import hmac
import secrets
from uuid import UUID


def issue_csrf_token(family_id: UUID, key: bytes) -> str:
    nonce = secrets.token_bytes(32)
    mac = hmac.digest(key, family_id.bytes + nonce, hashlib.sha256)
    return ".".join(
        base64.urlsafe_b64encode(part).rstrip(b"=").decode("ascii")
        for part in (nonce, mac)
    )
```

Validation must decode with strict length limits and use `hmac.compare_digest`; malformed input maps to the same denial result. [CITED: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html; https://docs.python.org/3/library/hmac.html]

## State of the Art

| Old Approach | Current Approach | When Changed / Current Evidence | Impact |
|---|---|---|---|
| NIST SP 800-63B-3 password minimums | SP 800-63B-4 requires 15 characters for single-factor passwords, no composition rules, and blocklist checks | SP 800-63-4 superseded the prior suite on 2025-08-01. [CITED: https://pages.nist.gov/800-63-4/sp800-63b.html] | Phase 1 should use 15-character minimum rather than legacy 8-character defaults. |
| OAuth 2.0 guidance scattered across threat documents | RFC 9700 BCP explicitly requires replay detection for public-client refresh tokens through sender constraint or rotation | RFC 9700 published January 2025. [CITED: https://www.rfc-editor.org/rfc/rfc9700] | Retain lineage and revoke active family on reuse. |
| Untyped JWT accepted as any token kind | `typ=at+jwt`, exact issuer/audience, mutually exclusive validation profiles | RFC 9068 plus RFC 8725. [CITED: https://www.rfc-editor.org/rfc/rfc9068; https://www.rfc-editor.org/rfc/rfc8725] | Prevent ID-token/access-token confusion. |
| Pydantic v1 settings in core package | Separate `pydantic-settings` package with environment/secrets sources | Current Pydantic v2 docs. [CITED: https://docs.pydantic.dev/latest/concepts/pydantic_settings/] | Plan an explicit settings dependency and secret source. |
| Treat Alembic autogenerate as final | Autogenerate creates candidate migrations requiring manual review | Alembic 1.18.4 docs. [CITED: https://alembic.sqlalchemy.org/en/latest/autogenerate.html] | Add schema SQL/introspection review tasks. |
| PostgreSQL image volume mounted at old major-independent PGDATA path | PostgreSQL 18 uses version-specific `/var/lib/postgresql/18/docker` and volume target `/var/lib/postgresql` | Official image notes for PostgreSQL 18. [CITED: https://hub.docker.com/_/postgres] | Compose volume must use the PostgreSQL 18 layout. |
| Assume a named Gemini stable model remains available | Configure and live-check model availability/capability | `gemini-2.5-flash` entered its documented earliest shutdown month in June 2026. [CITED: https://ai.google.dev/gemini-api/docs/deprecations] | No hardcoded default or silent fallback. |
| ASVS 4-era chapter references | ASVS 5.0 categories: V6 Authentication, V7 Session, V8 Authorization, V9 Self-contained Tokens, V10 OAuth/OIDC, V11 Cryptography | Latest stable ASVS is 5.0.0. [CITED: https://owasp.org/www-project-application-security-verification-standard/] | Validation document should cite versioned ASVS 5 categories. |

**Deprecated/outdated:**

- Passlib for this greenfield Python 3.13 project: use `pwdlib[argon2]` per project stack and current FastAPI guidance. [VERIFIED: AGENTS.md; CITED: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/]
- `python-jose`: use `PyJWT[crypto]` per project stack. [VERIFIED: AGENTS.md]
- Browser `localStorage` for bearer tokens: access token stays in memory; refresh token stays HttpOnly. [VERIFIED: AGENTS.md]
- Startup `Base.metadata.create_all()`: use Alembic migrations. [CITED: https://alembic.sqlalchemy.org/en/latest/autogenerate.html]
- PostgreSQL 18 volume assumptions copied from PostgreSQL 17 examples: use the version-specific official image layout. [CITED: https://hub.docker.com/_/postgres]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | [ASSUMED] The evaluator's browser accepts `Secure` `__Host-` cookies on `http://localhost` exactly as current MDN describes. | Cookie contract | If the target browser differs, local auth cookies need local TLS or an explicitly development-only cookie mode; this must be tested in Compose UAT. |
| A2 | [ASSUMED] A minimal `google-genai` `models.get` call is permitted and useful for the selected Google credential type in the target environment. | Provider degradation | If the API/credential mode does not support this getter, keep the provider checker interface and report `unknown/unavailable` until Phase 3's live capability probe. |
| A3 | [ASSUMED] Ten active refresh families per user is an acceptable prototype bound. | Session behavior | If evaluator workflows need more devices, make the cap configurable while keeping a finite production default. |

## Open Questions

1. **Exact evaluator browser and local URL topology**
   - What we know: frontend and API may use different localhost ports, which are different origins but the same site. [CITED: https://fastapi.tiangolo.com/tutorial/cors/]
   - What's unclear: whether the final demo routes browser API calls through Kong on the same host/origin or cross-origin localhost ports.
   - Recommendation: plan exact origins now, use credentialed explicit CORS, and add a browser smoke test for cookie/CSRF behavior before closing AUTH-09.

2. **Live Gemini 2 availability on implementation/demo date**
   - What we know: the official page places `gemini-2.5-flash` at earliest shutdown in June 2026. [CITED: https://ai.google.dev/gemini-api/docs/deprecations]
   - What's unclear: no Google credentials were available in research, so live availability was not verified on June 8, 2026.
   - Recommendation: Phase 1 implements sanitized model status; Phase 3 must run a real search-grounding capability check and may need to surface a project-constraint conflict if no Gemini 2 model remains.

3. **Production secret provisioning mechanism**
   - What we know: Compose secrets may source files or host environment values, and Pydantic Settings can load a secrets directory. [CITED: https://docs.docker.com/reference/compose-file/secrets/; https://docs.pydantic.dev/latest/concepts/pydantic_settings/]
   - What's unclear: the evaluator may prefer generated local files or manually supplied environment values.
   - Recommendation: support `*_FILE`/`/run/secrets` as canonical, provide a development initializer for random keys, and keep direct secret environment aliases only as documented local fallback.

## Environment Availability

| Dependency | Required By | Available | Version / State | Fallback |
|---|---|---|---|---|
| Docker CLI/daemon | PLAT-01/02 Compose validation | Partial | CLI `27.2.0`; daemon version unavailable during probe | Upgrade/start Docker Desktop before implementation verification |
| Docker Compose | PLAT-01/02 | Yes, below target | `v2.29.2-desktop.2`; project target is `>=2.35` | Upgrade Docker Desktop; do not plan around features newer than the declared minimum without a version gate |
| Python host | Local tooling | Yes, below selected runtime | `3.12.5`; project container target is 3.13 | Build/test in Python 3.13 container |
| Node/npm | Frontend foundation | Yes | Node `22.16.0`, npm `10.9.2` | None currently |
| PostgreSQL CLI | Manual host DB diagnostics | No | `psql` and `pg_isready` absent on host | Use official PostgreSQL container tools |
| OpenSSL | Key inspection/generation support | Yes | `3.3.1` | Python `cryptography` in controlled dev initializer |
| Context7 CLI/MCP | Documentation lookup preference | No | `ctx7` missing | Official primary documentation and registries were used |
| Provider credentials | PLAT-06 live capability probe | Not available in research | No live OpenAI/Google probe performed | Inject fake provider checker in tests; require live operator smoke check later |

[VERIFIED: local environment probes on 2026-06-08]

**Missing dependencies with no fallback for final runtime verification:**

- A running/upgraded Docker daemon is required to prove `docker compose up --build`, PostgreSQL concurrency, and service health.

**Missing dependencies with fallback:**

- Host Python 3.13 and PostgreSQL CLIs are not required if all implementation/test commands run inside the pinned containers.
- Context7 was unavailable; official docs and primary registries provided the source basis.

## Validation Architecture

### Test Framework

| Property | Value |
|---|---|
| Framework | pytest `>=9,<10`, pytest-asyncio `>=1.4,<2`, HTTPX `>=0.28,<1` [VERIFIED: PyPI registry 2026-06-08] |
| Config file | `backend/pyproject.toml` - Wave 0 |
| Unit quick run | `docker compose run --rm backend pytest -q tests/unit -x` |
| Auth integration quick run | `docker compose run --rm backend pytest -q tests/integration/auth -x` |
| Security quick run | `docker compose run --rm backend pytest -q tests/security/test_refresh_replay.py -x` |
| Full backend suite | `docker compose run --rm backend pytest -q` |
| Migration/schema suite | `docker compose run --rm backend pytest -q tests/integration/db/test_migrations.py` |
| Compose smoke | `docker compose up --build --wait && docker compose run --rm backend pytest -q tests/smoke` |

All database integration/security tests must use PostgreSQL 18, not SQLite. Use a dedicated test database/container, apply Alembic to head once per session, and clean data between tests with deterministic truncation or per-test schemas. Do not wrap HTTP integration tests in a transaction invisible to application-created sessions. [CITED: https://www.postgresql.org/docs/current/explicit-locking.html] [VERIFIED: validation architecture selected for this phase]

### Test Layers and Fixtures

| Layer | Purpose | Required fixtures |
|---|---|---|
| Unit | Settings invariants, email/password policy, JWT semantic validation, CSRF HMAC, policy enums, provider-state mapping | fixed clock, generated RSA keys, settings factory, canary secrets, dummy password hash |
| Repository integration | Constraints/indexes, migrations, row locks, refresh state transitions | PostgreSQL 18, migrated schema, async session factory, DB inspection |
| API integration | Registration/login/refresh/logout/me and cookies/errors | FastAPI app factory, HTTPX ASGI transport, real DB, exact Origin/CSRF helpers |
| Concurrency/security | Parallel refresh, duplicate registration, inactive/stale principals, unknown signed claims, side effects | independent clients/sessions, synchronization barrier, direct DB assertions |
| Compose smoke | Build/start ordering, health/readiness, seed idempotency, private service exposure | real Compose stack, shell/API probes, `docker compose ps --format json` |
| Secret leakage | Password/token/key canaries absent from responses, logs, events, settings errors | captured logs, database event queries, response corpus |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| PLAT-01 | Required command builds/starts and reaches expected terminal states | Compose smoke | `docker compose up --build --wait` | No - Wave 0 |
| PLAT-02 | Required five services plus one-shot jobs have correct health/dependencies/networks | Compose/schema | `docker compose config -q && docker compose run --rm backend pytest -q tests/smoke/test_topology.py` | No - Wave 0 |
| PLAT-03 | Fresh DB upgrades to head with all tables/constraints/indexes; metadata has no pending diff | Migration integration | `docker compose run --rm backend pytest -q tests/integration/db/test_migrations.py` | No - Wave 0 |
| PLAT-04 | `.env.example` covers settings; production rejects unsafe/missing values; secrets redact | Unit/config | `docker compose run --rm backend pytest -q tests/unit/test_config.py` | No - Wave 0 |
| PLAT-05 | Liveness ignores dependencies; readiness distinguishes DB/migration failure and reveals no secrets | API integration | `docker compose run --rm backend pytest -q tests/integration/test_health.py` | No - Wave 0 |
| PLAT-06 | Missing/unavailable providers yield sanitized degraded state; feature guard fails closed | Unit/API integration | `docker compose run --rm backend pytest -q tests/integration/test_provider_status.py` | No - Wave 0 |
| AUTH-01 | Normalized unique registration, fixed defaults, duplicate/race generic response | API/concurrency | `docker compose run --rm backend pytest -q tests/integration/auth/test_registration.py` | No - Wave 0 |
| AUTH-02 | Valid login returns 10-minute JWT and protected refresh/CSRF cookies; invalid cases generic | API integration | `docker compose run --rm backend pytest -q tests/integration/auth/test_login.py` | No - Wave 0 |
| AUTH-03 | Argon2id at rest; no plaintext/canary in DB, response, logs, events | Security | `docker compose run --rm backend pytest -q tests/security/test_secret_leakage.py -k password` | No - Wave 0 |
| AUTH-04 | Complete positive/negative strict JWT corpus | Unit/security | `docker compose run --rm backend pytest -q tests/security/test_jwt_profile.py` | No - Wave 0 |
| AUTH-05 | Opaque token hash only, sequential atomic rotation and lineage | Repository/API integration | `docker compose run --rm backend pytest -q tests/integration/auth/test_refresh_rotation.py` | No - Wave 0 |
| AUTH-06 | Old-token reuse and two-request concurrency revoke family, deny, emit event, invalidate child | Concurrency/security | `docker compose run --rm backend pytest -q tests/security/test_refresh_replay.py` | No - Wave 0 |
| AUTH-07 | Logout revokes current family, clears cookies, is idempotent, preserves other family | API integration | `docker compose run --rm backend pytest -q tests/integration/auth/test_logout.py` | No - Wave 0 |
| AUTH-08 | `/me` returns safe fields only | API integration | `docker compose run --rm backend pytest -q tests/integration/auth/test_me.py` | No - Wave 0 |
| AUTH-09 | HttpOnly/Secure/SameSite/host cookies and Origin/CSRF deny matrix with zero mutation | Security/API | `docker compose run --rm backend pytest -q tests/security/test_browser_session.py` | No - Wave 0 |
| AUTH-10 | Local adapter satisfies identity protocol; fake OIDC assertion links by issuer/sub; no OP endpoints | Unit/contract | `docker compose run --rm backend pytest -q tests/unit/identity/test_provider_contract.py` | No - Wave 0 |
| AUTHZ-01 | Missing token and inactive/deleted user after issuance are denied | Security/API | `docker compose run --rm backend pytest -q tests/security/test_principal_fail_closed.py` | No - Wave 0 |
| AUTHZ-08 | Signed token/policy with unknown role/scope/tool/state denies and creates redacted event | Unit/security | `docker compose run --rm backend pytest -q tests/security/test_unknown_policy_state.py` | No - Wave 0 |

### Critical Test Scenarios

1. **Concurrent refresh barrier:** log in once, copy the same cookie/CSRF values into two independent clients, synchronize POST start, assert exactly one rotation attempt can create a child, assert one denial records replay, assert family revoked, and assert the child cannot refresh.
2. **Replay commit test:** inject router mapping that returns/raises only after service completion, then query family/event in a new DB session to prove commit survived the HTTP denial.
3. **Duplicate registration race:** send two normalized-equivalent emails concurrently, assert one user/local identity/credential, identical response status/body, fixed user scopes, and no Admin role.
4. **JWT corpus:** `none`, HS/RS confusion attempt, wrong key/kid/typ/iss/aud, missing each required claim, string NumericDates, expired, future `nbf`/`iat`, excessive lifetime, invalid UUIDs, duplicate scopes, unknown scope/role, and valid token for an account later deactivated.
5. **CSRF matrix:** missing/wrong/null/suffix Origin; missing cookie/header; mismatched token; tampered HMAC; cross-site fetch metadata; valid exact Origin. Assert denied requests do not rotate/revoke except a correctly authenticated old-token replay case.
6. **Provider redaction:** fake exceptions contain API key, DSN, endpoint credentials, and canary values; `/ready`, logs, and events contain only reason code/correlation ID.
7. **Seed/bootstrap:** run seed twice and assert stable two demo users/no duplicate scopes; production-enabled seed fails; bootstrap creates/promotes once; second invocation fails; no password in process output/logs.
8. **Migration fidelity:** upgrade empty DB, inspect named constraints/index predicates/FK actions, downgrade only in disposable DB, re-upgrade, and run `alembic check`.

### Sampling Rate

- **Per task commit:** relevant unit file plus one affected integration file; target under 30 seconds.
- **Per wave merge:** `docker compose run --rm backend pytest -q tests/unit tests/integration`.
- **After refresh/JWT/authz changes:** add `tests/security/test_jwt_profile.py`, `test_refresh_replay.py`, and `test_browser_session.py`.
- **Phase gate:** fresh-volume `docker compose up --build --wait`, full backend suite, Compose smoke, and secret-canary scan green before `$gsd-verify-work`.

### Wave 0 Gaps

- [ ] `backend/pyproject.toml` - dependencies, pytest config, explicit asyncio mode, markers.
- [ ] `backend/tests/conftest.py` - app/settings/key/clock/client fixtures.
- [ ] `backend/tests/fixtures/postgres.py` - migrated PostgreSQL session and cleanup.
- [ ] `backend/tests/fixtures/auth.py` - user/login/cookie/CSRF/token helpers.
- [ ] `backend/tests/unit/test_config.py` - PLAT-04.
- [ ] `backend/tests/integration/db/test_migrations.py` - PLAT-03.
- [ ] `backend/tests/integration/test_health.py` - PLAT-05/06.
- [ ] `backend/tests/integration/auth/` lifecycle test modules - AUTH-01 through AUTH-09.
- [ ] `backend/tests/security/test_jwt_profile.py` - AUTH-04/AUTHZ-08.
- [ ] `backend/tests/security/test_refresh_replay.py` - AUTH-05/06.
- [ ] `backend/tests/security/test_browser_session.py` - AUTH-09.
- [ ] `backend/tests/security/test_secret_leakage.py` - project secret policy.
- [ ] `backend/tests/unit/identity/test_provider_contract.py` - AUTH-10.
- [ ] `backend/tests/security/test_principal_fail_closed.py` - AUTHZ-01.
- [ ] `backend/tests/security/test_unknown_policy_state.py` - AUTHZ-08.
- [ ] `backend/tests/smoke/test_topology.py` - PLAT-01/02.
- [ ] `compose.test.yaml` - isolated PostgreSQL test service/config.

## Security Domain

### Applicable ASVS 5.0 Categories

| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Validation and Business Logic | Yes | Pydantic strict schemas, fixed registration defaults, closed state machines, anti-automation boundary |
| V3 Web Frontend Security | Yes | Secure/HttpOnly/SameSite host cookies, exact Origin, explicit CORS |
| V4 API and Web Service | Yes | Stable JSON errors, content types, no stack traces, health/readiness contracts |
| V6 Authentication | Yes | NIST-aligned password policy, Argon2id, generic responses, local identity adapter |
| V7 Session Management | Yes | Opaque rotating families, idle/absolute expiry, logout, replay revocation |
| V8 Authorization | Yes | Typed principal, active account reload, deny-by-default role/scope/tool policy |
| V9 Self-contained Tokens | Yes | RS256, `at+jwt`, exact profile, key/claim/lifetime validation |
| V10 OAuth and OIDC | Yes, boundary only | Issuer-subject provider contract; no false OP claim; future external OIDC adapter |
| V11 Cryptography | Yes | Library-backed Argon2id/RSA/JWT; CSPRNG; HMAC keys separated from DB |

[CITED: https://owasp.org/www-project-application-security-verification-standard/]

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---|---|---|
| Account enumeration | Information Disclosure | Generic HTTP/body/work path, dummy hash, bounded timing tests |
| Password database theft | Information Disclosure | Argon2id encoded hashes, no plaintext, optional future pepper/HSM |
| JWT algorithm/type confusion | Spoofing/Elevation | RS256 allowlist, `at+jwt`, key binding, exact issuer/audience |
| Stale/inactive principal | Elevation | Reload current user/scopes on every protected request |
| Refresh-token theft/replay | Spoofing | Opaque HMAC lookup, rotation lineage, family revocation |
| Concurrent refresh race | Tampering | PostgreSQL row locks, fixed lock order, committed typed outcome |
| CSRF/login CSRF | Spoofing | Exact Origin, signed family-bound token, custom header, SameSite |
| Demo/admin credential exposure | Elevation | Development gate, no production defaults, interactive one-time bootstrap |
| Secret-bearing diagnostics | Information Disclosure | SecretStr/files, bounded reason enums, canary tests |
| Unknown policy state | Elevation | Closed enums and deny-by-default mapping plus redacted event |
| Migration drift | Tampering | Reviewed Alembic revision, fresh DB introspection, `alembic check` |
| Dependency startup race | Denial of Service | Compose health/completion conditions and readiness |

## Sources

### Primary (HIGH confidence)

- https://www.rfc-editor.org/rfc/rfc9700 - refresh-token rotation, replay detection, active-token revocation, logout/expiry guidance.
- https://www.rfc-editor.org/rfc/rfc8725 - JWT algorithm verification, issuer/subject validation, cross-JWT defenses.
- https://www.rfc-editor.org/rfc/rfc9068 - `at+jwt`, exact issuer/audience/type validation, asymmetric signing recommendation.
- https://openid.net/specs/openid-connect-core-1_0-18.html - issuer/subject identity semantics and provider distinction.
- https://pages.nist.gov/800-63-4/sp800-63b.html - current password length, normalization, composition, blocklist, and storage guidance.
- https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html - Argon2id baseline.
- https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html - generic authentication/registration responses and timing discrepancy.
- https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html - signed double-submit, Origin, custom headers, SameSite limits.
- https://developer.mozilla.org/en-US/docs/Web/Security/Practical_implementation_guides/Cookies - secure cookie prefixes/attributes.
- https://pyjwt.readthedocs.io/en/latest/usage.html - current PyJWT claim/algorithm/audience/issuer/leeway APIs.
- https://frankie567.github.io/pwdlib/ - `PasswordHash.recommended()` and Argon2 support.
- https://github.com/JoshData/python-email-validator - email validation/normalization behavior.
- https://docs.pydantic.dev/latest/concepts/pydantic_settings/ - environment and secrets settings.
- https://docs.sqlalchemy.org/en/20/ - SQLAlchemy 2.0 sessions/select/locking APIs.
- https://alembic.sqlalchemy.org/en/latest/autogenerate.html - candidate migration review and autogenerate limits.
- https://www.postgresql.org/docs/current/explicit-locking.html - PostgreSQL 18 row-lock behavior/deadlocks.
- https://www.postgresql.org/docs/current/indexes-partial.html - partial and partial-unique indexes.
- https://docs.docker.com/compose/how-tos/startup-order/ - Compose health/completion dependency conditions.
- https://docs.docker.com/reference/compose-file/secrets/ - Compose secret sources/grants.
- https://hub.docker.com/_/postgres - PostgreSQL 18.4 image and volume path change.
- https://googleapis.github.io/python-genai/ - model getter API.
- https://ai.google.dev/gemini-api/docs/deprecations - time-sensitive Gemini shutdown schedule.
- https://owasp.org/www-project-application-security-verification-standard/ - ASVS 5.0 stable categories.
- PyPI JSON/`pip index versions` on 2026-06-08 - package versions and release metadata.
- `slopcheck 0.6.1` package scans on 2026-06-08 - all recommended packages returned `OK`.

### Secondary (MEDIUM confidence)

- None used for roadmap-critical conclusions.

### Tertiary (LOW confidence)

- None. Unverified environment/provider assumptions are isolated in the Assumptions Log.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH - package versions were checked against PyPI and official documentation; legitimacy scans passed.
- Authentication/JWT architecture: HIGH - grounded in current RFCs, NIST, OWASP, and official library docs.
- Refresh concurrency: HIGH - grounded in RFC 9700 and PostgreSQL 18 lock semantics; still requires executable real-PostgreSQL tests.
- Compose/readiness: HIGH - grounded in current Docker docs; local daemon was unavailable and installed Compose is below target.
- Provider availability: MEDIUM - official model lifecycle is known, but no credentialed live probe was possible.
- Validation architecture: HIGH - all 18 requirement IDs have concrete automated evidence paths and Wave 0 files.

**Research date:** 2026-06-08

**Valid until:** 2026-07-08 for stable auth/platform guidance; recheck Gemini model availability immediately before Phase 3 implementation and the final demonstration.
