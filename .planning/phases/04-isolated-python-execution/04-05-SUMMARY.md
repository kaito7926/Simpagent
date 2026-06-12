---
phase: 04-isolated-python-execution
plan: "05"
subsystem: assembled-verification
tags: [python, smoke, cleanup, sandbox, compose]
requires:
  - phase: 04-isolated-python-execution
    provides: trusted supervisor and reviewed runtime profiles
  - phase: 04-isolated-python-execution
    provides: chat coordinator with policy-gated Python execution
  - phase: 04-isolated-python-execution
    provides: dedicated Python chat surfaces
provides:
  - assembled-stack Python success, limit, and denial smoke coverage
  - cleanup and side-effect regression tests
  - supervisor portability fixes for the real Docker topology
  - final verification evidence for Phase 4
affects: [04-VERIFICATION, compose-topology, sandbox-runtime]
tech-stack:
  added: [docker-sdk-shim, runtime-result-log-marker, smoke-safe-db-fixture]
  patterns: [assembled-smoke-first, deny-without-side-effects, cleanup-on-access]
key-files:
  created:
    - .planning/phases/04-isolated-python-execution/04-05-SUMMARY.md
    - backend/tests/integration/python/test_python_full_flow.py
    - backend/tests/security/test_python_cleanup.py
    - backend/tests/security/test_python_side_effects.py
    - backend/tests/smoke/test_python_tool_flow.py
    - sandbox/docker_shim.py
  modified:
    - backend/app/agent/decisions.py
    - backend/app/db/repositories/python_state.py
    - backend/app/services/python_sessions.py
    - backend/tests/fixtures/postgres.py
    - backend/tests/security/test_python_runtime_profile.py
    - sandbox/Dockerfile
    - sandbox/server.py
    - sandbox/runtime/runner.py
    - sandbox/seccomp/python-restricted.json
key-decisions:
  - "Kept the 15-minute sliding session model but moved cleanup onto access paths so expired payloads are purged even without a background worker."
  - "Skipped test-database truncation for smoke-marked tests so assembled topology checks do not destroy seeded dev accounts."
  - "Added a Docker SDK-backed shim inside the sandbox image because this Debian runtime did not provide a usable `docker` CLI binary."
  - "Stopped forcing `seccomp=default` because Docker already applies its default seccomp profile when no override is present, and the explicit flag broke worker startup in the real stack."
  - "Emitted the runtime result envelope through a single log marker because `/workspace` is tmpfs and `result.json` disappears after the worker exits."
patterns-established:
  - "Phase-closing smoke now proves success, limit-reached, and denied paths through Kong against the real Compose topology."
  - "Cleanup is verified as behavior: expired artifact payloads are deleted, session-state rows are pruned, and expired downloads return `410 Gone`."
  - "Deny and timeout paths are tested for absence of hidden supervisor or runtime side effects, not only for user-visible wording."
requirements-completed: [CHAT-12, SBOX-01, SBOX-02, SBOX-03, SBOX-04, SBOX-05, SBOX-06, SBOX-07, SBOX-08]
completed: 2026-06-13T02:36:41.0263978+07:00
---

# Phase 4: Plan 05 Summary

**Phase 4 now closes with real assembled-topology evidence: the public chat path can produce successful Python results, exact limit-reached states, and explicit denial states, while cleanup and no-side-effect guarantees are enforced by tests instead of assumptions.**

## Accomplishments

- Added the missing end-to-end suites for full-flow execution, cleanup, side effects, and public-topology smoke:
  - `backend/tests/integration/python/test_python_full_flow.py`
  - `backend/tests/security/test_python_cleanup.py`
  - `backend/tests/security/test_python_side_effects.py`
  - `backend/tests/smoke/test_python_tool_flow.py`
- Closed the cleanup gap by teaching the Python session repository/service to delete expired artifact payloads and session-state rows on normal access paths while still retaining expired artifact records long enough to return `410 Gone`.
- Fixed the planner initialization bug in `backend/app/agent/decisions.py` so embedded fenced Python does not fail in real Compose topology when the optional LLM secret is absent.
- Made smoke tests safe for the assembled stack by skipping the autouse test-database truncation fixture for `@pytest.mark.smoke`, which had been wiping the seeded demo accounts before login.
- Hardened the real supervisor path for the actual Docker topology:
  - added `sandbox/docker_shim.py` plus a `docker` Python SDK dependency because the sandbox image had no usable `docker` binary
  - removed the broken explicit `seccomp=default` override and now inherit Docker's default seccomp profile
  - switched runtime result extraction to a log marker emitted by `sandbox/runtime/runner.py`, because the worker workspace is tmpfs and disappears on exit

## Decisions Made

- Cleanup remains lazy and request-driven. The backend does not need a separate sweeper to delete expired payload files or expired session snapshots.
- Expired artifact downloads still return `410 Gone` because only the file payload is deleted on expiry; the owner-scoped database record is intentionally retained.
- The assembled smoke logs in with the seeded demo account so the final Python path is isolated from separate account-registration concerns.
- The trusted supervisor keeps `no-new-privileges`, dropped capabilities, non-root execution, read-only rootfs, and network isolation, but it now relies on Docker's implicit default seccomp behavior instead of a non-portable explicit flag.

## Verification

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

## Next Readiness

- Phase 4 is ready for final verification sign-off.
- The remaining follow-up is operational rather than functional: if a developer locally edits `sandbox/runtime/` after the runtime image has already been built, they should verify against a fresh stack or rebuild the runtime image before trusting old local containers.

---
*Phase: 04-isolated-python-execution*
*Completed: 2026-06-13*
