# Phase 4: Isolated Python Execution - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-06-12
**Phase:** 4-isolated-python-execution
**Areas discussed:** Invocation flow, Sandbox shape, Runtime contents, Result UX, Session retention, Profile selection, User-code failures

---

## Invocation flow

### Python selection

| Option | Description | Selected |
|--------|-------------|----------|
| User trigger only | Python runs only when the user explicitly asks for the tool. | |
| Coordinator auto-selects Python | The coordinator may choose Python when the prompt clearly implies code execution. | ✓ |

**User's choice:** Coordinator auto-selects Python from natural-language intent.
**Notes:** The composer should remain natural-language only; no dedicated "Run Python" toggle.

### Search plus Python in one turn

| Option | Description | Selected |
|--------|-------------|----------|
| Ask user to choose one tool | Stop and have the user pick Search or Python. | |
| Run Search only | Prefer Search and require a follow-up turn for Python. | |
| Run Python only when enough data is already in the prompt | Stay within the one-tool-per-turn rule and deny if external data would be needed first. | ✓ |

**User's choice:** Run Python only when the prompt already includes enough data; otherwise deny and explain.
**Notes:** True Search-to-Python chaining was called out as desirable later, but deferred because v1 is locked to one tool invocation per turn.

### Permission failure UX

| Option | Description | Selected |
|--------|-------------|----------|
| Plain in-chat denial message | Show a normal assistant text denial. | |
| Special tool-denied card | Use a dedicated card for missing `tool:python` permission. | ✓ |
| Generic failure state | Reuse the same error state as infrastructure failures. | |

**User's choice:** Special tool-denied card.
**Notes:** The denial should be visually distinct from runtime failures and from normal assistant responses.

---

## Sandbox shape

### Isolation model

| Option | Description | Selected |
|--------|-------------|----------|
| Fresh container per run | Strong isolation and clean runtime for every execution. | ✓ |
| Warm worker pool with hard reset | Reuse workers but perform a reset between runs. | |
| Single long-lived worker | Keep one persistent runtime process. | |

**User's choice:** Fresh container per run.
**Notes:** This is the primary isolation boundary despite short-lived logical state retention.

### Execution state window

| Option | Description | Selected |
|--------|-------------|----------|
| Clean state every run | No state continuity between Python turns. | |
| Keep state within the conversation | Unlimited conversation-scoped continuity. | |
| Keep state for a short session window | Preserve limited state briefly, then expire it automatically. | ✓ |

**User's choice:** Keep state for a short session window.
**Notes:** State should stay conversation-scoped, not global.

### Limits profile ownership

| Option | Description | Selected |
|--------|-------------|----------|
| One fixed profile | Every Python run uses the same limits. | |
| Two reviewed profiles | Backend policy can choose between two reviewed runtime profiles. | ✓ |
| Adjust from prompt intent | Let prompt content influence limits dynamically. | |

**User's choice:** Two reviewed profiles.
**Notes:** Limits remain backend-owned rather than prompt- or model-controlled.

### Infra failure retry

| Option | Description | Selected |
|--------|-------------|----------|
| No automatic retry | Surface the failure and require a manual rerun. | |
| Retry once only for worker-start failures | Retry infrastructure startup issues once. | ✓ |
| Retry once for any failure | Retry both startup and execution failures once. | |

**User's choice:** Retry once only for worker-start failures.
**Notes:** User-code failures and policy denials should not auto-retry.

---

## Runtime contents

### Package policy

| Option | Description | Selected |
|--------|-------------|----------|
| Python standard library only | No third-party packages in the runtime image. | |
| Small prebuilt allowlist | Ship a small approved package set in the image. | ✓ |
| Broader curated data-science set | Include a larger prebuilt package catalog. | |

**User's choice:** Small prebuilt allowlist.
**Notes:** Package installation is still out of scope.

### Blocked import UX

| Option | Description | Selected |
|--------|-------------|----------|
| Clear policy error card | Explain that the import is blocked by policy. | ✓ |
| Normal ImportError | Let Python fail as if the module were missing. | |
| Warn first then block | Intercept and warn before refusing execution. | |

**User's choice:** Clear policy error card.
**Notes:** The UX should make policy denial distinct from accidental code bugs.

### File and artifact behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Temp workspace only | Allow ephemeral files but no user-downloadable artifacts. | |
| No file writes | Disallow all writes inside the sandbox. | |
| Small temp files plus downloadable artifacts | Allow bounded temp files and reviewed downloadable outputs. | ✓ |

**User's choice:** Small temp files plus downloadable artifacts.
**Notes:** Downloadable outputs should remain limited and reviewed.

### State expiry model

