---
phase: 04
slug: isolated-python-execution
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-12
---

# Phase 04 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest `>=9,<10`, pytest-asyncio `>=1.4,<2`, HTTPX `>=0.28,<1`, plus existing frontend typecheck/build checks |
| **Config file** | `backend/pyproject.toml` and `frontend/package.json` |
| **Quick run command** | `docker compose run --rm backend pytest -q tests/security -k python -x` |
| **Full suite command** | `docker compose run --rm backend pytest -q tests/integration tests/security && docker compose run --rm frontend npm run typecheck` |
| **Estimated runtime** | ~30 seconds for narrow backend checks once fixtures exist |

---

## Sampling Rate

- **After every task commit:** Run the narrowest relevant backend test module or frontend typecheck.
- **After every plan wave:** Run the full backend integration/security subset plus frontend typecheck when UI files changed.
- **Before `$gsd-verify-work`:** The full phase suite must be green against the assembled Compose topology.
- **Max feedback latency:** 30 seconds for narrow checks where practical.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | SBOX-01 | T-04-01 | Backend never directly evaluates user Python and only writes typed execution intent/state | security | `docker compose run --rm backend pytest -q tests/security/test_python_backend_boundary.py -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | SBOX-07 | T-04-02 | Result envelope and artifact metadata stay bounded, typed, and distinguish completed user-code exceptions from infrastructure failure | unit/integration | `docker compose run --rm backend pytest -q tests/integration/python/test_execution_contracts.py -x` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 1 | CHAT-12 | T-04-03 | Python result states are distinguishable from normal assistant/Search states at the contract level | unit | `docker compose run --rm backend pytest -q tests/unit/python/test_result_envelope.py -x` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 2 | SBOX-03 | T-04-04 | Runtime has no network and cannot reach internal or metadata addresses | security | `docker compose run --rm backend pytest -q tests/security/test_python_network_denial.py -x` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 2 | SBOX-04 | T-04-05 | Runtime is non-root, read-only-root, dropped-capability, no-new-privileges, seccomp-enforced | security | `docker compose run --rm backend pytest -q tests/security/test_python_runtime_profile.py -x` | ❌ W0 | ⬜ pending |
| 04-02-03 | 02 | 2 | SBOX-08 | T-04-06 | Package installation and arbitrary commands are denied | security | `docker compose run --rm backend pytest -q tests/security/test_python_policy_denials.py -x` | ❌ W0 | ⬜ pending |
| 04-03-01 | 03 | 3 | SBOX-02 | T-04-07 | Backend issues only reviewed profiles and capability-bound internal execution requests, defaulting to `python-basic-v1` unless a narrow backend rule allows `python-data-v1` | integration | `docker compose run --rm backend pytest -q tests/integration/python/test_python_authorization.py -x` | ❌ W0 | ⬜ pending |
| 04-03-02 | 03 | 3 | SBOX-05 | T-04-08 | Exact terminating limit is persisted and returned | integration | `docker compose run --rm backend pytest -q tests/integration/python/test_python_limits.py -x` | ❌ W0 | ⬜ pending |
| 04-03-03 | 03 | 3 | SBOX-06 | T-04-09 | Execution requests cannot smuggle secrets, mounts, Docker authority, or caller-controlled runtime options | security | `docker compose run --rm backend pytest -q tests/security/test_python_request_hardening.py -x` | ❌ W0 | ⬜ pending |
| 04-04-01 | 04 | 3 | CHAT-12 | T-04-10 | Frontend renders dedicated Python, denied, and limit-reached cards distinctly | frontend | `docker compose run --rm frontend npm run typecheck` | ❌ W0 | ⬜ pending |
| 04-04-02 | 04 | 3 | SBOX-07 | T-04-11 | Artifact links and bounded detail disclosure use approved state labels only | frontend/unit | `docker compose run --rm frontend npm run test -- python-result-card` | ❌ W0 | ⬜ pending |
| 04-05-01 | 05 | 4 | SBOX-07 | T-04-12 | Temporary runtime data, expired session snapshots, and expired artifact payloads are removed on the approved sliding-expiry path | integration/security | `docker compose run --rm backend pytest -q tests/security/test_python_cleanup.py -x` | ❌ W0 | ⬜ pending |
| 04-05-02 | 05 | 4 | CHAT-12, SBOX-01..08 | T-04-13 | Assembled topology proves denied, success, user-code exception, limit, artifact-expiry, and cleanup paths through the real stack | smoke | `docker compose up --build --wait && docker compose run --rm backend pytest -q tests/integration/python tests/security -k python` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/integration/python/test_execution_contracts.py` - typed backend result/artifact contract coverage
- [ ] `backend/tests/integration/python/test_python_authorization.py` - scope, policy, and profile-selection coverage
- [ ] `backend/tests/integration/python/test_python_limits.py` - exact limit-reporting coverage
- [ ] `backend/tests/security/test_python_backend_boundary.py` - prove backend never executes user code directly
- [ ] `backend/tests/security/test_python_network_denial.py` - deny outbound/internal network access
- [ ] `backend/tests/security/test_python_runtime_profile.py` - prove runtime isolation flags
- [ ] `backend/tests/security/test_python_policy_denials.py` - blocked imports, package install, command denial
- [ ] `backend/tests/security/test_python_request_hardening.py` - reject caller-controlled runtime mutation
- [ ] `backend/tests/security/test_python_cleanup.py` - prove temporary data cleanup
- [ ] `frontend/tests/python-result-card.test.tsx` or equivalent - Python-card rendering contract

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Python card clearly differs from direct chat and Search in the live UI | CHAT-12 | Final visual distinction is partly experiential | Open a conversation, trigger a successful Python run, a permission denial, and a limit termination; confirm each state is visually distinct |
| Approved artifact download flow is understandable and bounded | SBOX-07 | Reviewer must judge whether artifact actions are clear without exposing unsafe affordances | Produce `csv` and `png` outputs, inspect card labels and actions, and confirm no unsupported artifact appears |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all missing Python/security/frontend references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s for narrow checks where practical
- [ ] `nyquist_compliant: true` set in frontmatter after task coverage is confirmed

**Approval:** pending
