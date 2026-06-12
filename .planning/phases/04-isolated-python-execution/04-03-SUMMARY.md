---
phase: 04-isolated-python-execution
plan: "03"
subsystem: backend-orchestration
tags: [python, coordinator, policy, sandbox, artifacts]
requires:
  - phase: 04-isolated-python-execution
    provides: typed Python execution DTO contract
  - phase: 04-isolated-python-execution
    provides: trusted supervisor and reviewed runtime profiles
provides:
  - chat coordinator with policy-gated Python execution
  - backend capability signing and internal supervisor client
  - conversation-scoped sliding Python session retention and artifact download route
  - integration/security tests for authorization, exact limit reporting, and request hardening
affects: [04-04, 04-05, chat-backend, sandbox-contract]
tech-stack:
  added: [fastapi-route, coordinator-layer, httpx-internal-client, owner-scoped-artifact-storage]
  patterns: [lazy-tool-selection, capability-bound-supervisor-call, sliding-session-expiry]
key-files:
  created:
    - backend/app/agent/coordinator.py
    - backend/app/agent/decisions.py
    - backend/app/agent/policy.py
    - backend/app/api/routes/python.py
    - backend/app/security/tool_capabilities.py
    - backend/app/services/python_sessions.py
    - backend/app/tools/python_client.py
    - backend/tests/integration/python/test_python_authorization.py
    - backend/tests/integration/python/test_python_limits.py
    - backend/tests/security/test_python_request_hardening.py
  modified:
    - backend/app/api/routes/chat.py
    - backend/app/core/config.py
    - backend/app/db/repositories/python_state.py
    - backend/app/main.py
    - backend/app/services/chat.py
    - backend/tests/conftest.py
    - compose.yaml
    - compose.test.yaml
    - sandbox/server.py
    - sandbox/runtime/runner.py
key-decisions:
  - "Kept chat natural-language-first by adding backend coordinator heuristics instead of exposing a Python mode toggle."
  - "Left profile choice fully backend-owned: default `python-basic-v1`, elevate narrowly to `python-data-v1`, and ignore planner suggestions."
  - "Implemented the 15-minute sliding session window by storing opaque conversation-scoped snapshots plus extending active artifact expiry only after accepted executions."
  - "Extended the private backend-to-sandbox contract with signed `state_snapshot_b64` so session continuity works without widening the public API."
patterns-established:
  - "Routes stay thin and now delegate turn execution to a coordinator that can return either direct-chat metadata or a typed Python result envelope."
  - "The backend persists denied/running/terminal Python execution evidence in `ToolExecution` while keeping user-code exceptions on the normal Python result path."
  - "Approved artifact downloads are owner-scoped, API-relative, and return `410 Gone` after expiry."
requirements-completed: [CHAT-12, SBOX-02, SBOX-05, SBOX-06, SBOX-07]
completed: 2026-06-12T12:30:00+07:00
---

# Phase 4: Plan 03 Summary

**The backend chat flow can now choose bounded Python from a normal prompt, sign and call the trusted supervisor, retain conversation-scoped Python state on a 15-minute sliding window, and serve approved artifacts through an owner-scoped download route.**

## Accomplishments

- Added `backend/app/agent/coordinator.py`, `decisions.py`, and `policy.py` so chat turns now flow through backend-owned tool policy instead of calling the LLM adapter directly.
- Added `backend/app/security/tool_capabilities.py` and `backend/app/tools/python_client.py` to sign one-shot Python capabilities, call the supervisor through a strict internal request envelope, and retry exactly once for worker-start failures.
- Added `backend/app/services/python_sessions.py` plus a repository expiry helper so conversation-scoped state snapshots and approved artifacts share the locked 15-minute sliding inactivity window.
- Added `backend/app/api/routes/python.py` and wired it in `backend/app/main.py` for owner-scoped artifact downloads with `410 Gone` on expiry.
- Updated `sandbox/server.py` and `sandbox/runtime/runner.py` so the private supervisor/runtime contract can carry a signed opaque state snapshot and restore it inside each fresh container.
- Added RED-first backend tests for missing permission, Search-plus-Python denial, backend-owned profile selection, exact limit persistence, expired artifact download behavior, and request hardening.

## Decisions Made

- Denied Python turns now persist a `ToolExecution` row and complete the assistant message with a bounded `python_result` envelope instead of surfacing a generic route error.
- Profile elevation remains narrow and heuristic-driven; planner suggestions are ignored so model output cannot choose runtime policy.
- Session continuity is implemented as an opaque snapshot that the backend stores but does not deserialize beyond safe binding-name metadata, keeping untrusted object restoration inside the sandbox.
- Expired artifacts keep their owner-scoped database records long enough to return `410 Gone`, while the file payload is deleted on the first expired download attempt.

## Verification

- `python -m compileall backend/app backend/tests sandbox` passed.
- `git diff --check` passed.
- `docker compose config -q` passed.
- A lightweight local import smoke for the new Python-client surface could **not** complete because the host Python environment is missing `httpx`.
- The plan's pytest commands were **not run** because this host Python does not currently provide `pytest`, and Docker-backed backend tests were **not run** because the Docker daemon is still unavailable in this session.

## Next Readiness

- Phase `04-04` can now wire real `metadata.python_result` envelopes into the existing Next.js Python presenter without changing the backend shape again.
- Phase `04-05` can build cleanup automation on top of the new artifact/session expiry semantics and the sandbox snapshot contract.
- Once Docker and backend test dependencies are available, the immediate follow-up commands are:
  - `docker compose run --rm backend pytest -q tests/integration/python/test_python_authorization.py tests/integration/python/test_python_limits.py tests/security/test_python_request_hardening.py`
  - `docker compose run --rm backend pytest -q tests/integration/python tests/security -k python`

---
*Phase: 04-isolated-python-execution*
*Completed: 2026-06-12*
