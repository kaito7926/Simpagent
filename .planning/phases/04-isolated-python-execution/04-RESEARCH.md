# Phase 4: Isolated Python Execution - Research

**Researched:** 2026-06-12
**Domain:** Policy-gated Python execution, sandbox isolation, bounded artifacts, conversation-scoped tool state, and explicit in-chat tool UX
**Confidence:** HIGH for architecture and repo integration direction; MEDIUM for exact runtime profile tuning because phases 2 and 3 are not yet implemented in this checkout

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** The coordinator may select Python automatically from natural-language intent, and the composer must not expose a dedicated Python toggle.
- **D-02:** v1 remains one-tool-per-turn. Requests that need both Search and Python must deny-and-explain unless the prompt already contains enough data for Python-only execution.
- **D-03:** Missing `tool:python` permission renders a dedicated tool-denied card.
- **D-04:** Each execution uses a fresh sandbox container.
- **D-05:** Python state is retained per conversation for a short inactivity window.
- **D-06:** Backend policy owns exactly two reviewed sandbox limits profiles.
- **D-07:** Retry once only for worker-start failures.
- **D-08:** Ship a small prebuilt package allowlist.
- **D-09:** Disallowed imports surface as a clear policy error card.
- **D-10:** Small temporary files and reviewed downloadable artifacts are allowed.
- **D-11:** Approved artifact types are limited to small reviewed outputs such as `csv`, `json`, `txt`, and `png`.
- **D-12:** Python results render as a dedicated Python card with expandable raw details.
- **D-13:** Default card content shows summary, status, duration, and artifact links.
- **D-14:** Hard-limit termination renders as a dedicated card naming the exact limit.

### the agent's Discretion
- Choose the exact short inactivity TTL and how state snapshots are stored and expired.
- Choose the two profile names, exact caps, and selection rules.
- Choose the exact small package allowlist and size caps for reviewed artifacts.
- Choose the final wording for deny/explain flows and whether approved artifact previews exist in addition to downloads.

### Deferred Ideas (OUT OF SCOPE)

- Multi-tool Search-to-Python chaining in one user turn.
</user_constraints>

## Summary

Phase 4 should extend the existing security architecture rather than bolt a mini-notebook onto the product. The right shape is: backend policy decides whether Python may run, signs a one-shot internal capability, persists a `ToolExecution` state transition, and hands the request to a trusted sandbox supervisor. The supervisor validates the capability, selects one backend-owned limits profile, creates a fresh execution container, captures bounded output and approved artifacts, destroys the container, and returns a typed result envelope. The frontend then renders a dedicated Python card that is visibly different from direct assistant replies and Search results. The backend, not the model, remains authoritative for whether Python runs, which profile applies, what artifacts are returned, and how retained state expires.

**Primary recommendation:** Plan Phase 4 in this order: execution contracts and RED tests; trusted supervisor and runtime profile implementation; backend coordinator/session-state integration; Python-specific frontend rendering; then end-to-end abuse and cleanup verification.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| Tool authorization immediately before execution | API / Backend | Database / Storage | `tool:python` and one-tool-per-turn remain backend policy decisions, not model decisions. |
| Internal capability credential | API / Backend | Sandbox supervisor | The backend signs the exact execution request; the supervisor only accepts capability-bound invocations. |
| Fresh runtime isolation | Sandbox supervisor | Runtime container | The trusted control plane owns container creation; untrusted code runs only in the ephemeral container. |
| Limits profile ownership | API / Backend | Sandbox supervisor | The backend chooses one of two approved profiles; the supervisor enforces, but never invents, runtime policy. |
| Conversation-scoped Python state window | API / Backend | Database / Storage | State continuity and expiry belong to application semantics, not the runtime container lifetime. |
| Artifact filtering and transport | Sandbox supervisor | API / Backend | The runtime may generate outputs, but the supervisor and backend decide which artifacts are safe to surface. |
| Python card rendering | Frontend | Backend typed response contract | The frontend distinguishes tool states, but the backend provides the trusted status/result envelope. |
| Cleanup and evidence | Sandbox supervisor | Database / Storage | The system must prove container cleanup, bounded output, and persisted execution state. |

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|---|---|---|
| CHAT-12 | User can distinguish direct LLM, Search, and Python responses. | Dedicated Python card, status badges, and explicit deny/limit states. |
| SBOX-01 | Backend never executes user Python directly. | All execution crosses a sandbox supervisor boundary; FastAPI only signs and records work. |
| SBOX-02 | Authorized code runs only through a dedicated fixed-policy sandbox boundary. | One supervisor API plus two backend-owned reviewed profiles. |
| SBOX-03 | Sandbox has no network access and cannot reach internal addresses. | `network=none`, no host networking, no internal service joins, no metadata or private address access. |
| SBOX-04 | Sandbox runs non-root with read-only root, temp writable space, dropped caps, `no-new-privileges`, and seccomp. | Execution profile hardcodes these controls; callers cannot override them. |
| SBOX-05 | Sandbox enforces time, CPU, memory, PID, file, process, and output limits and reports the terminating limit. | Profiles define hard caps, and result envelopes include the exact terminating limit. |
| SBOX-06 | Sandbox receives no secrets, host paths, Docker socket, privileged mode, host namespaces, devices, or caller-controlled runtime config. | The supervisor owns runtime options, and the container receives only code plus the selected profile. |
| SBOX-07 | Sandbox captures bounded stdout/stderr/status/duration and removes temporary execution data. | Typed result envelope and cleanup verification after every run. |
| SBOX-08 | Package installation and arbitrary external commands are denied. | Prebuilt allowlist only; no pip, no arbitrary subprocess, no shell escape surface. |
</phase_requirements>

