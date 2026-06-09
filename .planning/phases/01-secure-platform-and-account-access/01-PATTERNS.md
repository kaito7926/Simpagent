# Phase 01: Secure Platform and Account Access - Pattern Map

**Mapped:** 2026-06-08
**Repository state:** Greenfield
**Expected file/symbol groups classified:** 38
**Reusable application analogs found:** 0 / 38

## Greenfield Finding

The repository contains no application or product source code. The only current
files are planning artifacts, GSD workflow implementation, editor metadata, and
the original project brief.

- Existing application/source files: **0**
- Existing backend, frontend, migration, Compose, Kong, or sandbox analogs: **0**
- Existing import, error, repository, service, component, or test conventions:
  **none**
- `.codex/**` is workflow tooling and MUST NOT be treated as a product-code
  analog.
- `.planning/**` is the canonical contract source, not executable application
  code.

Therefore every Phase 1 file is a first implementation. The planner must use
the canonical contracts below rather than claiming that a new file copies an
existing repository pattern.

## Canonical Source Order

When sources overlap, use this order:

1. `01-CONTEXT.md` for locked Phase 1 decisions and scope.
2. `01-UI-SPEC.md` for frontend behavior, copy, accessibility, visual tokens,
   and browser session behavior.
3. `01-VALIDATION.md` for required evidence, fixtures, commands, and test paths.
4. `01-RESEARCH.md` for architecture, security state machines, schema, and
   implementation order.
