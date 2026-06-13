# Phase 3: Policy-Controlled Google Search - Research

**Researched:** 2026-06-11
**Domain:** Policy-controlled Google-grounded search inside the chat flow, with a typed FastAPI coordinator, a dedicated Google ADK worker, grounding-integrity UI, and explicit degraded states
**Confidence:** HIGH for architecture, persistence seams, and UI/state contracts; MEDIUM for exact Google retention details and currently available Gemini 2 model support because those must be revalidated against live provider behavior at implementation time

<user_constraints>
## User Constraints (from CONTEXT.md, AI-SPEC.md, and UI-SPEC.md)

### Locked Decisions
- **D-01:** Search is an explicit per-turn mode inside the chat flow. The user must choose between normal chat and Google Search before submitting.
- **D-02:** Successful grounded search responses show inline citation markers, a compact `Google-grounded` badge, a source list with `title + domain` only, and a separate Search Suggestions block.
- **D-03:** Clicking a Search Suggestion pre-fills the composer and waits for explicit user submission. Suggestion clicks must never auto-run a new search turn.
- **D-04:** If the worker returns answer text without the required grounding metadata, render it as a normal assistant response with no badge, no citations, and no suggestions, plus the note `có thể tham khảo`.
- **D-05:** Denied search turns must clearly state that search was blocked and that no search was executed.
- **D-06:** `search_unavailable`, `provider_failed`, and `timeout` are distinct user-visible outcomes and each failed search turn owns an inline `Thử lại tìm kiếm` action.
- **D-07:** Google ADK 2.2.x is used only for the dedicated Gemini search worker. The top-level coordinator remains hand-written and typed in FastAPI.
- **D-08:** The current local frontend component system is preserved. Do not initialize shadcn for this phase.

### the agent's Discretion
- Choose the exact internal request/response schema between the FastAPI coordinator and the search worker as long as the boundary is typed, fail-closed, and does not forward the user's bearer token.
- Choose the normalized persistence shape for grounded metadata, source rows, retry state, and suggestion payloads as long as the UI contract and Google retention constraints remain satisfied.
- Choose the exact time, token, concurrency, retry, and cost budgets as long as only one bounded tool invocation is possible per turn and all degraded states remain explicit.
- Choose whether the search worker runs in-process or as a separate internal service boundary, as long as it retains separate credentials and a typed capability boundary from normal chat and Python execution.

### Deferred Ideas (OUT OF SCOPE)
- No Python execution path in this phase.
- No arbitrary HTTP tools, crawling pipeline, snippet-rich search cards, admin evidence UI, or model/tool routing beyond direct chat versus Google Search.
- No hidden fallback to automatic search when the user chose normal chat.
</user_constraints>

## Summary

Phase 3 should be planned as a bounded tool-execution phase, not as "add another model call." The primary system behavior is a deterministic FastAPI coordinator that accepts an explicit user search intent, re-checks `tool:websearch` immediately before execution, enforces one-tool-per-turn budgets, and only then delegates to a dedicated Google Search worker. This phase should reuse the repository's existing policy seam in `backend/app/authorization/policy.py`, the search-readiness seam in `backend/app/core/provider_status.py`, and the durable evidence seams already present in `backend/app/models/domain.py`. The resulting search state must persist through both `messages.metadata` and `tool_executions`, because Phase 3 is as much about evidence and failure honesty as it is about grounded answer generation. [VERIFIED: backend/app/authorization/policy.py; backend/app/core/provider_status.py; backend/app/models/domain.py]

The approved AI and UI contracts already settle the highest-risk design choices: use Google ADK only for a dedicated search worker; keep the coordinator outside model control; preserve a separate Search Suggestions block; and never present missing-grounding, denied, or unavailable states as if they were verified grounded answers. Planning should therefore optimize for translation from those contracts into executable backend/frontend work: typed internal schemas, capability credentials, metadata normalization, search-state persistence, explicit retry behavior, and negative security tests. The implementation should not spend time debating framework selection or redesigning the search UX; those questions are closed for this phase. [VERIFIED: .planning/phases/03-policy-controlled-google-search/03-AI-SPEC.md; .planning/phases/03-policy-controlled-google-search/03-UI-SPEC.md]