## Existing Repo Implications

- `backend/app/authorization/policy.py` already models `tool:python` as a first-class scope, so Phase 4 should extend current authorization patterns rather than invent a separate permission model.
- `backend/app/models/domain.py` already contains `ToolExecution`, which should remain the canonical execution audit surface.
- `frontend/lib/auth-session.ts` already includes sandbox readiness in the readiness payload shape, so Phase 4 should reuse the same fail-closed UI posture for Python availability.
- `sandbox/server.py` is only a health foundation today. It must not become the place where untrusted code executes directly.
- Earlier chat and Search surfaces are not yet implemented in this checkout, so Phase 4 plans must target future chat integration while preserving current backend/frontend layering conventions.

## Recommended Architecture Patterns

### Pattern 1: Explicit Python Result Envelope

Return a typed backend envelope instead of raw runtime blobs:

- `status`
- `summary`
- `stdout_excerpt`
- `stderr_excerpt`
- `duration_ms`
- `profile_name`
- `limit_triggered`
- `artifacts[]`
- `execution_id`
- `correlation_id`

The frontend should not infer result state from raw text.

### Pattern 2: Trusted Supervisor + Ephemeral Runtime

Separate trusted orchestration from untrusted execution:

- The supervisor validates capability, selects the fixed runtime profile, and owns cleanup.
- The runtime container executes user code only and has no authority to choose mounts, network, or devices.
- The backend never shells out or calls Python execution directly.

### Pattern 3: Conversation-Scoped State Snapshot

Because users want a short-lived Python session window but each run uses a fresh container, retained state must be an application-level feature rather than process persistence. The backend should store bounded state snapshots keyed by conversation and expire them after inactivity. The runtime receives only the restored bounded state needed for the next run.

### Pattern 4: Approved Artifact Surface

Treat artifacts as a reviewed output channel:

- Only approved small types may leave the runtime.
- File names, types, and sizes are validated by the supervisor/backend.
- Unknown or oversized outputs become denied artifacts, not silent downloads.

### Pattern 5: Policy-Specific UX

Use different backend statuses and frontend cards for:

- missing permission
- policy-blocked imports/behavior
- hard-limit termination
- infrastructure failure
- successful completion

This avoids teaching users that all failures are the same class of problem.

## Validation Architecture

Phase 4 should rely on side-effect assertions rather than trusting output wording:

- verify the backend process never runs user code
- verify the sandbox container has no network and no host mounts
- verify blocked imports and commands create no side effects
- verify exact limits are surfaced in result metadata
- verify approved artifacts survive only through the allowed response path
- verify cleanup removes temporary execution state from the runtime boundary
- verify one-tool-per-turn and missing-permission flows leave no supervisor invocation behind

The most important execution evidence is not the response body; it is the persisted `ToolExecution` state, the absence of forbidden side effects, and the bounded runtime configuration.

## Implementation Order

1. **Contracts and RED tests first** so later plans implement against stable result, artifact, and state-window semantics.
2. **Supervisor/runtime second** because the backend cannot safely integrate Python until the trusted boundary exists.
3. **Backend orchestration next** to connect authorization, capability signing, `ToolExecution`, and short-lived Python state.
4. **Frontend rendering after contracts exist** so the Python card states align to the real typed envelope.
5. **End-to-end and abuse verification last** to prove cleanup, denial, limit, and isolation behavior against the assembled stack.

## Planning Consequences

- Do not plan package installation, arbitrary shell execution, or general file browsing into this phase.
- Keep all Python execution behind one fixed internal API rather than scattering runtime behavior across FastAPI routes and helpers.
- Make artifact validation a first-class task rather than a post-processing detail.
- Treat retained state as a bounded application feature with explicit expiry, not as a long-lived worker process.
- Ensure at least one plan owns the exact UX distinction between Python success, deny, policy error, and limit termination.
