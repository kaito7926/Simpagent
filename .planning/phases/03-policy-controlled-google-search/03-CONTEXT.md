# Phase 3: Policy-Controlled Google Search - Context

**Gathered:** 2026-06-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a bounded Google-grounded search path for authorized users inside the chatbot flow: execution-time scope/policy enforcement, distinct grounded-result presentation, safe handling of Google Search Suggestions, and explicit denied/degraded/timeout/missing-grounding outcomes. This phase clarifies how search results behave in the conversation and how they remain distinguishable from normal chat; it does not add Python execution, gateway hardening, or unrelated new product capabilities.

</domain>

<decisions>
## Implementation Decisions

### Grounded Answer Presentation
- **D-01:** Successful grounded search responses render inline citation markers inside the assistant answer text.
- **D-02:** Each grounded response renders a separate source list below the answer with source `title + domain` only. Do not show snippets or full passages in the default list.
- **D-03:** Required Google Search Suggestions render in a dedicated block separate from the answer Markdown and separate from the source list.
- **D-04:** Clicking a Search Suggestion pre-fills the composer and waits for explicit user submission. Suggestion clicks must not auto-run a new search turn.
- **D-05:** Successful grounded search responses display a compact `Google-grounded` badge on the assistant response.

### Failure and Fallback Behavior
- **D-06:** If Google Search is denied by missing `tool:websearch` scope or coordinator policy, the conversation must show a visible tool-denied response that clearly states search was blocked and no search was executed.
- **D-07:** If the search worker returns answer text without the required grounding metadata, render it as a normal assistant response with no citations, no `Google-grounded` badge, and no Search Suggestions. Add a note that the response is `có thể tham khảo` because the output is spontaneous and the source is unclear.
- **D-08:** If Gemini/search capability is unavailable or the search worker times out completely, show a search-specific error that asks the user to retry or switch to a normal question.
- **D-09:** Search unavailable and timeout failures render inline in the conversation with a `Thử lại tìm kiếm` retry control attached to that turn.

### the agent's Discretion
- Choose the exact trigger contract for when a user turn enters the Google Search path versus normal direct chat, as long as search remains explicit, policy-enforced, and visibly distinct from ordinary assistant answers.
- Choose how much search execution trace to expose in conversation history beyond the locked badge, citations, source list, and Search Suggestions behavior.
- Choose the precise copy, iconography, and component structure for denied, degraded, and retry states while preserving the distinctions locked above.
- Choose capability-check mechanics, grounding-metadata persistence shape, audit/event fields, and coordinator request/output/retry/time/cost budgets consistent with `AUTHZ-04`, `AUTHZ-07`, `AGNT-*`, and `SRCH-*` requirements.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and Requirements
- `.planning/ROADMAP.md` - Defines the Phase 3 boundary, dependency on Phase 2, and the five success criteria for policy-controlled Google Search.
- `.planning/REQUIREMENTS.md` - Defines `AUTHZ-04`, `AUTHZ-07`, `AGNT-01` through `AGNT-07`, `SRCH-01` through `SRCH-08`, and the project-wide acceptance criteria that Phase 3 must satisfy.
- `.planning/PROJECT.md` - Defines the core security value, Gemini/Google ADK constraints, grounding retention expectations, and the requirement to keep search and Python behind separate bounded workers.
- `.planning/STATE.md` - Records the project position and flags the standing concern to revalidate Gemini 2 availability, ADK grounding behavior, and Google retention terms before implementation.

### Prior Decisions
- `.planning/phases/01-secure-platform-and-account-access/01-CONTEXT.md` - Carries forward that standard users receive `tool:websearch` by default and that tool access must still be rechecked immediately before execution.

### Original Brief and Local Guidance
- `prompt.md` - Original project brief, required secure-tool architecture, grounding expectations, and local Compose delivery shape.
- `AGENTS.md` - Project stack, security constraints, and workflow guidance that implementation agents must continue to follow.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/authorization/policy.py` - Already defines `tool:websearch` and the shared scope-evaluation helper used for execution-time authorization checks.
- `backend/app/core/config.py` - Already exposes `search_model`, Google credential loading, and provider timeout settings that Phase 3 can extend into capability checks and search-worker configuration.
- `backend/app/core/provider_status.py` - Already models search readiness separately from chat and sandbox, giving Phase 3 a place to surface search-specific degraded or unavailable states.
- `backend/app/models/domain.py` - `Message.message_metadata` and `ToolExecution` already provide storage seams for grounding metadata, response labels, failure states, and correlated tool records.
- `frontend/lib/auth-session.ts` and `frontend/lib/readiness.ts` - Already model session restoration, search readiness, and degraded-state UI behavior that search features can plug into.

### Established Patterns
- FastAPI remains authoritative for authorization and tool policy even if model output or frontend interactions suggest search.
- Search, direct chat, and Python are separate surfaces and must remain distinguishable in UI, persistence, and audit state.
- The existing frontend uses compact badges, status labels, and inline alerts rather than heavy banners for state communication.
- Provider readiness is already a first-class UI concept, so search unavailability should fit the same explicit readiness/degraded-state model.

### Integration Points
- Search execution will connect to the existing principal, scope, and session machinery before any worker call is made.
- Grounded answers, denied executions, degraded fallbacks, and retry affordances should persist through `messages.metadata` and `tool_executions` so later phases can audit and render them consistently.
- The current repository has account-access UI but no conversation/composer components yet, so grounded-response rendering, citation markers, Search Suggestions, and inline retry controls will require new chat-facing UI that still respects the established auth-session and readiness helpers.

</code_context>

<specifics>
## Specific Ideas

- Missing-grounding fallback copy should explicitly signal tentative trust with the note `có thể tham khảo` because the result is spontaneous and source attribution is unclear.
- Search Suggestions must remain an explicit-intent aid only: populate the composer, let the user review, then require manual submit.

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope.

</deferred>

---

*Phase: 3-policy-controlled-google-search*
*Context gathered: 2026-06-11*
