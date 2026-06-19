---
phase: 06
slug: adversarial-verification-and-vietnamese-delivery
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-19
updated: 2026-06-19
---

# Phase 06 - Validation Strategy

> Per-phase validation contract and final execution status.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Backend: `pytest`; Frontend: Node/`tsx --test`; Attack suite: repo-owned scripts under `security-tests/`; Docs review: Markdown plus live Compose verification |
| **Config file** | `backend/pyproject.toml`, `frontend/package.json`, `compose.yaml`, `compose.test.yaml` |
| **Quick run command** | `docker compose run --rm backend python -m pytest tests/integration/auth tests/integration/chat tests/integration/search tests/integration/python -q` |
| **Full suite command** | `powershell -ExecutionPolicy Bypass -File security-tests/run-phase6-matrix.ps1` plus `powershell -ExecutionPolicy Bypass -File security-tests/run-phase6-attacks.ps1` |
| **Estimated runtime** | ~2-5 minutes for the matrix plus ~2 minutes for the attack suite on a warm local stack |

---

## Sampling Rate

- After every task-sized change: run the narrowest touched backend/frontend test file or attack script.
- Before final verification: rebuild the main stack, rerun the full matrix, then rerun the full attack suite from repo root.
- Human UAT: complete a README-first navigation/truthfulness review after the executable evidence is green.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-V-01 | 06-01 | 1 | TEST-01 | T-06-01 | Auth lifecycle, refresh replay, invalid/expired token handling stay covered as a repeatable phase matrix | integration/security | `docker compose run --rm backend python -m pytest tests/integration/auth tests/security/test_jwt_profile.py -q` | yes | green |
| 06-V-02 | 06-01 | 1 | TEST-02 | T-06-02 | Two-user BOLA denial is proven across conversation/message read-write-delete paths | integration/security | `docker compose run --rm backend python -m pytest tests/integration/chat tests/security/test_chat_authorization.py -q` | yes | green |
| 06-V-03 | 06-01 | 1 | TEST-03 | T-06-03 | Role, scope, and tool denials stay enforced for admin, search, and Python surfaces | integration/security | `docker compose run --rm backend python -m pytest tests/integration/admin tests/integration/search/test_search_authz.py tests/integration/python/test_python_authorization.py -q` | yes | green |
| 06-V-04 | 06-01 | 1 | TEST-04 | T-06-04 | Chat conversation flow, ordering, idempotency, and provider-failure behavior remain green | integration/security | `docker compose run --rm backend python -m pytest tests/integration/chat tests/security/test_chat_idempotency.py tests/security/test_chat_provider_failure.py -q` | yes | green |
| 06-V-05 | 06-01 | 1 | TEST-05 | T-06-05 | Search grounding, timeout/failure states, and prompt-injection resistance remain covered | integration/security | `docker compose run --rm backend python -m pytest tests/integration/search tests/security/test_search_prompt_injection.py tests/security/test_search_guardrails.py -q` | yes | green |
| 06-V-06 | 06-01 | 1 | TEST-06 | T-06-06 | Sandbox timeout, network denial, output bounds, cleanup, and escape resistance remain covered | integration/security | `docker compose run --rm backend python -m pytest tests/integration/python tests/security -k python -q` | yes | green |
| 06-V-07 | 06-01 | 1 | TEST-09, TEST-10 | T-06-07 | Side-effect assertions and canary-secret non-leakage are explicit in the phase runner | security/smoke | `docker compose run --rm backend python -m pytest tests/security/test_secret_leakage.py tests/security/test_search_secret_leakage.py tests/smoke/test_logging_flow.py -q` | yes | green |
| 06-V-08 | 06-02 | 1 | TEST-07 | T-06-08 | Attack scripts prove brute force, token replay, BOLA, SSRF, prompt/tool abuse, and sandbox abuse denial against the live stack | black-box attack | `powershell -ExecutionPolicy Bypass -File security-tests/run-phase6-attacks.ps1` | yes | green |
| 06-V-09 | 06-03 | 2 | TEST-08 | T-06-09 | Repo contains practical Semgrep, dependency, image, Burp, AWVS, and DAST guidance plus a finding template | docs/tooling | `rg -n "Semgrep|Trivy|Bandit|pip-audit|Burp|AWVS|ZAP|finding template" docs security-tests README.md` | yes | green |
| 06-V-10 | 06-04 | 2 | DOCS-01, DOCS-02, DOCS-03 | T-06-10 | Vietnamese setup, architecture, and security docs match the implemented system and include Mermaid diagrams | docs/manual | `rg -n "```mermaid|JWT|OAuth|BOLA|sandbox|grounding|Cloudflare" README.md docs` | yes | green |
| 06-V-11 | 06-05 | 3 | DOCS-04, DOCS-05, DOCS-06 | T-06-11 | Vietnamese testing, runbook, limitations, and final verification docs are truthful and complete | docs/manual | `rg -n "Semgrep|Burp|AWVS|runbook|limitations|prototype|Windows|Docker|Google" docs .planning/phases/06-adversarial-verification-and-vietnamese-delivery` | yes | green |

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements

- [x] `security-tests/README.md` - evaluator attack-suite entrypoint
- [x] `security-tests/run-phase6-matrix.ps1` - repeatable verification matrix runner
- [x] `security-tests/run-phase6-attacks.ps1` - black-box attack orchestration entrypoint
- [x] `security-tests/` focused attack scripts for replay, BOLA, brute force, SSRF, prompt/tool abuse, and sandbox abuse
- [x] `docs/architecture.vi.md` - Vietnamese architecture and Mermaid diagrams
- [x] `docs/security.vi.md` - Vietnamese security-control explanation
- [x] `docs/testing.vi.md` - Vietnamese testing and scanner guide
- [x] `docs/runbook.vi.md` - Vietnamese incident and operations runbook
- [x] `docs/limitations.vi.md` - Vietnamese limitations and external-data-flow note
- [x] `.planning/phases/06-adversarial-verification-and-vietnamese-delivery/06-VERIFICATION.md` - final proof artifact

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Vietnamese docs can be followed without reading `.planning` | DOCS-01..06 | Evaluator usability and document flow are human judgments | Completed in `06-UAT.md`: README-first navigation passed |
| Live browser and public-route behavior matches the final evidence claims | TEST-07, DOCS-01 | Final evaluator flow still benefits from manual confirmation | Completed in `06-UAT.md`: live-stack behavior spot-check passed |
| Limitation statements do not overclaim production readiness or search-planning history | DOCS-06 | Truthfulness and claim discipline require human review | Completed in `06-UAT.md`: limitation/truthfulness review passed |

---

## Validation Sign-Off

- [x] All planned work items have automated verification or explicit manual review hooks
- [x] Sampling continuity: no 3 consecutive tasks without an automated verify path
- [x] Wave 0 artifacts now exist and were exercised in final verification
- [x] No watch-mode flags
- [x] `nyquist_compliant: true` retained after closeout

**Approval:** passed
