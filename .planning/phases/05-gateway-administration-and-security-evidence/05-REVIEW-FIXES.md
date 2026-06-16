---
phase: 05-gateway-administration-and-security-evidence
review_follow_up: 2026-06-16
source_review: 05-REVIEW.md
status: critical_fixes_applied
---

# Phase 05 Review Fixes

Post-review fixes applied after `05-REVIEW.md`:

- `CR-01`: Kong now routes `/api/auth/oauth` to the backend OAuth router, matching frontend and FastAPI paths.
- `CR-02`: OAuth state cookies now use explicit `SameSite=lax` for provider callback navigation while normal session cookies keep the configured policy.
- `CR-03`: FastAPI and Kong CORS allow `PATCH` for browser admin mutations.
- `CR-04`: Compose no longer bind-mounts `/var/run/docker.sock` into the sandbox service. The local stack now fails closed instead of granting the request-facing sandbox container control over the host Docker daemon.
- `WR-01`: Compose no longer passes the literal `sandbox-dev-secret`; `init-dev-secrets` now creates `python_capability_secret`, and backend/sandbox read it through secret files.
- `WR-02`: Added focused regression coverage for OAuth gateway routing, PATCH CORS, OAuth state SameSite behavior, dev secret generation, and the no-host-Docker-socket Compose boundary.

Verification run:

- `py -3.13 -m pytest tests/unit/test_oauth_state_cookie.py tests/integration/gateway/test_cors.py tests/integration/gateway/test_production_profile.py::test_compose_exposes_small_production_profile_and_proxy_environment tests/integration/gateway/test_production_profile.py::test_compose_sandbox_boundary_uses_secret_file_and_no_host_docker_socket tests/integration/cli/test_provisioning.py::test_init_dev_secrets_creates_expected_files tests/security/test_jwt_profile.py tests/unit/test_admin_evidence_service.py tests/security/test_python_runtime_profile.py tests/security/test_python_side_effects.py::test_supervisor_timeout_kills_and_removes_runtime_container tests/security/test_python_side_effects.py::test_supervisor_prefers_runtime_result_marker_from_logs -q`
  - Result: 31 passed, 1 skipped.
- `docker compose config -q`
  - Result: passed.

Residual risk:

- The sandbox supervisor no longer receives host Docker daemon access from Compose. Full Python execution through a socket-free runtime worker should be handled by a dedicated sandbox architecture phase if Python execution availability must be restored without weakening the isolation boundary.
