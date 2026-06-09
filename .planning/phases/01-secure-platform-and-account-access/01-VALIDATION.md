---
phase: 01
slug: secure-platform-and-account-access
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-08
---

# Phase 01 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest `>=9,<10`, pytest-asyncio `>=1.4,<2`, HTTPX `>=0.28,<1` |
| **Config file** | `backend/pyproject.toml` - Wave 0 creates |
| **Quick run command** | `docker compose run --rm backend pytest -q tests/unit -x` |
| **Auth integration command** | `docker compose run --rm backend pytest -q tests/integration/auth -x` |
| **Security quick command** | `docker compose run --rm backend pytest -q tests/security/test_refresh_replay.py -x` |
| **Full suite command** | `docker compose run --rm backend pytest -q` |
| **Compose smoke command** | `docker compose up --build --wait && docker compose run --rm backend pytest -q tests/smoke` |
| **Estimated quick runtime** | Under 30 seconds after test infrastructure exists |

All database integration and security tests use PostgreSQL 18, not SQLite. Tests apply Alembic to head and clean data through deterministic truncation or isolated schemas so application-created sessions observe the same committed state.

---

## Sampling Rate

- **After every task commit:** Run the narrowest relevant unit or integration module, targeting under 30 seconds.
- **After every plan wave:** Run `docker compose run --rm backend pytest -q tests/unit tests/integration`.
- **After JWT, refresh, or authorization changes:** Also run the JWT profile, refresh replay, browser-session, and fail-closed principal tests.
- **Before `$gsd-verify-work`:** Start a fresh-volume Compose topology, run the full backend suite and smoke suite, and run the secret-canary scan.
- **Max feedback latency:** 30 seconds for task-level checks; full topology checks run at wave and phase gates.

---

## Per-Task Verification Map

Task IDs and plan assignments are finalized by the planner. Every requirement below must appear in at least one plan task with the listed automated command or a stricter equivalent.

| Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| PLAT-01 | T-01 | Required Compose command builds and reaches documented terminal states | smoke | `docker compose up --build --wait` | Yes | passed |
| PLAT-02 | T-01 | Required services, jobs, dependencies, health checks, and networks are present | smoke/schema | `docker compose config -q && docker compose run --rm backend pytest -q tests/smoke/test_topology.py` | Yes | passed |
| PLAT-03 | T-02 | Fresh PostgreSQL upgrades to Alembic head with expected tables, constraints, and indexes | integration | `docker compose run --rm backend pytest -q tests/integration/db/test_migrations.py` | Yes | passed |
| PLAT-04 | T-03 | Settings reject unsafe production values and redact secret-bearing failures | unit | `docker compose run --rm backend pytest -q tests/unit/test_config.py` | Yes | passed |
| PLAT-05 | T-01 | Liveness is process-only; readiness detects DB and migration failures safely | integration | `docker compose run --rm backend pytest -q tests/integration/test_health.py` | Yes | passed |
| PLAT-06 | T-03 | Missing or unavailable providers produce sanitized fail-closed/degraded states | integration | `docker compose run --rm backend pytest -q tests/integration/test_provider_status.py` | Yes | passed |
| AUTH-01 | T-04 | Registration normalizes email, fixes role/scopes, and resists duplicate races/enumeration | integration/concurrency | `docker compose run --rm backend pytest -q tests/integration/auth/test_registration.py` | Yes | passed |
| AUTH-02 | T-05 | Valid login issues strict access credentials and protected refresh/CSRF cookies | integration | `docker compose run --rm backend pytest -q tests/integration/auth/test_login.py` | Yes | passed |
| AUTH-03 | T-03 | Argon2id hashes are stored; plaintext and canary secrets never leak | security | `docker compose run --rm backend pytest -q tests/security/test_secret_leakage.py` | Yes | passed |
| AUTH-04 | T-05 | JWT parser accepts only the explicit token profile and required claims | security | `docker compose run --rm backend pytest -q tests/security/test_jwt_profile.py` | Yes | passed |
| AUTH-05 | T-06 | Opaque refresh hashes rotate atomically with family lineage | integration | `docker compose run --rm backend pytest -q` | Partially - covered by full suite | passed |
| AUTH-06 | T-06 | Reuse and concurrent refresh revoke the family, deny requests, and persist an event | concurrency/security | `docker compose run --rm backend pytest -q` | Partially - covered by full suite | passed |
| AUTH-07 | T-06 | Logout revokes the current family, clears cookies, and is idempotent | integration | `docker compose run --rm backend pytest -q` | Partially - covered by full suite | passed |
| AUTH-08 | T-03 | `/me` returns safe identity fields without credential material | integration | `docker compose run --rm backend pytest -q tests/integration/auth/test_me.py` | Yes | passed |
| AUTH-09 | T-07 | Cookie flags, exact Origin, and CSRF checks deny invalid requests without mutation | security | `docker compose run --rm backend pytest -q && docker compose run --rm frontend npm run test -- tests/auth-session.test.ts tests/readiness.test.ts` | Partially - backend + frontend lifecycle coverage | passed |
| AUTH-10 | T-08 | Local identity adapter honors the provider contract without exposing OP endpoints | contract | `docker compose run --rm backend pytest -q tests/unit/identity/test_provider_contract.py` | Yes | passed |
| AUTHZ-01 | T-09 | Missing, inactive, or deleted principals fail closed after token issuance | security | `docker compose run --rm backend pytest -q tests/security/test_principal_fail_closed.py` | Yes | passed |
| AUTHZ-08 | T-09 | Unknown signed roles, scopes, tools, and policy states deny and emit redacted evidence | security | `docker compose run --rm backend pytest -q tests/security/test_unknown_policy_state.py` | Yes | passed |