Current Google documentation and public examples continue to evolve. Official Grounding with Google Search docs describe grounding metadata and a trusted `searchEntryPoint` payload for Search Suggestions, while current examples and model pages can move faster than this project's locked Gemini 2 requirement. The correct planning response is not to hardcode a single model ID everywhere; it is to make the search model configuration-driven, add a startup capability probe for the selected Gemini 2 search model, and fail closed when the model cannot produce the expected grounded metadata shape. Likewise, retention behavior must be treated as an implementation-time verification point: retain only allowlisted fields needed for UI and audit, and re-check Google terms before deciding whether to persist any raw provider payload beyond that minimal allowlist. [CITED: https://ai.google.dev/gemini-api/docs/google-search; https://ai.google.dev/gemini-api/docs/models; https://pypi.org/project/google-adk/]

One practical repository reality materially affects planning: the current codebase still contains only Phase 1 account-access code. There are no chat routes, no conversation API, and no chat shell components yet. Because Phase 3 depends on Phase 2 in the roadmap but planning is happening before that code exists in the repository, Phase 3 plans must be written to integrate cleanly with future Phase 2 seams while also respecting the UI contract's fallback instruction: if the Phase 2 shell is absent at implementation time, implement the minimum shell defined in `03-UI-SPEC.md` rather than blocking on nonexistent code. That means reusing the current local component style (`ActionButton`, `InlineAlert`, `StatusBadge`, `AuthModeSwitch`) and client-state patterns (`auth-session.ts`, `readiness.ts`) instead of pretending a mature chat stack already exists in the repository. [VERIFIED: frontend/components/account-access/*.tsx; frontend/lib/auth-session.ts; frontend/lib/readiness.ts; .planning/phases/03-policy-controlled-google-search/03-UI-SPEC.md]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| Explicit search/direct mode selection | Frontend / Client | API / Backend | The client captures explicit user intent, but the backend remains authoritative for whether search actually runs. [VERIFIED: 03-UI-SPEC.md] |
| Tool allowlist and pre-execution authorization | API / Backend | Database / Storage | `tool:websearch` must be rechecked immediately before execution and cannot be granted by model output. [VERIFIED: REQUIREMENTS.md AUTHZ-04, AUTHZ-07; backend/app/authorization/policy.py] |
| Search worker orchestration | API / Backend | Dedicated ADK worker | The deterministic coordinator owns policy and budgets; the ADK worker owns only Google Search execution and typed reply generation. [VERIFIED: 03-AI-SPEC.md] |
| Capability credentials for internal tool calls | API / Backend | Worker boundary | Requirement AGNT-05 explicitly forbids forwarding the user's bearer token. A short-lived audience-bound internal credential is the correct contract seam. [VERIFIED: REQUIREMENTS.md AGNT-05] |
| Google credentials and model capability probing | API / Backend | Provider adapter | The backend already owns settings and readiness state; Phase 3 extends that seam to model support and metadata-shape checks. [VERIFIED: backend/app/core/config.py; backend/app/core/provider_status.py] |
| Grounding normalization and safe persistence | API / Backend | Database / Storage | Grounded results, degraded states, source rows, retry context, and suggestions must persist durably for UI rendering and audit. [VERIFIED: backend/app/models/domain.py] |
| Search suggestions and citation rendering | Frontend / Client | Backend metadata normalizer | The backend should send normalized safe suggestion/source payloads; the client renders them in dedicated trusted components, not via markdown HTML. [VERIFIED: 03-UI-SPEC.md] |
| Retry state and per-turn update-in-place behavior | Frontend / Client | API / Backend | The UI owns the same-turn retry affordance, while the backend owns correlation, status transitions, and no-duplicate-user-turn guarantees. [VERIFIED: 03-UI-SPEC.md; REQUIREMENTS.md AGNT-06] |
| Prompt-injection, SSRF, and tool-chaining defense | API / Backend | Worker boundary | Retrieved search content is untrusted and must never trigger internal URL fetching, policy mutation, or arbitrary tool execution. [VERIFIED: REQUIREMENTS.md AGNT-07, SRCH-08] |
| Admin/audit evidence for search actions | Database / Storage | API / Backend | Every requested, denied, started, succeeded, failed, or timed-out action needs a persisted correlated state. [VERIFIED: REQUIREMENTS.md AGNT-06; backend/app/models/domain.py] |

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|---|---|---|
| AUTHZ-04 | Web Search execution requires `tool:websearch`. | Reuse `evaluate_required_scopes`, enforce again at the coordinator boundary, and add negative tests. |
| AUTHZ-07 | Tool authorization is checked immediately before execution and cannot be granted by model output. | Coordinator-owned allowlist, no worker-side authority, no implicit tool selection. |
| AGNT-01 | Deterministic coordinator can select only direct chat, Google Search, or Python from an explicit allowlist. | Add an explicit turn mode/request schema and server-side enum; no ad hoc string switching. |
| AGNT-02 | Model may propose a tool action but cannot authorize it or select arbitrary commands/APIs. | Keep search worker instruction narrow and separate from policy; no arbitrary tool registration in the worker. |
| AGNT-03 | At most one bounded tool invocation per user turn. | One search attempt per turn, bounded retries, explicit timeout/cost/input limits, no hidden follow-on calls. |
| AGNT-04 | Search and Python use separate workers and credential boundaries. | Search worker gets its own ADK boundary and Google credentials; Python remains absent in this phase. |
| AGNT-05 | Internal tool requests use short-lived audience-bound capability credentials. | Mint a coordinator-owned short-lived internal capability token/claim set for the worker boundary. |
| AGNT-06 | Every requested, denied, started, succeeded, failed, or timed-out tool action has persisted state and correlation ID. | Extend `messages.metadata` and `tool_executions` with search-state conventions and correlation-bearing transitions. |
| AGNT-07 | User input, model output, and tool content are untrusted and never expose secrets to model context. | No bearer-token forwarding, no secret-bearing prompts, no raw search HTML in markdown, no internal fetches. |
| SRCH-01 | Dedicated Google ADK worker invokes built-in Google Search using a deployment-configured compatible Gemini 2 model. | Add `google-adk` to backend dependencies and a dedicated search worker module. |
| SRCH-02 | Startup/deployment performs a capability check for model availability, Search support, and grounding metadata. | Extend search readiness beyond `unconfigured|ready` and fail closed when the metadata contract is absent. |
| SRCH-03 | Live grounded response transports answer text and required grounding fields without falsely labeling ungrounded output as grounded. | Normalize source/support/suggestion payloads only when grounding evidence is present. |
| SRCH-04 | Frontend renders claim-to-source citations and required Search Suggestions safely. | Dedicated citation/source/suggestion components, no raw provider HTML merged into markdown. |
| SRCH-05 | Persistence and telemetry retain only fields allowed by Google terms and do not perform source-link click tracking. | Explicit persistence allowlist and a terms-review checkpoint before final field selection. |
| SRCH-06 | Search requests apply input limits, timeout, result/output limits, user budgets, and safe failure behavior. | Coordinator-side input/time/output budgets plus explicit failed states and user-triggered retry only. |
| SRCH-07 | Search failures, missing grounding, and model unavailability are visibly distinguished from success. | Backend state enum plus UI-specific copy and component treatments from UI-SPEC. |
| SRCH-08 | Search content cannot cause internal URL fetching, scope escalation, arbitrary tool execution, or policy changes. | Treat retrieved content as untrusted data only; never let it influence policy, fetch paths, or tool chaining. |
</phase_requirements>