5. `AGENTS.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `PROJECT.md`, and `prompt.md`
   for project-wide constraints.

### Resolved Source Conflict

`01-RESEARCH.md` line 275 describes the frontend as a health-checkable shell
and says auth UI is Phase 2. The later, approved `01-UI-SPEC.md` explicitly
requires a complete Phase 1 account-access walking skeleton. The approved UI
contract is authoritative:

- Phase 1 MUST implement registration, login, session restoration, `/me`,
  logout, readiness states, and development-only demo account controls on `/`.
- Phase 1 MUST NOT implement chat, conversation navigation, model controls,
  tool controls, admin UI, or placeholder future functionality.

## File Classification

Paths below are expected planner targets. A plan may split a grouped row into
several focused files, but it must preserve the responsibility and data flow.
No row has a repository code analog.

| # | Expected File or Symbol Group | Role | Data Flow | Closest Analog | Canonical Contract |
|---:|---|---|---|---|---|
| 1 | `compose.yaml` | config/orchestrator | event-driven startup | None | Research Pattern 9 |
| 2 | `compose.test.yaml` | test config | event-driven startup | None | Validation Wave 0 |
| 3 | `.env.example` | config/documentation | configuration transform | None | Research Pattern 12 |
| 4 | `backend/pyproject.toml`, `backend/Dockerfile` | build/config | batch/build | None | AGENTS stack; Validation Test Infrastructure |
| 5 | `backend/app/main.py` | application factory | request-response/lifespan | None | Research Implementation Order Wave 0 |
| 6 | `backend/app/api/routes/auth.py` | controller/route | request-response | None | AUTH-01 through AUTH-09 |
| 7 | `backend/app/api/routes/health.py` | controller/route | request-response/probe | None | PLAT-05/06; UI readiness contract |
| 8 | `backend/app/core/config.py` | config | environment-to-domain transform | None | Research Pattern 12 |
| 9 | `backend/app/core/errors.py`, `provider_status.py` | utility/service | transform/request-response | None | PLAT-06; UI error mapping |
| 10 | `backend/app/db/base.py`, `session.py` | config/utility | CRUD/transaction | None | SQLAlchemy 2.0; PostgreSQL only |
| 11 | `backend/app/models/{user,identity,credential,scope}.py` | model | CRUD | None | Research Pattern 8 |
| 12 | `backend/app/models/refresh_*.py` | model | CRUD/state machine | None | Research Patterns 5 and 8 |
| 13 | `backend/app/models/{conversation,message,tool_execution}.py` | model foundation | CRUD | None | PLAT-03 minimum schema only |
| 14 | `backend/app/models/{audit_log,security_event}.py` | model/evidence | event-driven append | None | PLAT-03; AUTH-06; AUTHZ-08 |
| 15 | `backend/app/db/repositories/**` | repository | CRUD/locking | None | Research Patterns 5, 7, and 8 |
| 16 | `backend/app/identity/{contracts,local_provider,account_linker}.py` | provider/service | request-response/transform | None | Research Pattern 1 |
| 17 | `backend/app/schemas/{auth,health,errors}.py` | schema | validation/transform | None | UI-SPEC; Research Patterns 2, 7, 11 |
| 18 | `backend/app/security/passwords.py` | security utility | transform | None | Research Pattern 3 |
| 19 | `backend/app/security/access_tokens.py` | security service | transform/request-response | None | Research Pattern 4 |
| 20 | `backend/app/security/{refresh_tokens,csrf}.py` | security utility | transform/state validation | None | Research Patterns 5 and 6 |
| 21 | `backend/app/authorization/{principal,policy}.py` | middleware/policy | request-response/transform | None | Research Pattern 7 |
| 22 | `backend/app/services/{registration,authentication}.py` | service | CRUD/request-response | None | Research Patterns 1 through 4 |
| 23 | `backend/app/services/sessions.py` | service | transactional state machine | None | Research Patterns 5 and 6 |
| 24 | `backend/app/cli/{bootstrap_admin,seed_demo,init_dev_secrets}.py` | CLI/service | batch/CRUD | None | Context D-03 through D-05 |
| 25 | `backend/alembic/**` | migration | batch/schema I/O | None | PLAT-03; Research Pattern 8 |
| 26 | `frontend/package.json` and Next/Tailwind/TypeScript config | build/config | build/transform | None | AGENTS stack; UI Design System |
| 27 | `frontend/app/{layout,page,globals}.tsx/css` and local font assets | page/component | request-response/render | None | UI Layout and Information Architecture |
| 28 | `frontend/components/account-access/**` | component | event-driven/render | None | UI Component Strategy |
| 29 | `frontend/lib/{api,auth-session}.ts` or equivalent | client/service/store | request-response/state machine | None | UI Session Lifecycle |
| 30 | `frontend/lib/{readiness,demo-config}.ts` or equivalent | client/config | polling/transform | None | UI Readiness and Demo contracts |
| 31 | `kong/kong.yml` | gateway config | request-response proxy | None | Minimal Phase 1 DB-less routing |
| 32 | `sandbox/**` | service foundation | health probe only | None | PLAT-02; Research anti-patterns |
| 33 | `backend/tests/conftest.py`, `tests/fixtures/**` | test fixture | setup/CRUD | None | Validation Wave 0 |
| 34 | `backend/tests/unit/**` | test | transform/contract | None | Validation test map |
| 35 | `backend/tests/integration/db/**`, `test_health.py`, `test_provider_status.py` | test | CRUD/probe | None | PLAT-03 through PLAT-06 |
| 36 | `backend/tests/integration/auth/**` | test | request-response/CRUD | None | AUTH-01 through AUTH-09 |
| 37 | `backend/tests/security/**` | negative/security test | adversarial request-response | None | AUTH-03/04/05/06/09; AUTHZ-01/08 |
| 38 | `backend/tests/smoke/test_topology.py` | smoke test | event-driven/probe | None | PLAT-01/02 |

## Pattern Assignments

These are specification-derived assignments. They are not existing code
excerpts.

### Backend Application Boundary

**Applies to:**
`backend/app/main.py`, `backend/app/api/routes/*.py`,
`backend/app/core/errors.py`

**Required symbols and ownership:**

- `create_app(settings: Settings | None = None) -> FastAPI` or an equivalent
  application factory that supports test dependency injection.
- Route handlers validate transport concerns and map typed service outcomes to
  HTTP. They do not own password, token, or transaction logic.
- Services own use-case sequencing.
- Repositories own SQLAlchemy queries, row locks, and persistence operations.
- Security modules own cryptographic-library calls and strict token formats.
- Authorization dependencies own principal reconstruction and fail-closed
  decisions.
- Pydantic response models prevent accidental credential/session fields from
  reaching API responses.

**Error pattern:**

- Define one stable JSON error envelope with a bounded machine code, safe
  message, and optional safe correlation ID.
- Never return raw exception text, SQL errors, provider bodies, settings dumps,
  key paths, DSNs, credentials, or stack traces.
- Service methods return typed outcomes when state must commit before denial.
  Routers map the outcome to HTTP only after the transaction has committed.
- Unknown enum or policy state maps to denial and redacted evidence.

### Configuration

**Applies to:** `backend/app/core/config.py`, `.env.example`, Compose service
configuration.

**Pattern source:** `01-RESEARCH.md` Pattern 12 and `AGENTS.md`.

**Constraints:**

- Use one cached, immutable Pydantic Settings object with nested groups.
- Use `SIMPAGENT_` or one consistently documented environment prefix.
- Load secrets from `/run/secrets` or explicit `*_FILE` paths.
- `APP_ENV` is a closed value: `development`, `test`, or `production`.
- Production rejects demo seeding, debug mode, wildcard origins, insecure
  cookies, placeholder secrets, loopback provider URLs, and missing JWT,
  refresh-HMAC, or CSRF-HMAC keys.
- JWT algorithm is fixed in code to RS256. Environment input must not select an
  arbitrary algorithm.
- RSA keys are at least 2048 bits; generated development keys should be 3072
  bits.
- Refresh and CSRF keys are independent values of at least 32 random bytes.
- Database URLs and secret values are redacted from `repr`, validation errors,
  logs, and API output.
- `.env.example` contains safe placeholders for every required non-secret and
  secret-file setting, including demo settings, origins, JWT profile, token
  lifetimes, providers, and model-status timeout.

### Database and Model Layout

**Applies to:** `backend/app/models/**`, `backend/app/db/**`,
`backend/alembic/**`.

**Base conventions:**

- SQLAlchemy 2.0 typed declarative mappings and Psycopg 3.
- UUID primary keys generated by the application.
- UTC-aware Python datetimes and PostgreSQL `timestamptz`.
- Explicitly named foreign keys, unique constraints, check constraints, and
  indexes.
- Closed role/status/scope values use text columns plus named CHECK constraints
  in the initial migration, not PostgreSQL enum types.
- Never use SQLite for integration/security tests.
- Never use runtime `create_all()` as the migration strategy.
- Alembic autogeneration may draft revisions, but every revision and generated
  SQL must be reviewed.
- Map Python attributes such as `event_metadata` to SQL column `metadata`
  because SQLAlchemy Declarative reserves `metadata`.

**Required relationships:**

```text
users
  1 -> many user_scopes
  1 -> many identities
  1 -> 0..1 local_credentials
  1 -> many refresh_token_families
  1 -> many conversations
  1 -> many tool_executions
  1 -> many nullable audit_logs/security_events

refresh_token_families
  many -> 1 user
  1 -> many refresh_tokens

refresh_tokens
  many -> 1 family
  0..1 -> parent refresh_token
  0..1 -> replacement refresh_token

conversations
  many -> 1 user
  1 -> many messages
```

**Required identity/session constraints:**

- `users.email_key` is unique.
- `user_scopes` has composite primary key `(user_id, scope)`.
- `identities` has unique `(issuer, subject)`.
- `local_credentials.user_id` is its primary key and user foreign key.
- `refresh_tokens.token_hash` and `refresh_tokens.jti` are unique.
- `refresh_tokens.parent_token_id` is nullable unique so one token has at most
  one child.
- Active-family, expiry, stable pagination, correlation, event-type, and status
  indexes follow Research Pattern 8.
- Foreign-key delete actions are explicit and migration-tested.

**Phase boundary:**

Conversation, message, tool-execution, audit-log, and security-event tables are
created to satisfy PLAT-03. Phase 1 does not expose chat/tool/admin behavior.

### Identity Provider Boundary

**Applies to:** `backend/app/identity/**`.

**Required internal contract:**

```python
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

**Constraints:**

- The local provider verifies normalized email/password and returns a stable
  local issuer plus a non-email subject.
- Account linking uses `(issuer, subject)`, never email as an external identity
  key.
- Local authentication is not described or exposed as an OAuth Authorization
  Server or OpenID Provider.
- Do not add discovery, authorization, token, ID-token, or UserInfo endpoints
  that imply OP conformance.
- A fake future OIDC provider must be able to satisfy the same protocol in a
  contract test without changing account-linking code.

### Registration

**Applies to:** auth schemas/routes, `registration.py`, password utilities,
user/identity/credential/scope repositories, and the registration UI.

**Data flow:**

```text
Browser registration form
  -> exact allowed Origin
  -> request schema containing only email + password
  -> email-validator normalization
  -> product email_key = normalized.casefold()
  -> NFC password normalization and policy validation
  -> Argon2id hash work
  -> transaction inserts user + local identity + credential + fixed scopes
  -> unique race is absorbed
  -> same generic 202 body for new and duplicate email
  -> UI renders the same registration-accepted state
```

**Constraints:**

- Clients cannot submit role, scopes, active state, or demo state.
- Every normal registration creates an active `user` with exactly:
  `chat:read`, `chat:write`, `tool:websearch`, `tool:python`.
- Normalize email consistently in register, login, seed, and bootstrap paths.
- Disable email deliverability DNS checks for the offline deterministic phase.
- Password policy: NFC, 15 to 128 Unicode code points, separate bounded UTF-8
  byte ceiling, spaces/printable Unicode allowed, no composition rule, and a
  bounded local common/context password blocklist.
- Hash before deciding whether the account already exists; catch the unique
  race and discard the duplicate hash.
- Do not return a user ID or duplicate indicator.
- Frontend confirmation is client-only and never sent to the API.

### Login and Access Tokens

**Applies to:** `local_provider.py`, `authentication.py`, `passwords.py`,
`access_tokens.py`, auth route/schema, and frontend auth client.

**Data flow:**

```text
Browser login form
  -> exact allowed Origin
  -> normalized email lookup
  -> real Argon2id verify or precomputed dummy-hash verify
  -> generic denial for unknown email, wrong password, inactive account,
     or invalid local identity state
  -> create one refresh family/token
  -> issue strict 10-minute access JWT
  -> set refresh and CSRF cookies
  -> frontend stores access token in memory only
  -> frontend calls /api/auth/me
  -> render only server-returned current-user fields
```

**Access JWT profile:**

```text
Header: alg=RS256, typ=at+jwt, kid=<configured active key id>
Claims: iss, aud, sub, role, scopes, iat, nbf, exp, jti
TTL: exp - iat <= 600 seconds
```

**Validation order:**

1. Inspect header only to select a preconfigured key.
2. Reject missing/unknown `kid`, unexpected `typ`, or non-RS256 `alg`.
3. Decode with PyJWT using `algorithms=["RS256"]`, exact issuer/audience,
   required claims, and 30-second leeway.
4. Enforce exact JSON/Python types, UUID formats, time ordering, lifetime,
   sorted unique known scopes, and a known role.
5. Reload current user and scopes.
6. Require active user and exact role/scope equality with current state.
7. Emit redacted evidence for signature-valid unknown role/scope/policy state.

The browser must not derive displayed role/scopes by decoding the JWT.

### Principal and Authorization Policy

**Applies to:** `authorization/principal.py`, `authorization/policy.py`, all
protected routes.

**Canonical pipeline:**

```text
Authorization header
  -> strict JWT validator
  -> typed AccessTokenClaims
  -> load current user + scopes by sub
  -> active/known/exact-state checks
  -> AuthenticatedPrincipal
  -> endpoint-specific policy
```

**Policy constraints:**

- Define closed role, scope, tool, provider-state, and policy-result enums or
  equivalent allowlists.
- Any unknown value maps to `DENY_UNKNOWN_STATE`.
- Missing, deleted, or inactive users are denied even if the JWT signature and
  timestamps are valid.
- FastAPI remains authoritative even when Kong later performs coarse checks.
- `/api/auth/me` returns only `id`, normalized `email`, `role`, sorted `scopes`,
  and `is_active`.

### Refresh Rotation, CSRF, and Logout

**Applies to:** refresh/session models, repositories, `sessions.py`,
`refresh_tokens.py`, `csrf.py`, auth routes, and frontend session utility.

**Session policy:**

- One family per successful login/device.
- Access token lifetime: 10 minutes.
- Refresh idle window: 7 days.
- Family absolute lifetime: 30 days.
- A child expires at the earlier of idle expiry and family absolute expiry.
- Logout revokes only the current family.
- Used token rows and lineage are retained for replay detection.

**Cookie contract:**

```text
__Host-simpagent_refresh
  Secure; HttpOnly; SameSite=Strict; Path=/; no Domain

__Host-simpagent_csrf
  Secure; SameSite=Strict; Path=/; no Domain; intentionally readable by JS
```

**Refresh token storage:**

- Generate 32 random bytes with `secrets.token_bytes(32)`.
- Store only `HMAC-SHA-256(refresh_key, raw_token)` as a fixed 32-byte digest.
- Keep the HMAC key outside PostgreSQL.

**CSRF contract:**

- Bind the CSRF HMAC to `family_id || nonce`.
- Require exact allowed `Origin`.
- Reject missing, `null`, suffix-matched, or untrusted same-site origins.
- Require matching CSRF cookie/header and constant-time HMAC comparison.
- Use explicit credentialed CORS origins, methods, and headers.
- Clear both cookies using matching attributes on refresh failure, replay, or
  successful logout.

**Transaction and lock pattern:**

```text
begin transaction
  lock refresh token FOR UPDATE
  lock family FOR UPDATE
  inspect committed token/family state
  rotate OR revoke family + append event OR return invalid outcome
commit transaction
map typed outcome to HTTP
```

- Lock token then family in the same order everywhere.
- Never share one `AsyncSession` across concurrent tasks.
- Never raise an HTTP exception inside the transaction after mutating replay
  state.
- A concurrent loser that observes the old token as used revokes the entire
  family and records the security event.
- The child issued by the winning request becomes unusable after family
  revocation.
- Frontend uses one shared in-memory refresh promise and retries the original
  request at most once.

### Health, Readiness, and Provider State

**Applies to:** `health.py`, `provider_status.py`, app lifespan, frontend
readiness client, and Compose health checks.

**Contracts:**

```json
GET /health -> 200 {"status":"alive"}
```

`/health` performs no database or provider calls.

```text
GET /ready -> 200 ready/degraded or 503 not_ready
components:
  database: ready|unavailable
  migrations: ready|out_of_date|unknown
  llm: ready|unconfigured|unavailable
  search: ready|unconfigured|model_unavailable|unavailable
  sandbox: foundation_ready|unavailable
```

**Rules:**

- Database or migration-head failure returns `503 not_ready`.
- Missing/unavailable external providers return sanitized `200 degraded` while
  core auth/storage remain ready.
- Provider status uses closed state/reason enums. Raw exceptions are never part
  of responses or logs.
- A bounded model existence check may call `google-genai` model metadata only.
  Phase 1 must not call generation or Google Search.
- `SEARCH_MODEL` is configuration-driven; do not hardcode
  `gemini-2.5-flash`.
- The frontend polls readiness every 60 seconds only while visible and fails
  closed on network errors or malformed unknown aggregate state.
- Degraded provider state does not disable account access. Core-not-ready does.

### Compose, Kong, and Sandbox Foundations

**Applies to:** `compose.yaml`, `kong/kong.yml`, `sandbox/**`, service
Dockerfiles.

**Startup graph:**

```text
postgres healthy
  -> migrate completes
  -> dev-init/seed-demo completes or safely no-ops
  -> backend healthy/ready
  -> kong and frontend healthy

sandbox foundation starts on its isolated control network and reports health
```

**Service boundaries:**

- PostgreSQL uses a named volume and no public host port.
- Migration is a one-shot app-image service running `alembic upgrade head`.
- Backend is on app/data networks and has no direct public application port.
- Kong is DB-less and exposes only approved application/health traffic.
- Kong Admin API ports are not host-exposed.
- Frontend uses the edge/app network.
- Sandbox has a health endpoint only, no execution API, no Docker socket, no
  host path, no privileged mode, and no access to application secrets.
- Phase 1 Kong configuration is minimal routing. Full JWT/rate-limit/security
  hardening remains Phase 5.

### Demo Seed and Production Bootstrap

**Applies to:** CLI modules, Compose one-shot services, development-only
frontend config.

**Demo seed constraints:**

- Mutation requires both `APP_ENV=development` and
  `DEMO_SEED_ENABLED=true`.
- Disabled seed exits successfully without mutation.
- Enabled seed outside development fails hard.
- Use a transaction advisory lock or deterministic locking to make repeated
  Compose starts safe.
- Upsert only the fixed demo User and Admin identities and exact scope bundles.
- Admin gets the four standard scopes plus `admin:read` and `admin:write`.
- Passwords are never printed or logged.
- Production bundles, HTML, RSC payloads, source maps, comments, and hidden
  elements must not contain demo credentials.

**Bootstrap constraints:**

- Runs only as an explicit operator CLI, never application startup.
- Uses interactive `getpass`; no password command-line argument.
- Acquires a transaction advisory lock.
- Fails without mutation if an Admin already exists.
- May promote an existing User or create one Admin.
- Sets `is_demo=false`, replaces scopes with the full Admin bundle, writes
  redacted evidence, and prints safe result data only.

### Frontend Account-Access Pattern

**Applies to:** `frontend/app/**`, account-access components, client/session
utilities.

**Component set:**

`AccountAccessShell`, `BrandLockup`, `PlatformStatus`, `SecuritySummary`,
`AuthCard`, `AuthModeSwitch`, `FormField`, `PasswordField`, `ActionButton`,
`InlineAlert`, `DemoAccountPanel`, `CurrentUserCard`, `StatusBadge`, and
`ScopeList`.

Do not create a generic dashboard shell, sidebar, table system, toast system,
modal framework, or chat placeholder.

**Single-route state machine:**

```text
checking_session
  -> anonymous_login
  -> anonymous_register
  -> registration_accepted
  -> authenticated
  -> session_expired
  -> core_not_ready
```

**Browser security constraints:**

- Access token lives in memory only.
- Never use `localStorage`, `sessionStorage`, IndexedDB, URLs, or readable
  bearer-token cookies.
- All auth/current-user requests use `cache: "no-store"`.
- Initial session restoration completes before rendering anonymous login.
- Protected requests share one refresh promise and retry once.
- `/me`, not decoded JWT data, is the only identity rendering source.
- Unknown role/scope in `/me` invalidates the client session.
- Passwords are cleared after server error, registration acceptance, mode
  switch, session expiry, or logout.
- Logout failure leaves the authenticated state visible and does not falsely
  claim server revocation.

**UI conventions:**

- Next.js 16 App Router, React 19, TypeScript 5.9, Tailwind CSS 4.
- Local semantic components; no third-party registry blocks.
- Light theme only, Be Vietnam Pro loaded with `next/font/local`.
- Use the exact spacing, typography, color, responsive, copy, focus, and
  accessibility contracts from `01-UI-SPEC.md`.
- User-visible Phase 1 copy is Vietnamese.
- Status is never communicated by color alone.
- Minimum target size is 44x44 px; input and primary button height is 48 px.
- Use inline alerts, not a toast dependency.
- Raw HTML and raw API/server diagnostics are never rendered.

### Testing Pattern

**Applies to:** all `backend/tests/**` and `compose.test.yaml`.

**Fixture boundaries:**

- `conftest.py`: app factory, settings, generated RSA keys, fixed clock, HTTPX
  client, and canary secrets.
- `tests/fixtures/postgres.py`: PostgreSQL 18, Alembic-to-head setup, async
  session factory, and deterministic cleanup.
- `tests/fixtures/auth.py`: user, login, token, cookie, Origin, and CSRF helpers.
- HTTP integration tests use application-created sessions and committed state.
  Do not hide test data in a transaction the application cannot observe.

**Required test layers:**

| Layer | Pattern |
|---|---|
| Unit | Settings invariants, normalization, password policy, JWT semantics, CSRF HMAC, closed enums |
| Repository integration | Constraints, migrations, row locks, refresh transitions on PostgreSQL 18 |
| API integration | Register/login/refresh/logout/me plus cookie and readiness contracts |
| Concurrency/security | Duplicate registration, parallel refresh, inactive principals, unknown signed claims |
| Smoke | Compose services, dependencies, health, private exposure, seed idempotency |
| Secret leakage | Canary values absent from responses, logs, events, and settings errors |

**Mandatory high-risk assertions:**

- Concurrent refresh proves family revocation and that the winning child cannot
  refresh afterward.
- Replay denial is followed by a new-session DB query proving revocation/event
  commit.
- Duplicate registration creates one account and returns indistinguishable
  response status/body.
- JWT corpus covers algorithm confusion, wrong key/type/issuer/audience,
  missing/invalid claims, unknown role/scope, and later-deactivated users.
- CSRF/Origin deny cases produce no state mutation.
- Provider exceptions containing canary secrets are reduced to safe reason
  codes.
- Migration tests inspect actual constraints, indexes, predicates, FK actions,
  downgrade/re-upgrade behavior, and `alembic check`.

Use the exact commands and paths in `01-VALIDATION.md`. Task-level checks target
under 30 seconds; full PostgreSQL/Compose checks run at wave and phase gates.

## Cross-Cutting Shared Patterns

### Fail Closed

Apply to every security-sensitive parser and state machine:

- Unknown role, scope, tool, provider state, policy result, readiness aggregate,
  or token claim type denies access.
- A permissive `else` branch is forbidden.
- Denial must have no forbidden database, provider, cookie, or UI side effect.

### Secret Handling

Apply to configuration, routes, logs, events, tests, CLI, UI, and Compose:

- Never log or return passwords, access tokens, refresh tokens, cookies, CSRF
  values, API keys, private keys, peppers, DSNs, or environment dumps.
- Never send secrets to model context or tools.
- Use canary-secret tests on both success and failure paths.
- Demo credentials are public development-only configuration, not production
  secrets, and must be absent from production artifacts.

### Transaction Boundaries

Apply to registration, login session creation, refresh, replay, logout, seed,
and bootstrap:

- One service owns each transaction.
- Repository functions do not independently commit.
- HTTP exceptions are mapped after transactional outcomes are durable.
- Lock ordering is stable.
- Security evidence required by a denial commits in the same transaction as
  the state change it documents.

### Stable Time and Randomness

- Inject a clock into token/session services for deterministic tests.
- Inject or wrap token/JTI generation where tests need deterministic assertions.
- Production randomness uses `secrets`; do not create custom PRNGs.
- Store all time values as UTC-aware timestamps.

### No Hand-Rolled Security Primitives

| Need | Required Mechanism |
|---|---|
| Password hashing | `pwdlib[argon2]` |
| JWT | `PyJWT[crypto]` with a fixed RS256 profile |
| Email normalization | `email-validator` |
| Random opaque tokens | `secrets.token_bytes(32)` |
| Digest/MAC comparison | `hmac.compare_digest` |
| Migration history | reviewed Alembic revisions |
| Refresh serialization | PostgreSQL transaction and `FOR UPDATE` |
| Secret delivery | Compose secret files and Pydantic settings sources |

## Planner Dependency Order

Plan tasks should preserve the research dependency order:

1. Repository, package, app factory, configuration, error, and test contracts.
2. PostgreSQL models, reviewed migrations, Compose networks/jobs, and health
   foundations.
3. Identity protocol, normalization, password policy, registration, and login.
4. Access JWT profile, principal reload, policy, `/me`, and fail-closed tests.
5. Refresh family rotation, CSRF/Origin, logout, browser single-flight refresh,
   and concurrency tests.
6. Development seed, production bootstrap, provider degradation, and the full
   approved account-access UI.
7. Fresh-volume assembled verification and secret-canary review.

The planner may parallelize frontend visual component work after API contracts
are fixed, but session behavior depends on the auth, cookie, `/me`, and
readiness response contracts.

## Phase Boundary Constraints

Phase 1 creates foundations but does not implement:

- Conversation or message API behavior.
- LLM chat generation.
- Google Search execution or grounding.
- Python code execution.
- Admin evidence APIs or admin UI.
- Production gateway hardening, distributed rate limiting, or Cloudflare.
- Password reset, email verification, MFA, external OIDC login, session
  management, logout-all, or remember-me.

The sandbox is health-only, Kong is minimal DB-less routing, provider checks
are metadata/status-only, and future-domain tables have no Phase 1 business
routes.

## No Analog Found

| Domain | Files/Groups | Reason |
|---|---|---|
| Platform | Compose, environment, Kong, sandbox | No platform/application files exist |
| Backend HTTP | app factory, auth routes, health routes, schemas | No FastAPI code exists |
| Persistence | models, repositories, sessions, migrations | No SQLAlchemy/Alembic code exists |
| Identity/security | provider, password, JWT, refresh, CSRF, policy | No security implementation exists |
| Frontend | page, components, auth/session/readiness clients | No Next.js/React code exists |
| CLI | demo seed, admin bootstrap, dev secret initialization | No CLI code exists |
| Tests | fixtures, unit, integration, security, smoke | No test code exists |

## Metadata

**Analog search scope:** Entire repository excluding `.git/**`.

**Repository files scanned:** 478 non-git files.

**Existing product source files:** 0.

**Canonical files read:**

- `AGENTS.md`
- `prompt.md`
- `.planning/PROJECT.md`
- `.planning/STATE.md`
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/phases/01-secure-platform-and-account-access/01-CONTEXT.md`
- `.planning/phases/01-secure-platform-and-account-access/01-RESEARCH.md`
- `.planning/phases/01-secure-platform-and-account-access/01-UI-SPEC.md`
- `.planning/phases/01-secure-platform-and-account-access/01-VALIDATION.md`

**Pattern extraction date:** 2026-06-08
