---
phase: 04-isolated-python-execution
verified: 2026-06-13T02:36:41.0263978+07:00
status: passed
score: 5/5 end-to-end truths verified
---

# Phase 4: Isolated Python Execution Verification Report

**Phase Goal:** Authorized users can run bounded Python and receive useful results without granting code access to the backend, host, application network, secrets, or runtime policy.
**Verified:** 2026-06-13T02:36:41.0263978+07:00
**Status:** passed

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Authorized users can request Python through the chat workflow and distinguish successful, denied, and limit-triggered Python outcomes. | VERIFIED | The assembled public-topology smoke passed through Kong in `tests/smoke/test_python_tool_flow.py`, proving success, output-limit, and Search-required denial states. Frontend verification also passed: `npm run typecheck`, `npm run test -- tests/python-result-card.test.tsx`, and `npm run build`. |
| 2 | Submitted code executes only behind the fixed sandbox boundary and never through backend `exec`, shelling, or host-process evaluation. | VERIFIED | `docker compose ... pytest -q tests/integration/python tests/security -k python` passed with `31 passed`, including `test_python_backend_boundary.py`, the orchestration suites, and the full-flow integration path. |
| 3 | Sandbox execution remains non-root, read-only, capability-dropped, `no-new-privileges`, network-isolated, and bounded by backend-owned reviewed profiles. | VERIFIED | The same `31 passed` gate includes `test_python_runtime_profile.py` and `test_python_network_denial.py`. The real Compose smoke also exercised the supervisor and runtime path after the final portability fixes. |
| 4 | Users receive bounded stdout/stderr, exact limit classification, approved artifacts, and a clear distinction between user-code exceptions, policy denials, and infrastructure failures. | VERIFIED | `tests/integration/python/test_python_full_flow.py`, `tests/integration/python/test_python_limits.py`, the planner regression, and `tests/python-result-card.test.tsx` all passed. The public smoke proved a real succeeded run and a real `limit_reached` response. |
| 5 | Temporary execution state is cleaned up and forbidden network, command, package, and side-effect behavior is denied without hidden supervisor/runtime side effects. | VERIFIED | The final security gate passed with `test_python_cleanup.py`, `test_python_policy_denials.py`, `test_python_request_hardening.py`, and `test_python_side_effects.py`. Expired artifact payload deletion plus `410 Gone` semantics are covered by the cleanup and full-flow suites. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/agent/` | Backend-owned Python planning, policy, and orchestration | EXISTS + VERIFIED | Coordinator, planner, and policy gates are exercised by integration, security, and planner regression tests. |
| `backend/app/api/routes/chat.py` | Chat route that can emit typed Python tool results | EXISTS + VERIFIED | Public smoke and integration tests create conversations and receive Python result envelopes through the normal chat workflow. |
| `backend/app/api/routes/python.py` | Owner-scoped artifact download surface | EXISTS + VERIFIED | Full-flow and cleanup tests cover approved artifact download behavior and expired-download `410 Gone`. |
| `backend/app/services/python_sessions.py` and `backend/app/db/repositories/python_state.py` | Sliding session retention and cleanup | EXISTS + VERIFIED | Cleanup tests prove expired payload deletion and expired session-state pruning on access. |
| `backend/app/tools/python_client.py` and `backend/app/security/tool_capabilities.py` | Capability-bound supervisor client | EXISTS + VERIFIED | Integration and security suites cover request signing, profile ownership, and retry boundaries. |
| `sandbox/server.py` | Trusted supervisor | EXISTS + VERIFIED | The assembled smoke and the security gate both pass through the real supervisor/runtime boundary. |
| `sandbox/runtime/` | Reviewed runtime image and runner | EXISTS + VERIFIED | Runtime build, user-code execution, policy denial, and bounded result transport are covered by integration/security tests and real smoke. |
| `sandbox/docker_shim.py` | Docker-compatible control path for the sandbox container | EXISTS + VERIFIED | Real assembled smoke now succeeds in the Docker topology that previously failed with missing `docker` CLI support. |
| `sandbox/seccomp/` | Reviewed seccomp policy asset | EXISTS + VERIFIED | Runtime profile tests verify the fixed seccomp policy family and the supervisor's non-overridable hardening posture. |
| `frontend/components/chat/` and `frontend/lib/chat/tool-results.ts` | Dedicated Python result rendering surfaces | EXISTS + VERIFIED | Renderer tests passed and the production build completed successfully. |
| `backend/tests/integration/python/`, `backend/tests/security/*python*`, `backend/tests/unit/python/test_python_planner.py`, `backend/tests/smoke/test_python_tool_flow.py` | End-to-end behavioral proof | EXISTS + VERIFIED | Current-session Docker runs covered integration, security, planner, and public smoke gates. |

**Artifacts:** 11/11 verified

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| Chat route | Python coordinator | normal conversation create/message flow | WIRED | Public smoke proves Python selection and typed result persistence through `/api/conversations`. |
| Coordinator | Supervisor client | capability-bound internal execution call | WIRED | Integration and security suites cover backend-owned profile selection, request shaping, and retry boundaries. |
| Supervisor | Runtime worker | reviewed profile launch and bounded result transport | WIRED | Runtime profile, side-effect, cleanup, and smoke tests now pass through the real worker-launch path. |
| Runtime result | Backend persistence | `ToolExecution`, session state, and approved artifacts | WIRED | Full-flow and cleanup tests verify persisted evidence, session snapshots, approved artifact storage, and expired-download behavior. |
| Backend result envelope | Frontend presenter/cards | typed `python_result` metadata to dedicated UI surfaces | WIRED | `tests/python-result-card.test.tsx`, `npm run typecheck`, and `npm run build` all passed. |
| Compose topology | Public feature path | `docker compose up --build --wait` plus smoke | WIRED | The assembled stack reached healthy state and the real public Python smoke passed end-to-end. |

**Wiring:** 6/6 connections verified

## Requirements Coverage

| Requirement | Status | Blocking Issue |
|-------------|--------|----------------|
| CHAT-12 | SATISFIED | - |
| SBOX-01 | SATISFIED | - |
| SBOX-02 | SATISFIED | - |
| SBOX-03 | SATISFIED | - |
| SBOX-04 | SATISFIED | - |
| SBOX-05 | SATISFIED | - |
| SBOX-06 | SATISFIED | - |
| SBOX-07 | SATISFIED | - |
| SBOX-08 | SATISFIED | - |

**Coverage:** 9/9 requirements satisfied

## Decision Coverage

All locked Phase 4 decisions from the context and plan summaries are now represented either directly in shipped code or in the final documented implementation deviations from Plan 05:

- The 15-minute sliding session window is active and verified by cleanup tests.
- Profile selection remains backend-owned and narrow.
- Denial, limit, policy, and infrastructure states remain distinct in both backend envelopes and frontend presentation.
- The supervisor keeps the reviewed isolation posture while using two final implementation details proven by assembled verification:
  - Docker's implicit default seccomp profile is inherited instead of forcing `seccomp=default`.
  - Runtime results are transported through a supervisor log marker because the worker workspace is tmpfs.

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| - | - | None blocking found in Phase 4 verification scope | - | - |

**Anti-patterns:** 0 found

## Human Verification Required

None. The current-session automated backend, frontend, smoke, Compose, and hygiene gates cover the Phase 4 acceptance surface.

## Gaps Summary

**No functional gaps found.** Phase 4 goals are achieved.

Operational note only: when a developer locally edits `sandbox/runtime/` after the runtime image has already been built, they should verify against a fresh stack or rebuild the runtime image before trusting stale local containers.

## Verification Metadata

**Verification approach:** Goal-backward using the Phase 4 roadmap goal, the Phase 4 plan chain, and final assembled smoke
**Phase summaries present:** `04-01-SUMMARY.md`, `04-02-SUMMARY.md`, `04-03-SUMMARY.md`, `04-04-SUMMARY.md`, `04-05-SUMMARY.md`
**Automated checks:**
- `docker compose --project-name simpagentp405full --project-directory X:\ -f X:\compose.test.yaml run --rm --build backend-test pytest -q tests/integration/python tests/security -k python` -> `31 passed, 22 deselected`
- `docker compose --project-name simpagentp405b --project-directory X:\ -f X:\compose.test.yaml run --rm --build backend-test pytest -q tests/integration/python/test_python_full_flow.py tests/security/test_python_cleanup.py tests/security/test_python_side_effects.py tests/security/test_python_runtime_profile.py tests/unit/python/test_python_planner.py tests/smoke/test_python_tool_flow.py` -> `12 passed, 1 skipped`
- `docker compose --project-name simpagentsmokedbg2 --project-directory X:\ -f X:\compose.yaml up --build --wait -d` -> passed
- `docker compose --project-name simpagentsmokedbg2 --project-directory X:\ -f X:\compose.yaml run --rm --no-deps -e SIMPAGENT_RUN_SMOKE=true backend pytest -q tests/smoke/test_python_tool_flow.py` -> `1 passed`
- `docker compose --project-name simpagentsmokedbg2 --project-directory X:\ -f X:\compose.yaml run --rm frontend npm run typecheck` -> passed
- `docker compose --project-name simpagentsmokedbg2 --project-directory X:\ -f X:\compose.yaml run --rm frontend npm run test -- tests/python-result-card.test.tsx` -> `7 passed`
- `docker compose --project-name simpagentsmokedbg2 --project-directory X:\ -f X:\compose.yaml run --rm frontend npm run build` -> passed
- `git diff --check` -> passed
- `python -m compileall backend/app backend/tests sandbox` -> passed
- `docker compose --project-name simpagentcfg --project-directory X:\ -f X:\compose.yaml config -q` -> passed
**Human checks required:** 0

---
*Verified: 2026-06-13T02:36:41.0263978+07:00*
*Verifier: Codex*
