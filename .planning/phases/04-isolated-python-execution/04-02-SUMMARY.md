---
phase: 04-isolated-python-execution
plan: "02"
subsystem: sandbox
tags: [sandbox, docker, supervisor, runtime, seccomp]
requires:
  - phase: 04-isolated-python-execution
    provides: typed Python execution DTO contract
provides:
  - trusted sandbox supervisor HTTP surface
  - fixed reviewed runtime profiles and launch spec builder
  - isolated runtime image with reviewed package and artifact helpers
  - security tests for network denial, runtime profile, and blocked package/command behavior
affects: [04-03, sandbox-runtime, compose-topology, security-verification]
tech-stack:
  added: [python-stdlib-http, docker-cli, isolated-runtime-image]
  patterns: [trusted-supervisor, fresh-runtime-container, fixed-profile-launch-spec]
key-files:
  created:
    - sandbox/runtime/Dockerfile
    - sandbox/runtime/runner.py
    - sandbox/runtime/sitecustomize.py
    - sandbox/runtime/allowed_artifacts.py
    - sandbox/seccomp/python-restricted.json
    - backend/tests/security/test_python_network_denial.py
    - backend/tests/security/test_python_runtime_profile.py
    - backend/tests/security/test_python_policy_denials.py
  modified:
    - sandbox/Dockerfile
    - sandbox/server.py
    - compose.yaml
    - compose.test.yaml
key-decisions:
  - "Kept the sandbox control plane private and internal-only, with no published host port and fixed reviewed profiles only."
  - "Used a trusted supervisor that can prepare or build the runtime image and launch fresh containers with network=none, read-only rootfs, dropped capabilities, and no-new-privileges."
  - "Encoded reviewed artifacts inside the internal result envelope so the runtime container can be removed immediately without retaining temporary workspace files."
  - "Mounted sandbox source into backend test containers so security suites can inspect the reviewed runtime boundary without widening FastAPI authority."
patterns-established:
  - "Supervisor inputs are strict and reject unknown request fields."
  - "Runtime execution policy is reviewed through a launch-spec builder rather than caller-controlled Docker options."
  - "Runner pre-validates imports and dangerous calls, then enforces bounded stdout/stderr and reviewed artifact collection."
requirements-completed: [SBOX-03, SBOX-04, SBOX-08]
completed: 2026-06-12T04:34:15.5675853+07:00
---

# Phase 4: Plan 02 Summary

**The sandbox boundary now has a real trusted supervisor, a separate runtime image, fixed reviewed profiles, and security tests that inspect launch policy and runtime denials instead of relying on text-only refusals.**

## Accomplishments

- Replaced the health-only sandbox server with a supervisor in `sandbox/server.py` that validates a capability-bound execution request, owns two fixed reviewed profiles, prepares a Docker launch spec, and cleans up ephemeral runtime containers.
- Added a separate runtime image under `sandbox/runtime/` with a reviewed prebuilt package set, runtime policy hooks, bounded stdout/stderr handling, and reviewed artifact collection for `csv`, `json`, `txt`, and `png`.
- Added `backend/tests/security/test_python_network_denial.py`, `test_python_runtime_profile.py`, and `test_python_policy_denials.py` so the isolation contract now has focused RED/greenable test coverage.
- Updated `compose.yaml` and `compose.test.yaml` so the backend test path can inspect sandbox assets and the sandbox service owns the only Docker socket mount in the topology.

## Verification

- `python -m compileall sandbox backend/tests/security` passed.
- Direct local import and sanity checks for `sandbox/server.py` and `sandbox/runtime/runner.py` passed.
- A local runner smoke check proved one successful reviewed artifact path and one blocked-import policy path without Docker.
- `docker compose config -q` passed.
- `git diff --check` passed.

## Blockers and Gaps

- `docker build -f sandbox/Dockerfile sandbox` and runtime-launch verification were **not run** because the Docker client in this session still cannot connect to `dockerDesktopLinuxEngine`.
- `python -m pytest ...` for the new backend security tests was **not run** on the host because this machine does not currently have `pytest` installed for the available Python interpreter.
- The reviewed seccomp asset is staged and the supervisor enforces Docker's default seccomp profile today; tightening to a fully custom seccomp file may still need host-runtime-specific follow-up during end-to-end verification.

## Next Readiness

- `04-03` can now integrate a backend capability-signing helper and internal Python client against a concrete supervisor request/response shape.
- Once Docker daemon access and pytest are available, the immediate follow-up commands are:
  - `docker build -f sandbox/Dockerfile sandbox`
  - `docker build -f sandbox/runtime/Dockerfile sandbox/runtime`
  - `docker compose run --rm backend pytest -q tests/security/test_python_network_denial.py tests/security/test_python_runtime_profile.py tests/security/test_python_policy_denials.py`

---
*Phase: 04-isolated-python-execution*
*Completed: 2026-06-12*
