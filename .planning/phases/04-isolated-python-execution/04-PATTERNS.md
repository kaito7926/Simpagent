# Phase 04: Isolated Python Execution - Pattern Map

**Mapped:** 2026-06-12
**Repository state:** Early platform/auth foundation; no chat, Search, or Python execution implementation yet
**Expected file/symbol groups classified:** 15
**Reusable application analogs found:** 8 / 15

## Current Repo Finding

The repository now has real backend and frontend foundations, but only for account access and readiness. The chat flow, coordinator, search worker, and Python execution layers described in the roadmap do not exist yet in product code.

- Existing backend layering exists: thin routes, validated settings, explicit services, repositories, models, and security helpers.
- Existing frontend layering exists: local semantic components, stateful client helper modules, and explicit status/error surfaces.
- Existing sandbox code is only a health-only placeholder.
- Phase 4 therefore must reuse current application conventions while introducing the first real tool-execution boundary.

`.codex/**` remains workflow tooling and MUST NOT be used as a product-code analog.

## Canonical Source Order

When sources overlap, use this order:

1. `04-CONTEXT.md` for locked Phase 4 decisions.
2. `04-UI-SPEC.md` for Python-specific rendering, labels, and interaction rules.
3. `04-RESEARCH.md` for architecture, isolation, artifact, and validation guidance.
4. Current repo code analogs listed below for concrete module and component patterns.
5. `AGENTS.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `PROJECT.md`, and `prompt.md` for project-wide constraints.

## Resolved Source Gap

Phases 2 and 3 are roadmap dependencies but their implementation artifacts are not present in this checkout. Planning must therefore:

- preserve the current backend/frontend conventions that do exist
- target the expected future chat/tool surfaces without pretending concrete chat analogs already exist
- avoid redesigning account-access code just to host Python execution

## File Classification

| # | Expected File or Symbol Group | Role | Closest Analog | Canonical Pattern |
|---:|---|---|---|---|
| 1 | `backend/app/api/routes/chat.py` or equivalent tool-enabled chat route | controller/route | `backend/app/api/routes/auth.py` | Thin route, dependency injection, typed error mapping |
| 2 | `backend/app/agent/coordinator.py`, `decisions.py`, `policy.py` | service/policy | `backend/app/services/authentication.py`, `backend/app/authorization/policy.py` | Backend owns sequencing and authorization, not routes |
| 3 | `backend/app/tools/python_client.py` or equivalent internal RPC client | client/service | `backend/app/core/provider_status.py` for external-state mapping | Typed backend-owned request envelope |
| 4 | `backend/app/services/python_sessions.py` | service/state machine | `backend/app/services/sessions.py` | Transactional state transitions and expiry logic |
| 5 | `backend/app/schemas/python.py` or tool result DTOs | schema | `backend/app/schemas/auth.py` | Pydantic request/response models hide internal fields |
| 6 | `backend/app/models/domain.py` additions or adjacent Python session/artifact models | model | existing `ToolExecution` and `Message` models | Typed SQLAlchemy models, explicit constraints, JSONB only where justified |
| 7 | `backend/app/core/config.py` additions for sandbox profiles and retention | config | existing `Settings` | Immutable validated settings, no user-controlled policy knobs |
| 8 | `backend/app/security/tool_capabilities.py` or equivalent | security helper | `backend/app/security/access_tokens.py` | Signed, typed, explicit-claim token helpers |
| 9 | `sandbox/server.py` supervisor API | trusted runtime control plane | current `sandbox/server.py` placeholder | Supervisor never executes user code directly |
| 10 | `sandbox/runtime/**` execution entrypoint and profile assets | untrusted runtime | current `sandbox/Dockerfile` base | Runtime is minimal, fixed, and isolated |
| 11 | `sandbox/seccomp/**` or profile manifests | config/security | none yet | Runtime controls are fixed artifacts, not request input |
| 12 | `frontend/components/chat/python/**` | UI component | `frontend/components/account-access/InlineAlert.tsx`, `StatusBadge.tsx` | Local semantic components with explicit tones and states |
| 13 | `frontend/lib/chat/**` or equivalent tool-state helpers | client/service | `frontend/lib/auth-session.ts` | Explicit state machine and typed transport helpers |
| 14 | `backend/tests/integration/python/**`, `backend/tests/security/python/**` | verification | current auth/security test layout | Narrow module suites with side-effect assertions |
| 15 | `compose.yaml`, `compose.test.yaml`, sandbox service wiring | orchestrator/config | current Compose layout | Private service boundaries, explicit health/readiness, no unsafe host exposure |

## Pattern Assignments

### Backend Route and Service Ownership

**Applies to:** tool-enabled chat route, coordinator, Python session service

- Route handlers validate transport, load dependencies, and map typed failures to HTTP.
- Services own sequencing, transactions, and persistence.
- Authorization is rechecked in backend policy immediately before execution.
- New Python logic should follow the same separation visible in `auth.py` and `authentication.py`.

### Configuration and Policy Ownership

**Applies to:** `backend/app/core/config.py`, profile configuration, retention settings

- All policy-relevant configuration belongs in immutable validated settings.
- Limits profiles are backend-owned named policies, not request parameters.
- Allowed artifact types, session TTLs, and runtime image/profile names are configuration or code constants, not user inputs.

### Persistence and Evidence

**Applies to:** `ToolExecution`, any Python session/artifact tables, message metadata

- Prefer explicit columns for status, duration, and correlation identifiers.
- Keep `ToolExecution` as the canonical audit row for requested/denied/running/succeeded/failed/timed_out work.
- Add separate state or artifact storage only when the fields do not fit cleanly in existing execution/message models.

### Frontend State and Components

**Applies to:** Python cards, denied/limit cards, artifact list, client tool helpers

- Use local semantic components rather than adopting a generic terminal or notebook framework.
- Reuse the tone-based approach from `InlineAlert` and `StatusBadge`.
- Keep chat-tool state explicit in a typed client helper, similar to the existing auth session controller.

### Sandbox Boundary

**Applies to:** `sandbox/server.py`, runtime entrypoint, runtime profile assets

- The current placeholder server proves only health. It is not a valid analog for user-code execution.
- The trusted supervisor may orchestrate runtime creation and cleanup, but untrusted code runs only in the ephemeral runtime boundary.
- The request contract to the supervisor must be minimal and typed; callers never control mounts, devices, network, or arbitrary commands.
