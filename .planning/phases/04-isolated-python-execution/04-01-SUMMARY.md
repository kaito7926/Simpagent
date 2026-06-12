---
phase: 04-isolated-python-execution
plan: "01"
subsystem: database
tags: [python, sandbox, alembic, pydantic, postgres]
requires:
  - phase: 01-secure-platform-and-account-access
    provides: users, conversations, tool_executions, repository/test foundations
provides:
  - typed Python execution DTO contract
  - bounded Python session-state and artifact persistence
  - backend trust-boundary tests for forbidden in-process execution
affects: [04-02, 04-03, 04-04, python-runtime, chat-tooling]
tech-stack:
  added: [pydantic-models, sqlalchemy-models, alembic]
  patterns: [shared-python-contract-module, bounded-artifact-metadata, owner-scoped-python-state-repository]
key-files:
  created:
    - backend/app/python_contract.py
    - backend/app/schemas/python.py
    - backend/app/models/python_state.py
    - backend/app/db/repositories/python_state.py
    - backend/alembic/versions/0003_python_execution_contracts.py
    - backend/tests/unit/python/test_result_envelope.py
    - backend/tests/integration/python/test_execution_contracts.py
    - backend/tests/security/test_python_backend_boundary.py
  modified:
    - backend/app/models/domain.py
    - backend/app/models/__init__.py
    - backend/app/db/repositories/__init__.py
    - backend/tests/integration/db/test_migrations.py
key-decisions:
  - "Moved shared Python enums and limits into app/python_contract.py so persistence code does not depend on API schema packages."
  - "Extended ToolExecution status constraints with policy_error, limit_reached, and infra_failure so later Python flows can persist exact audit states."
  - "Stored conversation-scoped Python state as a bounded opaque blob plus explicit expiry, and stored reviewed artifacts as metadata records with safe names and backend-owned storage keys."
patterns-established:
  - "Python execution contracts use explicit status/reason enums rather than inferring UI state from freeform text."
  - "Conversation-scoped Python state is owner-bound, expiring, and repository-mediated from the first migration."
  - "Backend trust-boundary checks use AST scanning to forbid exec/eval/subprocess execution paths inside FastAPI code."
requirements-completed: [CHAT-12, SBOX-01, SBOX-07]
duration: 43min
completed: 2026-06-12
---

# Phase 4: Plan 01 Summary

**Typed Python result contracts, expiring conversation state storage, reviewed artifact metadata, and a backend trust-boundary guard are now defined before any runtime or UI work begins.**

## Performance

- **Duration:** 43 min
- **Started:** 2026-06-12T01:55:00+07:00
- **Completed:** 2026-06-12T02:38:03+07:00
- **Tasks:** 3
- **Files modified:** 14

## Accomplishments

- Added RED-first Python contract tests for result taxonomy, artifact metadata, repository state, and forbidden backend execution surfaces.
- Implemented the shared Python contract module plus `PythonExecutionResult` and `PythonExecutionArtifact` DTOs with bounded fields and state-specific validation.
- Added `python_session_states` and `python_artifact_records` models, a repository seam, and Alembic revision `0003_python_execution_contracts`.
- Updated migration coverage so the Python tables and new head revision are part of the verified schema contract.

## Task Commits

No commit was created in this manual execution run.

Normal GSD commit orchestration is currently unavailable in this checkout because `node` is missing and the Docker-backed test runtime is not running.

## Files Created/Modified

- `backend/app/python_contract.py` - Shared enums and size limits for Python execution contracts.
- `backend/app/schemas/python.py` - Typed Python execution and artifact DTOs with bounded validation.
- `backend/app/models/python_state.py` - SQLAlchemy models for expiring session state and reviewed artifact metadata.
- `backend/app/db/repositories/python_state.py` - Owner-scoped repository methods for Python session state and artifacts.
- `backend/alembic/versions/0003_python_execution_contracts.py` - Migration that adds Python persistence tables and expands ToolExecution status constraints.
- `backend/tests/unit/python/test_result_envelope.py` - DTO contract tests for status taxonomy and metadata bounds.
- `backend/tests/integration/python/test_execution_contracts.py` - Repository and metadata persistence tests.
- `backend/tests/security/test_python_backend_boundary.py` - AST guard against direct backend Python execution surfaces.
- `backend/tests/integration/db/test_migrations.py` - Head revision and table-set updates for the Python contracts.

## Decisions Made

- Used a neutral `app/python_contract.py` module so SQLAlchemy and repository code can share Python enums and limits without importing API-schema packages.
- Kept `ToolExecution` as the canonical audit row and added separate tables only for bounded session snapshots and reviewed artifact metadata.
- Constrained artifact names, storage keys, file types, hashes, and sizes at the schema and database layers to avoid arbitrary filesystem surfaces from day one.

## Deviations from Plan

None in product scope. The plan was implemented as written.

## Issues Encountered

- Docker was not running, so the compose-based pytest commands from the plan could not execute.
- The host Python is `3.14`, while the backend project targets `>=3.13,<3.14`, and this machine also lacks backend dependencies such as `pydantic` and `sqlalchemy`.
- Verification was therefore limited to static syntax checks via `python -m compileall` and source review rather than runtime pytest execution.

## User Setup Required

None - no external service configuration was added in this plan.

## Next Phase Readiness

- Phase `04-02` can now implement the trusted supervisor and runtime profiles against a stable DTO and persistence contract.
- Phase `04-03` can attach chat/coordinator flows to `ToolExecution`, `PythonStateRepository`, and the reviewed status taxonomy without redefining Python result semantics.
- Before claiming runtime verification, the intended backend environment still needs Docker running or a matching Python `3.13` environment with project dependencies installed.

---
*Phase: 04-isolated-python-execution*
*Completed: 2026-06-12*
