---
phase: 01
slug: secure-platform-and-account-access
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| PLAT-01 | T-01 | Required Compose command builds and reaches documented terminal states | smoke | `docker compose up --build --wait` | No - W0 | pending |
| PLAT-02 | T-01 | Required services, jobs, dependencies, health checks, and networks are present | smoke/schema | `docker compose config -q && docker compose run --rm backend pytest -q tests/smoke/test_topology.py` | No - W0 | pending |
| PLAT-03 | T-02 | Fresh PostgreSQL upgrades to Alembic head with expected tables, constraints, and indexes | integration | `docker compose run --rm backend pytest -q tests/integration/db/test_migrations.py` | No - W0 | pending |
| PLAT-04 | T-03 | Settings reject unsafe production values and redact secret-bearing failures | unit | `docker compose run --rm backend pytest -q tests/unit/test_config.py` | No - W0 | pending |
| PLAT-05 | T-01 | Liveness is process-only; readiness detects DB and migration failures safely | integration | `docker compose run --rm backend pytest -q tests/integration/test_health.py` | No - W0 | pending |
| PLAT-06 | T-03 | Missing or unavailable providers produce sanitized fail-closed/degraded states | integration | `docker compose run --rm backend pytest -q tests/integration/test_provider_status.py` | No - W0 | pending |
| AUTH-01 | T-04 | Registration normalizes email, fixes role/scopes, and resists duplicate races/enumeration | integration/concurrency | `docker compose run --rm backend pytest -q tests/integration/auth/test_registration.py` | No - W0 | pending |
| AUTH-02 | T-05 | Valid login issues strict access credentials and protected refresh/CSRF cookies | integration | `docker compose run --rm backend pytest -q tests/integration/auth/test_login.py` | No - W0 | pending |
| AUTH-03 | T-03 | Argon2id hashes are stored; plaintext and canary secrets never leak | security | `docker compose run --rm backend pytest -q tests/security/test_secret_leakage.py -k password` | No - W0 | pending |
| AUTH-04 | T-05 | JWT parser accepts only the explicit token profile and required claims | security | `docker compose run --rm backend pytest -q tests/security/test_jwt_profile.py` | No - W0 | pending |
| AUTH-05 | T-06 | Opaque refresh hashes rotate atomically with family lineage | integration | `docker compose run --rm backend pytest -q tests/integration/auth/test_refresh_rotation.py` | No - W0 | pending |
| AUTH-06 | T-06 | Reuse and concurrent refresh revoke the family, deny requests, and persist an event | concurrency/security | `docker compose run --rm backend pytest -q tests/security/test_refresh_replay.py` | No - W0 | pending |
| AUTH-07 | T-06 | Logout revokes the current family, clears cookies, and is idempotent | integration | `docker compose run --rm backend pytest -q tests/integration/auth/test_logout.py` | No - W0 | pending |
| AUTH-08 | T-03 | `/me` returns safe identity fields without credential material | integration | `docker compose run --rm backend pytest -q tests/integration/auth/test_me.py` | No - W0 | pending |
| AUTH-09 | T-07 | Cookie flags, exact Origin, and CSRF checks deny invalid requests without mutation | security | `docker compose run --rm backend pytest -q tests/security/test_browser_session.py` | No - W0 | pending |
| AUTH-10 | T-08 | Local identity adapter honors the provider contract without exposing OP endpoints | contract | `docker compose run --rm backend pytest -q tests/unit/identity/test_provider_contract.py` | No - W0 | pending |
| AUTHZ-01 | T-09 | Missing, inactive, or deleted principals fail closed after token issuance | security | `docker compose run --rm backend pytest -q tests/security/test_principal_fail_closed.py` | No - W0 | pending |
| AUTHZ-08 | T-09 | Unknown signed roles, scopes, tools, and policy states deny and emit redacted evidence | security | `docker compose run --rm backend pytest -q tests/security/test_unknown_policy_state.py` | No - W0 | pending |

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

- [ ] `backend/pyproject.toml` - runtime/test dependencies, pytest configuration, asyncio mode, and markers.
- [ ] `backend/tests/conftest.py` - app, settings, key, fixed-clock, client, and canary fixtures.
- [ ] `backend/tests/fixtures/postgres.py` - migrated PostgreSQL session and deterministic cleanup.
- [ ] `backend/tests/fixtures/auth.py` - user, login, cookie, CSRF, and token helpers.
- [ ] `backend/tests/unit/test_config.py` - PLAT-04.
- [ ] `backend/tests/integration/db/test_migrations.py` - PLAT-03.
- [ ] `backend/tests/integration/test_health.py` - PLAT-05 and PLAT-06.
- [ ] `backend/tests/integration/test_provider_status.py` - PLAT-06.
- [ ] `backend/tests/integration/auth/` - AUTH-01 through AUTH-09 lifecycle modules.
- [ ] `backend/tests/security/test_jwt_profile.py` - AUTH-04 and AUTHZ-08.
- [ ] `backend/tests/security/test_refresh_replay.py` - AUTH-05 and AUTH-06.
- [ ] `backend/tests/security/test_browser_session.py` - AUTH-09.
- [ ] `backend/tests/security/test_secret_leakage.py` - project secret policy.
- [ ] `backend/tests/unit/identity/test_provider_contract.py` - AUTH-10.
- [ ] `backend/tests/security/test_principal_fail_closed.py` - AUTHZ-01.
- [ ] `backend/tests/security/test_unknown_policy_state.py` - AUTHZ-08.
- [ ] `backend/tests/smoke/test_topology.py` - PLAT-01 and PLAT-02.
- [ ] `compose.test.yaml` - isolated PostgreSQL test topology.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Development demo credentials are understandable to an evaluator | D-04, D-05 | Documentation clarity is partly human-facing | Start development Compose, follow only documented credentials, confirm User/Admin identities and that production mode refuses automatic seeding |
| Health/readiness output is useful without leaking internals | PLAT-05, PLAT-06 | Operator usefulness and disclosure balance require review | Inspect healthy, database-down, migration-pending, and provider-unavailable responses and logs |

---

## Validation Sign-Off

- [ ] All plan tasks have an automated verification command or an explicit Wave 0 dependency.
- [ ] No three consecutive implementation tasks lack automated verification.
- [ ] Wave 0 creates every missing fixture and test path referenced above.
- [ ] No watch-mode flags appear in verification commands.
- [ ] Task-level feedback latency remains below 30 seconds where practical.
- [ ] PostgreSQL-backed integration tests and fresh-volume Compose smoke tests are green.
- [ ] Secret-canary, concurrent replay, duplicate registration, JWT, and CSRF suites are green.
- [ ] Set `nyquist_compliant: true` and `wave_0_complete: true` after the planner assigns tasks and Wave 0 is implemented.

**Approval:** pending
