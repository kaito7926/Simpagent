# Phase 4: Isolated Python Execution - Context

**Gathered:** 2026-06-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver policy-gated Python execution through the chat workflow so an authorized user can run bounded code and receive useful results without granting that code access to the backend process, host, application network, secrets, or runtime policy. Search chaining, package installation, arbitrary commands, and broader artifact handling remain outside this phase.

</domain>

<decisions>
## Implementation Decisions

### Invocation and Policy
- **D-01:** The coordinator may select Python automatically when a natural-language prompt clearly implies code execution. The chat composer should not expose a dedicated Python mode toggle.
- **D-02:** Phase 4 stays within the locked v1 rule of at most one tool invocation per user turn. If a request would need both Search and Python, run Python only when the prompt already contains enough data; otherwise deny the request with an explanation instead of chaining tools.
- **D-03:** If the user lacks `tool:python`, the frontend should render a dedicated tool-denied card rather than a generic error message.

### Isolation and Execution State
- **D-04:** Each Python execution runs in a fresh sandbox container.
- **D-05:** Python state is retained per conversation for a short inactivity window instead of being global, permanent, or browser-session-scoped.
- **D-15:** Conversation-scoped Python state uses a 15-minute sliding inactivity window. Each accepted Python execution resets the timer, and expired sessions restart from a clean environment.
- **D-06:** Backend policy owns exactly two reviewed sandbox limits profiles. Prompt text, model output, and client input cannot modify runtime limits directly.
- **D-16:** `python-basic-v1` is the default reviewed profile. Backend may elevate to `python-data-v1` only for clearly data-oriented work or approved artifact-producing requests such as `csv`, `json`, or `png`; if uncertain, stay on `python-basic-v1`.
- **D-07:** The system retries once only for worker-start failures. Execution failures, policy denials, and user-code failures do not auto-retry.

### Runtime Policy and Artifacts
- **D-08:** The sandbox image should ship with a small prebuilt package allowlist instead of standard-library-only or open-ended package installation.
- **D-09:** Disallowed imports should fail with a clear policy error card, not a generic import failure UX.
- **D-10:** The sandbox may create small temporary files in its workspace and may return reviewed downloadable artifacts.
- **D-11:** Downloadable artifacts are limited to small reviewed output types such as `csv`, `json`, `txt`, and `png`.
- **D-17:** Reviewed artifacts share the same 15-minute sliding session window as conversation-scoped Python state. The file payload is deleted on expiry, while download requests after expiry should return `410 Gone`.

### Result Presentation
- **D-12:** Python responses should render as a dedicated Python result card with an assistant summary and expandable raw execution details.
- **D-13:** The default card view should show a short summary, execution status, duration, and artifact links.
- **D-14:** Limit-triggered termination should render as a dedicated limit-reached card that names the exact limit that stopped execution.
- **D-18:** Exceptions raised by user code are not infrastructure failures. They should surface as completed Python execution results with a short failure summary and expandable trimmed traceback details.

### the agent's Discretion
- Choose the conversation-state storage shape and cleanup implementation, as long as it enforces the locked 15-minute sliding conversation window.
- Choose the exact CPU, memory, wall-time, file, PID, and output caps for `python-basic-v1` and `python-data-v1`, while keeping them backend-owned and non-user-configurable.
- Choose the exact small package allowlist and exact artifact size caps within the user's approved "small prebuilt set" and "small reviewed outputs" boundary.
- Choose the precise denial and explanation copy for missing permission, blocked imports, and requests that need Search plus Python but do not include enough data for a Python-only run.
- Choose whether reviewed text or image artifacts get inline previews in addition to download links, as long as the dedicated Python card remains the primary UX.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and Locked Requirements
- `.planning/ROADMAP.md` - Defines the Phase 4 boundary, dependencies, requirements, and success criteria.
- `.planning/REQUIREMENTS.md` - Defines `CHAT-12`, `SBOX-01` through `SBOX-08`, and the project-wide verification expectations that constrain Phase 4.
- `.planning/PROJECT.md` - Defines the project's security boundary, local-tool constraints, and the rule that user Python never executes in the backend or directly on the host.
- `.planning/STATE.md` - Records carried-forward project decisions and the broader milestone context around tool isolation.

