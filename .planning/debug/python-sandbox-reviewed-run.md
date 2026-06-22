---
status: resolved
trigger: "Ở bản deploy docker hiện tại: Khi tôi prompt: Calculate the sum from 1 to 3636, Simpagent Response: The Python execution service could not complete the reviewed run. Trước đó agent python sandbox vẫn chạy tốt và tính ra kết quả."
created: 2026-06-17
updated: 2026-06-17T14:07:06+07:00
---

## Symptoms

- Expected behavior: Chat agent dùng Python sandbox tính tổng từ 1 đến 3636 và trả kết quả.
- Actual behavior: Chat trả `The Python execution service could not complete the reviewed run.`
- Error messages: User-facing error text above; backend/runtime stack trace chưa xác định.
- Timeline: Lỗi xuất hiện trong bản deploy Docker hiện tại; trước đó Python sandbox vẫn chạy tốt.
- Reproduction: Gửi prompt `Calculate the sum from 1 to 3636` trong UI/chat deployment Docker.

## Current Focus

- hypothesis: Root cause confirmed: the current Docker deploy removed the trusted sandbox supervisor's Docker control channel, so `/execute` returned HTTP 500 while trying to inspect/build the runtime worker image.
- test: Rebuild sandbox with Docker control access, make health fail closed when Docker control is unavailable, then run direct reviewed Python execution for `sum(range(1, 3637))`.
- expecting: Sandbox health reports Docker control ready and `/execute` returns `succeeded` with stdout `6612066`.
- next_action: resolved; user can retry the chat prompt.

## Evidence

- timestamp: 2026-06-17T14:07:06+07:00
  checked: `rg` for user-facing error copy
  found: The UI-visible response is produced by `backend/app/tools/python_client.py` when the supervisor returns a non-200 response or transport failure.
  implication: The message is a backend wrapper for sandbox infrastructure failure, not the Python runtime's normal calculation output.

- timestamp: 2026-06-17T14:07:06+07:00
  checked: backend container logs
  found: Recent Python executions called `POST http://sandbox:8080/execute` and received `HTTP/1.0 500 Internal Server Error` with correlation IDs including `2cc13abc-21fc-44aa-9794-96eb2e9650c1` and `99906e9c-2d0d-4000-ae4a-442a20d33a9c`.
  implication: The request reached the sandbox supervisor; the failure was inside the supervisor layer.

- timestamp: 2026-06-17T14:07:06+07:00
  checked: sandbox runtime state before fix
  found: `/var/run/docker.sock` was absent in `simpagent-sandbox-1`, `docker_socket_present` was `false`, and Docker SDK calls failed with `FileNotFoundError`.
  implication: The trusted supervisor could not create the isolated Docker worker required to run user Python.

- timestamp: 2026-06-17T14:07:06+07:00
  checked: direct `/execute` call with valid capability before fix
  found: Sandbox returned HTTP 500 with `supervisor_failure` while running `docker build -f /sandbox/runtime/Dockerfile -t simpagent-python-runtime:local /sandbox/runtime`.
  implication: Missing Docker control access was sufficient to reproduce the exact failure without UI or LLM involvement.

- timestamp: 2026-06-17T14:07:06+07:00
  checked: git history for `compose.yaml`
  found: Earlier compose revisions mounted `/var/run/docker.sock:/var/run/docker.sock`; commit `cc1a86d` removed it while hardening gateway/sandbox boundary checks.
  implication: This is a regression from recent compose hardening: the runtime architecture still expects a Docker control channel.

- timestamp: 2026-06-17T14:07:06+07:00
  checked: direct `/execute` call after fix
  found: Sandbox health reports `docker_socket_present: true` and `docker_control_ready: true`; direct execution returned HTTP 200, status `succeeded`, stdout `6612066`.
  implication: Python sandbox execution is restored for the reported calculation path.

## Eliminated

- hypothesis: The Python planner generated incorrect code for the sum prompt.
  evidence: Direct execution of `print(sum(range(1, 3637)))` failed before fix with the same supervisor infrastructure failure and succeeded after Docker control access was restored.
  timestamp: 2026-06-17T14:07:06+07:00

- hypothesis: The CRLF shebang issue in `/usr/local/bin/docker` is still the current blocker.
  evidence: `docker --version` inside `simpagent-sandbox-1` returned `Docker shim via Python SDK`; the later failure was Docker daemon connectivity, not script execution.
  timestamp: 2026-06-17T14:07:06+07:00

## Resolution
root_cause: "The current Docker deployment removed `/var/run/docker.sock` from the trusted sandbox supervisor service, but `sandbox/server.py` still launches isolated runtime workers through Docker. Without a Docker daemon endpoint, `/execute` failed with HTTP 500 and the backend wrapped that as `The Python execution service could not complete the reviewed run.`"
fix: "Restored the Docker control mount for the trusted sandbox supervisor in `compose.yaml`, added `docker version` support to the Python Docker shim, and made sandbox health report `runtime_unavailable` instead of passing when Docker control is unavailable."
verification: "Rebuilt/recreated `simpagent-sandbox-1`; health now reports `foundation_ready`, `docker_socket_present: true`, and `docker_control_ready: true`. Direct `/execute` for `print(sum(range(1, 3637)))` returned HTTP 200, status `succeeded`, stdout `6612066`. Targeted tests passed: `test_compose_sandbox_boundary_uses_secret_file_and_trusted_runtime_control`; `test_python_runtime_profile.py`; `test_supervisor_prefers_runtime_result_marker_from_logs`."
files_changed:
  - "D:\\ADMIN\\Documents\\matmahoc\\@DO_AN\\Simpagent\\compose.yaml"
  - "D:\\ADMIN\\Documents\\matmahoc\\@DO_AN\\Simpagent\\sandbox\\docker_shim.py"
  - "D:\\ADMIN\\Documents\\matmahoc\\@DO_AN\\Simpagent\\sandbox\\server.py"
  - "D:\\ADMIN\\Documents\\matmahoc\\@DO_AN\\Simpagent\\backend\\tests\\integration\\gateway\\test_production_profile.py"