| Option | Description | Selected |
|--------|-------------|----------|
| Per conversation with short inactivity window | Expire retained state after brief idle time. | ✓ |
| Per browser session only | Tie retention to the browser session instead of the conversation. | |
| Fixed number of Python turns | Reset after a fixed number of executions. | |

**User's choice:** Per conversation with short inactivity window.
**Notes:** The chosen expiry model matches the earlier short session window decision.

### Sliding expiration semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed inactivity window | Set one short TTL and do not extend it after later Python runs. | |
| 15-minute sliding expiration | Reset the inactivity timer each time a Python execution is accepted. | âœ“ |
| Conversation-lifetime retention | Keep Python state until the conversation is explicitly ended or deleted. | |

**User's choice:** 15-minute sliding expiration.
**Notes:** Each accepted Python execution resets the 15-minute timer; when the timer expires, the next run starts from a clean environment.

### Profile selection policy

| Option | Description | Selected |
|--------|-------------|----------|
| Always use `python-basic-v1` | One reviewed profile for every request. | |
| Default to `python-basic-v1`, elevate narrowly to `python-data-v1` | Backend upgrades only for clearly data-oriented or approved artifact-producing requests. | âœ“ |
| Let prompt intent choose either profile freely | Model or prompt content may request the larger profile directly. | |

**User's choice:** Default to `python-basic-v1`, elevate narrowly to `python-data-v1`.
**Notes:** If backend policy is not confident that a request needs the data profile, it should stay on `python-basic-v1`.

---

## Result UX

### Result presentation

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated Python result card | Assistant summary plus expandable raw details. | ✓ |
| Raw stdout/stderr block only | Show execution output with no special container. | |
| Plain assistant message | Merge the result into a normal assistant response. | |

**User's choice:** Dedicated Python result card.
**Notes:** Python should be visually distinguishable from direct chat and Search.

### Default card contents

| Option | Description | Selected |
|--------|-------------|----------|
| Summary + status + duration + artifact links | Compact default view with the key execution facts. | ✓ |
| Summary + full stdout visible immediately | Show the full raw output by default. | |
| Only final answer text unless expanded | Hide most execution metadata initially. | |

**User's choice:** Summary + status + duration + artifact links.
**Notes:** Raw details should remain available behind expansion.

### Limit-triggered termination

| Option | Description | Selected |
|--------|-------------|----------|
| Special limit-reached card naming the exact limit | Make the stopping condition explicit. | ✓ |
| Generic execution failure | Treat it like any runtime failure. | |
| Raw runtime error only | Surface only low-level error text. | |

**User's choice:** Special limit-reached card naming the exact limit.
**Notes:** This should cover time, memory, CPU, output, and other enforced bounds.

### Download policy

| Option | Description | Selected |
|--------|-------------|----------|
| Only small reviewed text/data outputs | Restrict downloads to approved lightweight types such as csv/json/txt/png. | ✓ |
| Any file type under a size cap | Allow arbitrary content as long as it is small enough. | |
| No downloads | Keep artifacts inline only. | |

**User's choice:** Only small reviewed text/data outputs.
**Notes:** This narrows the approved artifact set while still enabling useful sandbox outputs.

### Artifact retention window

| Option | Description | Selected |
|--------|-------------|----------|
| Keep downloadable files indefinitely | Artifact links remain valid until manual cleanup. | |
| Match artifact lifetime to the Python session window | Artifact payloads expire with the same sliding inactivity window and expired links return `410 Gone`. | âœ“ |
| Remove artifact payloads immediately after rendering | No durable downloads after the first response. | |

**User's choice:** Match artifact lifetime to the Python session window.
**Notes:** Audit metadata may remain, but the file payload should be cleaned up when the conversation-scoped Python session expires.

### User-code exception mapping

| Option | Description | Selected |
|--------|-------------|----------|
| Treat as infrastructure failure | Use the same state as worker or sandbox startup failures. | |
| Treat as completed execution result with traceback details | Surface a failure summary and trimmed traceback without marking the sandbox itself failed. | âœ“ |
| Add a new notebook-style exception mode | Create a separate interactive error experience. | |

**User's choice:** Treat as completed execution result with traceback details.
**Notes:** User-code exceptions must stay distinct from infra failures and may expose a trimmed traceback only inside expandable details.

---

## the agent's Discretion

- Exact package allowlist and exact artifact size caps.
- Exact state snapshot storage shape and cleanup implementation.
- Exact caps for `python-basic-v1` and `python-data-v1`.
- Exact UI copy for denials, blocked imports, and limit-triggered failures.

## Deferred Ideas

- Single-turn Search to Python chaining after a future roadmap change and policy review.
