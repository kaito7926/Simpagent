---
phase: 05
slug: gateway-administration-and-security-evidence
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-15
---

# Phase 05 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Backend: `pytest` via `backend/pyproject.toml`; Frontend: Node/`tsx --test` via `frontend/package.json` |
| **Config file** | `backend/pyproject.toml` and `frontend/package.json` |
| **Quick run command** | `docker compose run --rm backend python -m pytest tests/unit/test_logging.py -q && npm --prefix frontend test -- frontend/tests/auth-session.test.ts` |
| **Full suite command** | `docker compose run --rm backend python -m pytest tests/integration/admin tests/integration/auth tests/integration/gateway tests/smoke -q && npm --prefix frontend test` |
| **Estimated runtime** | ~45 seconds for narrow checks once Wave 0 files exist |

---

## Sampling Rate

- **After every task commit:** Run the narrowest touched backend test module plus the smallest relevant frontend test file.
- **After every plan wave:** Run the full backend integration/smoke subset plus `npm --prefix frontend test` when frontend files changed.
- **Before `/gsd-verify-work`:** Full suite must be green against the assembled Compose topology.
- **Max feedback latency:** 45 seconds for narrow checks where practical.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-V-01 | TBD | 0 | IDEN-03 | T-05-01 | OAuth redirect start/callback/state handling stays backend-owned and rejects invalid state | integration | `docker compose run --rm backend python -m pytest tests/integration/auth/test_oauth_flows.py -q` | ❌ W0 | ⬜ pending |
| 05-V-02 | TBD | 0 | IDEN-06 | T-05-02 | Google provider enable/disable behavior follows backend configuration without breaking local login | integration | `docker compose run --rm backend python -m pytest tests/integration/auth/test_google_oauth.py -q` | ❌ W0 | ⬜ pending |
| 05-V-03 | TBD | 0 | IDEN-07 | T-05-03 | GitHub provider enable/disable behavior follows backend configuration without breaking local login | integration | `docker compose run --rm backend python -m pytest tests/integration/auth/test_github_oauth.py -q` | ❌ W0 | ⬜ pending |
| 05-V-04 | TBD | 0 | IDEN-08 | T-05-04 | Missing, unverified, or conflicting provider email fails closed and cannot take over local accounts | integration | `docker compose run --rm backend python -m pytest tests/integration/auth/test_oauth_account_linking.py -q` | ❌ W0 | ⬜ pending |
| 05-V-05 | TBD | 0 | GATE-02 | T-05-05 | Kong enforces exact CORS origins, methods, and headers including browser preflight handling | integration | `docker compose run --rm backend python -m pytest tests/integration/gateway/test_cors.py -q` | ❌ W0 | ⬜ pending |
| 05-V-06 | TBD | 0 | GATE-03 | T-05-06 | Kong applies tighter rate limits to auth/tool routes and returns useful `429` metadata | integration | `docker compose run --rm backend python -m pytest tests/integration/gateway/test_rate_limits.py -q` | ❌ W0 | ⬜ pending |
| 05-V-07 | TBD | 0 | GATE-04, OBS-01 | T-05-07 | Kong request-size limits and correlation propagation are enforced end-to-end | integration | `docker compose run --rm backend python -m pytest tests/integration/gateway/test_request_size_and_correlation.py -q` | ❌ W0 | ⬜ pending |
| 05-V-08 | TBD | 0 | AUTHZ-02, OBS-05, OBS-06 | T-05-08 | Admin read/write surfaces remain role-and-scope protected with denial evidence | integration | `docker compose run --rm backend python -m pytest tests/integration/admin/test_admin_evidence.py -q && docker compose run --rm backend python -m pytest tests/integration/admin/test_admin_write.py -q` | ✅ partial | ⬜ pending |
| 05-V-09 | TBD | 0 | OBS-02, OBS-03 | T-05-09 | Structured evidence and admin snippets recursively redact secrets and sensitive payloads | unit/integration | `docker compose run --rm backend python -m pytest tests/unit/test_logging.py -q && docker compose run --rm backend python -m pytest tests/security/test_secret_leakage.py -q` | ✅ partial | ⬜ pending |
| 05-V-10 | TBD | 0 | OBS-04, OBS-07 | T-05-10 | Tool execution summaries and admin metrics stay bounded, correlated, and content-safe | integration | `docker compose run --rm backend python -m pytest tests/smoke/test_admin_flow.py -q` | ✅ partial | ⬜ pending |
| 05-V-11 | TBD | 0 | PRODREADY-01, PRODREADY-02 | T-05-11 | Production profile settings enforce secure cookies, public URLs, trusted proxy handling, and env-only secrets | unit/integration | `docker compose run --rm backend python -m pytest tests/unit/test_config.py -q && docker compose run --rm backend python -m pytest tests/integration/gateway/test_production_profile.py -q` | ❌ W0 | ⬜ pending |
| 05-V-12 | TBD | 0 | PRODREADY-04 | T-05-12 | Assembled stack smoke checks cover local login, OAuth, gateway routing, admin evidence, chat, Search, and Python | smoke | `docker compose run --rm backend python -m pytest tests/smoke -q` | ✅ partial | ⬜ pending |
| 05-V-13 | TBD | 0 | IDEN-06, IDEN-07, OBS-05 | T-05-13 | Frontend auth shell and admin pages render configured providers, real evidence data, and explicit forbidden states | frontend | `npm --prefix frontend test -- frontend/tests/account-access-oauth.test.tsx frontend/tests/admin-evidence.test.tsx` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/integration/auth/test_oauth_flows.py` — redirect/callback/state coverage for both providers
- [ ] `backend/tests/integration/auth/test_google_oauth.py` — Google provider capability and sign-in coverage
- [ ] `backend/tests/integration/auth/test_github_oauth.py` — GitHub provider capability and sign-in coverage
- [ ] `backend/tests/integration/auth/test_oauth_account_linking.py` — verified match, missing email, conflicting identity, and auto-provision coverage
- [ ] `backend/tests/integration/gateway/test_cors.py` — strict CORS and browser preflight coverage through Kong
- [ ] `backend/tests/integration/gateway/test_rate_limits.py` — route-specific `429` behavior and rate-limit headers
- [ ] `backend/tests/integration/gateway/test_request_size_and_correlation.py` — oversized-body rejection plus correlation propagation/validation
- [ ] `backend/tests/integration/gateway/test_production_profile.py` — trusted proxy, secure-cookie, and public-URL profile checks
- [ ] `backend/tests/smoke/test_oauth_google_flow.py` — full-stack Google login smoke coverage
- [ ] `backend/tests/smoke/test_oauth_github_flow.py` — full-stack GitHub login smoke coverage
- [ ] `frontend/tests/account-access-oauth.test.tsx` — configured/disabled provider button behavior
- [ ] `frontend/tests/admin-evidence.test.tsx` — real admin data wiring, drawers, and forbidden-state rendering

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Google and GitHub login feel trustworthy and land in the same protected session experience as local login | IDEN-03, IDEN-06, IDEN-07 | Final provider redirects, browser cookies, and UI trust cues need human review | Run the stack, sign in with local, Google, and GitHub accounts, confirm each lands in the same authenticated workspace and that logout/refresh behavior matches local login |
| Gateway evidence page truthfully distinguishes Kong-only denials from backend-stored events | GATE-03, GATE-04, OBS-03, OBS-05 | Human review is needed to verify wording and avoid implying fabricated FastAPI rows | Trigger gateway-only `429` or oversized-body denials, inspect the admin gateway evidence page, and confirm copy references Kong/config or verification evidence rather than stored backend rows |
| Small-production documentation accurately describes Cloudflare, limits, and operational runbooks without overclaiming | GATE-07, GATE-08, PRODREADY-03, PRODREADY-05 | Requires document review against implemented topology and stated prototype limits | Review deployment and operations docs after implementation, verify Cloudflare is optional, trusted-proxy assumptions are explicit, and capacity/security claims stay within the 100-users/month prototype scope |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify steps or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all missing OAuth, gateway, and admin-evidence verification files
- [ ] No watch-mode flags
- [ ] Feedback latency < 45 seconds for narrow checks where practical
- [ ] `nyquist_compliant: true` set in frontmatter after task coverage is confirmed

**Approval:** pending