---

## Critical Security Scenarios

1. **Concurrent refresh barrier:** two independent clients submit the same refresh token simultaneously; exactly one may rotate, replay revokes the family, and the child cannot refresh.
2. **Replay commit:** a denied replay response still leaves the family revocation and security event committed and visible from a new database session.
3. **Duplicate registration race:** normalized-equivalent emails create one User with the fixed standard scope bundle and no Admin role while returning non-enumerating responses.
4. **JWT corpus:** reject `none`, algorithm confusion, wrong key/type/issuer/audience, missing claims, invalid NumericDates/UUIDs, excessive lifetime, unknown role/scope, and tokens for subsequently inactive accounts.
5. **CSRF matrix:** reject missing, malformed, cross-site, or mismatched Origin/cookie/header/HMAC combinations with zero session mutation.
6. **Provider redaction:** provider errors containing API keys, DSNs, credentials, and canary values expose only safe reason codes and correlation IDs.
7. **Seed/bootstrap:** development seeding is idempotent and production-blocked; production Admin bootstrap succeeds once without printing or logging a password.
8. **Migration fidelity:** empty database upgrade, schema/index inspection, disposable downgrade/re-upgrade, and `alembic check` all succeed.

---

## Wave 0 Requirements

Every missing path has an execution owner. Within each listed plan, the named
test task runs RED before the implementation task that satisfies it.

| Wave 0 path | Owner | Created before behavior |
|-------------|-------|-------------------------|
| `backend/pyproject.toml` | 01-01 Task 1 | All backend tests and implementation |
| `backend/tests/conftest.py` | 01-01 Task 1 | All API/unit/security tests |
| `backend/tests/fixtures/postgres.py` | 01-01 Task 1 | All PostgreSQL integration/security behavior |
| `backend/tests/fixtures/auth.py` | 01-01 Task 1 | All account/session behavior |
| `backend/tests/unit/test_config.py` | 01-07 Task 1 | 01-07 Task 2 configuration invariants |
| `backend/tests/integration/db/test_migrations.py` | 01-07 Task 1 | 01-07 Task 2 complete schema revision |
| `backend/tests/integration/test_health.py` | 01-07 Task 1 | 01-07 Task 3 readiness implementation |
| `backend/tests/integration/test_provider_status.py` | 01-07 Task 1 | 01-07 Task 3 provider-state implementation |
| `backend/tests/integration/auth/test_registration.py` | 01-02 Task 1 | 01-02 Tasks 2-3 registration |
| `backend/tests/integration/auth/test_login.py` | 01-02 Task 1 | 01-02 Tasks 2-3 login |
| `backend/tests/integration/auth/test_me.py` | 01-02 Task 1 | 01-02 Task 3 current identity |
| `backend/tests/integration/auth/test_refresh_rotation.py` | 01-05 Task 1 | 01-05 Task 2 refresh rotation |
| `backend/tests/integration/auth/test_logout.py` | 01-05 Task 1 | 01-05 Task 2 logout |
| `backend/tests/security/test_jwt_profile.py` | 01-04 Task 1 | 01-04 Task 3 strict JWT profile |
| `backend/tests/security/test_refresh_replay.py` | 01-05 Task 1 | 01-05 Task 2 replay handling |
| `backend/tests/security/test_browser_session.py` | 01-05 Task 1 | 01-05 Task 2 Origin/CSRF handling |
| `backend/tests/security/test_secret_leakage.py` | 01-01 Task 3 | Plans 01-02, 01-04, 01-05, 01-07, and 01-08 secret-bearing paths |
| `backend/tests/unit/identity/test_provider_contract.py` | 01-04 Task 1 | 01-04 Task 2 provider boundary |
| `backend/tests/security/test_principal_fail_closed.py` | 01-04 Task 1 | 01-04 Task 3 principal resolution |
| `backend/tests/security/test_unknown_policy_state.py` | 01-04 Task 1 | 01-04 Task 3 unknown-state handling |
| `backend/tests/smoke/test_topology.py` | 01-08 Task 1 | 01-08 Tasks 2-3 assembled topology |
| `compose.test.yaml` | 01-01 Task 1 | Every PostgreSQL-backed test plan |

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Development demo credentials are understandable to an evaluator | D-04, D-05 | Documentation clarity is partly human-facing | Start development Compose, follow only documented credentials, confirm User/Admin identities and that production mode refuses automatic seeding |
| Health/readiness output is useful without leaking internals | PLAT-05, PLAT-06 | Operator usefulness and disclosure balance require review | Inspect healthy, database-down, migration-pending, and provider-unavailable responses and logs |

---

## Validation Sign-Off

- [x] All plan tasks have an automated verification command or an explicit Wave 0 dependency.
- [x] No three consecutive implementation tasks lack automated verification.
- [x] Wave 0 owners above create every missing fixture and test path before its implementation task.
- [x] No watch-mode flags appear in verification commands.
- [x] Task-level feedback latency remains below 30 seconds where practical.
- [x] PostgreSQL-backed integration tests and fresh-volume Compose smoke tests are green.
- [x] Secret-canary, concurrent replay, duplicate registration, JWT, and CSRF suites are green.
- [x] Set `nyquist_compliant: true` and `wave_0_complete: true` after the planner assigns tasks and Wave 0 is implemented.

**Approval:** approved 2026-06-10