## Project Constraints (from AGENTS.md and current code)

- Phase 3 must preserve the project stack: FastAPI/Pydantic/SQLAlchemy/PostgreSQL/Alembic on the backend and Next.js/TypeScript/Tailwind on the frontend. [VERIFIED: AGENTS.md]
- Search and Python must remain separate bounded tool surfaces. Phase 3 does not introduce or reserve a Python control path. [VERIFIED: AGENTS.md; 03-UI-SPEC.md]
- Secrets, bearer tokens, refresh tokens, provider API keys, and internal diagnostics must not be logged or forwarded into model context. [VERIFIED: AGENTS.md]
- The current backend already exposes `search_model` and `google_api_key` settings but does not yet implement ADK or model-capability probing. Phase 3 should extend those settings instead of replacing them. [VERIFIED: backend/app/core/config.py]
- The current readiness model for search is only `unconfigured` or `ready`. Phase 3 must extend this to support search-specific degraded states such as unavailable/model-unavailable without breaking existing readiness semantics. [VERIFIED: backend/app/core/provider_status.py; frontend/lib/readiness.ts]
- The current persistence layer already contains `Conversation`, `Message`, and `ToolExecution`, but there is no route/service/chat-shell implementation yet. Phase 3 planning must account for that gap explicitly. [VERIFIED: backend/app/models/domain.py; backend/app/api/routes; frontend/app; frontend/components]
- The frontend local component language is already established in `frontend/components/account-access/*` and `frontend/app/globals.css`; Phase 3 must extend those patterns instead of importing a new design system. [VERIFIED: 03-UI-SPEC.md; frontend/components/account-access/*.tsx]

## Standard Stack

### Core

| Library / Runtime | Version for Phase 3 | Purpose | Why Standard |
|---|---:|---|---|
| Python | `>=3.13,<3.14` | Backend runtime | Already locked by project stack and current backend packaging. [VERIFIED: backend/pyproject.toml; AGENTS.md] |
| FastAPI | `>=0.136,<0.137` | Search API routes, dependency injection, readiness endpoints | Existing backend already uses this line; Phase 3 extends the same service boundary. [VERIFIED: backend/pyproject.toml] |
| Pydantic 2 | `>=2.12,<3` | Typed search state, normalized source/suggestion DTOs, internal worker contracts | Required for safe backend branching and typed persistence/UI envelopes. [VERIFIED: backend/pyproject.toml] |
| SQLAlchemy 2 + PostgreSQL 18 | Existing stack | Persist message metadata, tool states, and correlated evidence | `Message.metadata` and `ToolExecution` already exist and should be extended, not replaced. [VERIFIED: backend/app/models/domain.py; compose.yaml] |
| `google-adk` | `>=2.2,<2.3` | Dedicated Google Search worker | The approved AI contract selected ADK 2.2.x specifically for this boundary. This dependency is not yet present in `backend/pyproject.toml`, so Phase 3 must add it deliberately. [VERIFIED: 03-AI-SPEC.md; backend/pyproject.toml; CITED: https://pypi.org/project/google-adk/] |
| `google-genai` | `>=2.8,<2.9` | Gemini capability probe, grounding metadata types, and provider-level checks | Already present in backend dependencies and appropriate for startup capability checks. [VERIFIED: backend/pyproject.toml; CITED: https://ai.google.dev/gemini-api/docs/google-search] |
| Configured Gemini 2 Search model | Configuration-driven | Grounded Google Search execution | Because public examples and model availability move over time, the planner should treat the model as a startup-validated capability rather than a hardcoded constant. [VERIFIED: REQUIREMENTS.md SRCH-01, SRCH-02; CITED: https://ai.google.dev/gemini-api/docs/models] |
| PyJWT | Existing stack | Short-lived internal capability credential for the worker boundary | Requirement AGNT-05 already calls for audience-bound capability credentials; existing JWT infrastructure is the most maintainable path. [VERIFIED: backend/pyproject.toml; REQUIREMENTS.md AGNT-05] |

### Supporting

| Library / Tool | Version | Purpose | When to Use |
|---|---:|---|---|
| HTTPX | `>=0.28,<1` | Integration tests and any bounded provider probes | Reuse for backend integration/security tests around search routing and failure states. [VERIFIED: backend/pyproject.toml] |
| pytest + pytest-asyncio | Existing stack | Search contract, grounding, timeout, prompt-injection, and authz tests | Primary backend verification path for Phase 3. [VERIFIED: backend/pyproject.toml] |
| Frontend `tsx --test` | Existing stack | Client-state, rendering, retry, and suggestion-prefill tests | Existing frontend already uses this test runner; extend it for chat/search state. [VERIFIED: frontend/package.json; frontend/tests/*.ts] |
| OpenTelemetry / Phoenix / Promptfoo | Introduce only in dedicated eval work | Optional tracing and eval regression aligned with AI-SPEC | Useful for Phase 3 evaluation and observability, but not required to land the first functional search slice. [VERIFIED: 03-AI-SPEC.md] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|---|---|---|
| Dedicated ADK worker | Call Gemini Search directly from ordinary application code | Simpler initially, but conflicts with SRCH-01 and the approved AI contract. Use ADK only for the dedicated search worker. |
| Reuse the user's bearer token internally | Forward the access token to the worker/service | Violates AGNT-05 and couples tool authorization to user credentials. Use a short-lived internal capability credential instead. |
| Let the worker choose whether to search | Single prompt path that conditionally decides tool usage | Violates AGNT-01 and AGNT-02 because the model becomes the policy router. Keep routing deterministic in FastAPI. |
| One agent containing Search and Python | Multi-tool ADK agent | Violates the separate worker boundary and increases prompt-injection blast radius. Keep search isolated. |
| Store rendered Search Suggestions inside markdown content | Blend provider HTML into user-visible markdown | Breaks the approved UI safety model and creates XSS/policy risk. Render a dedicated trusted suggestion block. |
| Persist every raw grounding field forever | Full raw provider payload retention | Overcollects data and may violate SRCH-05. Store only the minimum allowlisted fields needed for UI and audit. |

## Package Legitimacy Audit

| Package / Surface | Current Repo State | Phase 3 Decision |
|---|---|---|
| `google-adk` | Not installed yet | Add intentionally for the dedicated search worker only. |
| `google-genai` | Already present | Reuse for capability probes and typed provider interaction. |
| OpenAI-compatible normal chat path | Not yet visible in repository | Preserve as a separate adapter boundary; do not collapse it into the Google worker. |
| Frontend local component system | Already present | Reuse and extend; no shadcn initialization for this phase. |

## Architecture Patterns

### Pattern 1: Explicit Per-Turn Routing State Machine

Use one typed request enum for the submitted turn mode, for example `direct_chat | google_search`. The client may request `google_search`, but the backend is still allowed to return one of these execution states:

- `grounded`
- `missing_grounding`
- `denied`
- `search_unavailable`
- `provider_failed`
- `timeout`

The route should never accept a generic free-form "tool name" string from the browser. The coordinator owns the explicit allowlist (`direct chat`, `Google Search`, and later `Python`) and rejects anything outside it. This satisfies AGNT-01 and makes one-invocation-per-turn enforcement straightforward. [VERIFIED: REQUIREMENTS.md AGNT-01 through AGNT-03; 03-UI-SPEC.md]

### Pattern 2: Dedicated Search Worker Boundary

Create a dedicated backend search worker module, for example:

```text
backend/app/ai/search_worker/
  agent.py
  grounding.py
  schemas.py
  service.py
```

That worker should:

- use Google ADK only for Google Search;
- attach only the Google Search tool;
- expose a typed output schema back to the coordinator;
- never perform authorization or budget decisions;
- never own frontend copy or persistence policy.

The worker should not share an agent object with Python execution or arbitrary custom tools. Even if future ADK releases relax some tool constraints, the project's security model still benefits from a single-purpose boundary. [VERIFIED: 03-AI-SPEC.md; CITED: https://google.github.io/adk-docs/docs/tools/limitations/]

### Pattern 3: Short-Lived Internal Capability Credential

The worker boundary must not receive the user's bearer token. Reuse the current JWT primitives to mint an internal capability credential with:

- a dedicated audience such as `simpagent-search-worker`;
- a TTL measured in seconds, not minutes;
- explicit `tool=google_search`;
- conversation and correlation identifiers;
- no reusable end-user scopes beyond the single approved action.

The coordinator validates the user and policy first, then mints the capability, invokes the worker, and discards the capability after the call. This is the cleanest way to satisfy AGNT-05 without introducing a second unrelated credential system. [VERIFIED: REQUIREMENTS.md AGNT-05; backend/app/security/access_tokens.py]

### Pattern 4: Grounding Normalization and Persistence Contract

Use the existing durable seams instead of inventing new tables first:

- `messages.metadata` for user-visible search outcome details;
- `tool_executions` for the correlated execution lifecycle.

Recommended normalized message metadata shape:

```text
metadata.search = {
  mode: "google_search",
  state: "grounded|missing_grounding|denied|search_unavailable|provider_failed|timeout",
  google_grounded: true|false,
  correlation_id: "...",
  sources: [{ index, title, domain, uri }],
  citations: [{ index, source_index, start, end }],
  web_search_queries: [...],
  suggestions: { trusted: true, items: [...] },
  retry_of_message_id: "..." | null
}
```

Rules:

- `sources` should already be normalized to the UI contract's `title + domain` display model.
- `suggestions` must stay outside markdown content.
- `missing_grounding` stores no grounded badge/citation payload.
- `denied` stores `tool_executed=false`.
- If raw grounding metadata is retained for audit, keep it under a separate allowlisted key and gate it by SRCH-05's implementation-time terms review.

`tool_executions` should record the lifecycle transition and duration regardless of whether the user-facing answer succeeded. [VERIFIED: backend/app/models/domain.py; REQUIREMENTS.md AGNT-06, SRCH-05]

### Pattern 5: Frontend Rendering Contract for Grounded and Degraded Search

The UI contract is specific enough that backend planning should conform to it rather than reinterpret it:

- `Google-grounded` badge only on real grounded turns;
- inline numeric citation markers linked to a source row in the same assistant message;
- source list with `title + domain` only;
- separate Search Suggestions block rendered from trusted provider fields;
- missing-grounding note `có thể tham khảo` with no evidence treatment;
- denied/unavailable/provider-failed/timeout states visibly distinct.

Implementation should therefore create search-specific rendering components rather than trying to overload one generic markdown renderer with conditional fragments. The current repo already has the right style analogs in `ActionButton`, `InlineAlert`, `StatusBadge`, and `AuthModeSwitch`. [VERIFIED: 03-UI-SPEC.md; frontend/components/account-access/*.tsx]

### Pattern 6: Provider Readiness and Capability Check

The current `search_status()` helper only distinguishes `unconfigured` and `ready`. That is insufficient for Phase 3 because the phase explicitly needs to distinguish:

- no configured search credentials/model;
- configured but unsupported/unavailable model;
- provider error/timeout at runtime;
- successful configuration with expected grounding metadata.

Plan a capability-check adapter that runs at startup or deployment check time and validates:

1. Google API credentials are present.
2. The configured Gemini 2 search model is callable.
3. The model supports Google Search grounding for this deployment path.
4. The returned payload includes the metadata shape the UI and persistence layer expect.

Do not treat a configured `search_model` string as proof of support. [VERIFIED: backend/app/core/config.py; backend/app/core/provider_status.py; REQUIREMENTS.md SRCH-01, SRCH-02]

### Pattern 7: Budgets, Timeouts, and Retry Discipline

The correct Phase 3 retry model is asymmetric:

- the coordinator may retry only schema-validation or similarly bounded internal parsing failures;
- the backend should not silently issue a second Google Search after a provider/runtime failure;
- the user-visible retry is explicit and bound to the failed assistant turn.

Recommended budgets for planning:

- one tool invocation per turn;
- bounded input size from the submitted prompt plus a short coordinator-authored context summary;
- worker timeout under the interactive UI budget;
- explicit output token cap;
- per-user/day or per-conversation search budget hooks, even if the first implementation uses only simple counters.

The retry button updates the same failed assistant slot instead of duplicating the user message. [VERIFIED: REQUIREMENTS.md AGNT-03, SRCH-06; 03-UI-SPEC.md]

### Pattern 8: Prompt-Injection and SSRF Defense

Search content is untrusted data. The worker and coordinator must never:

- fetch URLs mentioned in search results or answer text;
- obey instructions inside retrieved pages to reveal secrets or change policy;
- open arbitrary tools because a result suggested it;
- pass internal URLs, bearer tokens, or environment details into the prompt.

At plan level this means:

- keep the worker prompt minimal and role-like;
- keep all policy outside model control;
- never pipe `searchEntryPoint.renderedContent` back into model context;
- add negative tests specifically for prompt-injection text, internal-URL lures, and tool-chaining attempts.

This is a first-order Phase 3 requirement, not a "nice to have" security hardening task. [VERIFIED: REQUIREMENTS.md AGNT-07, SRCH-08]

### Pattern 9: Repository-Realistic Incrementalism

The repository currently has no conversation routes or chat UI. Planning should therefore split work so that:

- backend search contracts can land on top of existing auth/session/persistence seams;
- frontend search UI work can either extend the future Phase 2 shell or create the minimum shell defined in the UI-SPEC when that shell is absent;
- validation does not assume a full Phase 2 product already exists in the current branch.

This is the main reason to prefer vertical slices over horizontal "backend first, then all frontend, then all tests" planning for this phase. [VERIFIED: backend/app/api/routes; frontend/app; frontend/components; ROADMAP.md Phase 3]

## Implementation Order

1. **Lock the backend contract first.** Add the search route/request schema, normalized response-state enum, capability-token design, and RED tests for authorization, grounding states, and persistence semantics.
2. **Land the worker boundary and capability check next.** Add `google-adk`, the dedicated worker module, provider/model capability probing, and the metadata normalizer.
3. **Wire durable evidence and state transitions.** Extend `messages.metadata`, `tool_executions`, and any repositories/services needed for correlated search state.
4. **Add the frontend search shell and rendering surfaces.** Implement the explicit mode switch, grounded/degraded assistant cards, source list, Search Suggestions block, retry behavior, and minimal chat shell fallback if the Phase 2 shell is absent.
5. **Close the security and evaluation loop last.** Add prompt-injection, timeout, unavailable, and missing-grounding tests; ensure the final state matrix matches the UI-SPEC and AI-SPEC contracts.

## Don't Hand-Roll

- Do not invent a second, ad hoc internal credential format when existing JWT primitives already satisfy AGNT-05.
- Do not design a custom HTML sanitizer for Search Suggestions. Keep them in a dedicated trusted rendering path and avoid markdown HTML injection entirely.
- Do not create a generic tool orchestration framework in this phase. The explicit allowlist is enough.
- Do not build a separate search index, crawler, or scraper. Gemini-grounded Google Search is the selected path.

## Common Pitfalls

### Pitfall 1: A grounded badge is shown whenever search ran

This is wrong. `grounded` and `missing_grounding` are different product states. If evidence is absent, the turn must downgrade to ordinary assistant styling plus the `có thể tham khảo` note. [VERIFIED: 03-UI-SPEC.md]

### Pitfall 2: The worker receives the user's bearer token

This violates AGNT-05 and widens blast radius if logs or model context leak. Use a short-lived internal capability credential instead. [VERIFIED: REQUIREMENTS.md AGNT-05]

### Pitfall 3: Search Suggestions are merged into markdown content

This breaks the approved rendering model and creates avoidable XSS/trust confusion. Render them in a dedicated trusted component only. [VERIFIED: 03-UI-SPEC.md]

### Pitfall 4: Search unavailability is treated as the same thing as denial

`denied` means policy blocked the action and no search executed. `search_unavailable` means search was permitted but the capability was not available. The UI and persistence layer must preserve that distinction. [VERIFIED: 03-CONTEXT.md; 03-UI-SPEC.md]

### Pitfall 5: The plan assumes the Phase 2 chat shell already exists

It does not exist in the current repository. If the implementation branch is still missing it, Phase 3 must build the minimum shell required by the UI-SPEC rather than blocking on a nonexistent abstraction. [VERIFIED: frontend/app; frontend/components; 03-UI-SPEC.md]

### Pitfall 6: The worker is allowed to mix Search and Python

Even if that looks efficient, it collapses the very security boundary Phase 3 exists to demonstrate. Keep them separate. [VERIFIED: REQUIREMENTS.md AGNT-04; 03-AI-SPEC.md]

### Pitfall 7: The route stores every raw grounding field forever

SRCH-05 is specifically about retaining only fields allowed by current Google terms. Treat field persistence as an allowlist decision with an implementation-time terms checkpoint, not as "save everything and filter later." [VERIFIED: REQUIREMENTS.md SRCH-05]

### Pitfall 8: Frontend retry creates a second user turn

The approved UX updates the failed assistant slot in place. Duplicate user turns make correlation, history, and idempotency harder than necessary. [VERIFIED: 03-UI-SPEC.md]

### Pitfall 9: Startup only checks whether `search_model` is non-empty

That proves configuration exists, not that the model supports grounded Google Search with the expected metadata shape. Capability probing is mandatory for SRCH-02. [VERIFIED: backend/app/core/provider_status.py; REQUIREMENTS.md SRCH-02]

## Validation Architecture

Phase 3 needs both backend and frontend evidence. The minimal validation portfolio should include:

- backend integration tests for search route success, denial, unavailability, timeout, missing grounding, and persisted state transitions;
- backend security tests for prompt injection, internal-URL lure, no bearer-token forwarding, and one-tool-per-turn enforcement;
- frontend tests for explicit mode switching, grounded/degraded rendering, suggestion prefill without auto-run, retry updating the same failed turn, and no evidence UI on missing grounding;
- a compose-level smoke path that proves the end user can submit a grounded search request through the full topology.

This section is intentionally strong enough to justify `03-VALIDATION.md` and keep Nyquist validation enabled for the phase. [VERIFIED: backend/pyproject.toml; frontend/package.json; 03-AI-SPEC.md; 03-UI-SPEC.md]

## Security Domain

### Applicable Threat Patterns

- **Spoofing:** forged internal capability credentials or mis-bound worker audience.
- **Tampering:** altered grounded-state metadata, duplicate retry mutation, or mixed search/Python boundaries.
- **Repudiation:** missing `tool_executions` rows or missing correlation IDs on denied/failed search.
- **Information Disclosure:** raw provider payloads, secrets in prompts/logs, source-link click tracking, or unsafe suggestion rendering.
- **Denial of Service:** repeated search retries, oversized prompts, or unbounded provider timeouts.
- **Elevation of Privilege:** model output or search content overriding policy and triggering unauthorized tools.

### Blocking Security Expectations

- Search routes must prove `tool:websearch` denial before any provider call.
- Worker prompts and traces must not contain bearer tokens, refresh tokens, or internal secrets.
- Search content must not trigger internal URL fetching or second-tool execution.
- Grounded/degraded state must remain honest under provider errors and prompt-injection text.

## Assumptions Log

- Phase 2 will eventually provide the durable conversation and ordinary chat path required by the roadmap, but Phase 3 plans may need to build a minimum compatible shell if those artifacts are still absent in the implementation branch.
- The internal capability boundary can reuse the existing backend JWT/security stack without introducing a second credential store.
- The team will accept a configuration-driven Gemini 2 model strategy with a startup probe instead of locking one model identifier into every code path.

## Open Questions (RESOLVED FOR PLANNING)

1. **Should the top-level coordinator be built in ADK too?** No. The approved AI contract keeps the coordinator hand-written and typed in FastAPI.
2. **Should search and Python share one worker?** No. Requirements and AI-SPEC both require separate bounded workers.
3. **Can Search Suggestions auto-run?** No. The approved UI contract explicitly forbids auto-run and requires composer prefill only.
4. **Should the frontend use shadcn?** No. The user explicitly chose to keep the local component system.

## Environment Availability

- `backend/pyproject.toml` already contains `google-genai` but not `google-adk`.
- The backend already exposes `SIMPAGENT_GOOGLE_API_KEY(_FILE)` and `SIMPAGENT_SEARCH_MODEL`.
- The repository currently exposes only account-access routes and components; chat/search routes and components are not present yet.
- Git commits for planning artifacts currently fail until `git config user.name` and `git config user.email` are set in this repository or globally.

## Sources

### Primary (HIGH confidence)

- `AGENTS.md`
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/STATE.md`
- `.planning/phases/03-policy-controlled-google-search/03-CONTEXT.md`
- `.planning/phases/03-policy-controlled-google-search/03-AI-SPEC.md`
- `.planning/phases/03-policy-controlled-google-search/03-UI-SPEC.md`
- `backend/app/authorization/policy.py`
- `backend/app/core/config.py`
- `backend/app/core/provider_status.py`
- `backend/app/models/domain.py`
- `backend/app/api/routes/auth.py`
- `backend/app/services/authentication.py`
- `backend/app/services/registration.py`
- `frontend/lib/auth-session.ts`
- `frontend/lib/readiness.ts`
- `frontend/components/account-access/*.tsx`

### Official External Docs (implementation-time verification points)

- https://ai.google.dev/gemini-api/docs/google-search
- https://ai.google.dev/gemini-api/docs/models
- https://google.github.io/adk-docs/docs/get-started/python/
- https://google.github.io/adk-docs/docs/integrations/google-search/
- https://google.github.io/adk-docs/docs/tools/limitations/
- https://pypi.org/project/google-adk/

### Secondary (MEDIUM confidence)

- `03-AI-SPEC.md` evaluation/tooling guidance for Phoenix and Promptfoo
- Current Google public examples and model pages, which should be treated as moving references rather than immutable build-time truth

## Metadata

- **Research date:** 2026-06-11
- **Planner impact:** Strongly reduces ambiguity for the worker boundary, persistence shape, UI rendering split, and negative-test matrix
- **Expected downstream artifacts:** `03-VALIDATION.md`, `03-PATTERNS.md`, and 3-4 vertical-slice `03-0X-PLAN.md` files