### Architecture and Risk Guidance
- `.planning/research/ARCHITECTURE.md` - Defines the recommended trusted-supervisor plus isolated-runtime split, the capability-token contract, and the separation between backend policy and sandbox execution.
- `.planning/research/SUMMARY.md` - Captures the recommended phase ordering, the Phase 4 research flags, and the security rationale for keeping Python behind a separate worker boundary.
- `.planning/research/PITFALLS.md` - Highlights the policy-bypass, logging-leakage, and internal-call-path risks that Phase 4 must explicitly avoid.

### Prior Decisions That Carry Forward
- `.planning/phases/01-secure-platform-and-account-access/01-CONTEXT.md` - Carries forward the decision that standard users include `tool:python` and that FastAPI remains the authorization authority even when later tool flows are added.

### Original Brief and Local Guidance
- `prompt.md` - Original project brief with the fixed sandbox and security constraints.
- `AGENTS.md` - Generated local workflow and stack guidance used by downstream GSD agents.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/authorization/policy.py` already defines `tool:python` as a first-class scope and uses fail-closed scope evaluation helpers.
- `backend/app/models/domain.py` already includes `Conversation`, `Message`, and `ToolExecution` models, with tool execution states `queued`, `running`, `succeeded`, `failed`, `denied`, and `timed_out`.
- `backend/app/core/config.py` already centralizes validated security configuration and is the right seam for sandbox profile configuration, capability settings, and bounded artifact controls.
- `sandbox/Dockerfile` and `sandbox/server.py` already provide a sandbox container placeholder and health surface, but they do not yet implement isolated user-code execution.
- `frontend/lib/auth-session.ts` already models `tool:python` as a known scope and includes sandbox readiness in the readiness payload shape.

### Established Patterns
- Backend code is organized around thin route handlers, validated settings, explicit service layers, and fail-closed authorization behavior.
- Migrations already provision the persistence tables needed for future chat and tool work, so Phase 4 can build on existing conversation and tool execution records rather than inventing new storage from scratch.
- The current frontend uses explicit state machines and dedicated error UI rather than silent fallbacks, which matches the requested tool-denied and limit-reached card behavior.

### Integration Points
- Phase 4 should attach Python execution to the existing `ToolExecution` persistence path and future conversation/message flow rather than creating an unrelated execution subsystem.
- Sandbox profile configuration should be backend-owned and validated through existing settings patterns, not derived from user prompts or model output.
- The current sandbox container should evolve into the trusted supervisor/runtime boundary described in research, without ever executing user code in the backend process or in the same long-lived control process.
- The frontend will need new Python result-card components in the future chat surface, but it can reuse the current readiness and error-handling conventions already present in account-access flows.

</code_context>

<specifics>
## Specific Ideas

- Keep Python invocation natural-language-first with no explicit "Run Python" toggle.
- Use a dedicated tool-denied card for missing `tool:python` permission.
- Use a dedicated Python result card with expandable raw details, plus a distinct card for exact limit-trigger failures.
- Prefer deny-and-explain behavior over hidden multi-tool chaining when a request would require Search and Python in the same turn.
- Default to `python-basic-v1`, and elevate to `python-data-v1` only for clearly data-heavy or approved artifact-producing runs.
- Expire conversation-scoped Python state and reviewed artifact files with the same 15-minute sliding window.
- Treat user-code exceptions as execution results, not infrastructure failures.

</specifics>

<deferred>
## Deferred Ideas

- Support a single user turn that chains Search and Python after additional policy review and a roadmap change, since the current v1 rule allows at most one tool invocation per turn.

</deferred>

---

*Phase: 4-Isolated Python Execution*
*Context gathered: 2026-06-12*
