# Phase 3: Policy-Controlled Google Search - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-06-11
**Phase:** 3-Policy-Controlled Google Search
**Areas discussed:** Grounded answer presentation, Failure and fallback behavior

---

## Grounded answer presentation

### How should a grounded search answer appear in chat?

| Option | Description | Selected |
|--------|-------------|----------|
| Inline citations + source list + suggestions block | Keep citations tied to claims, show a separate list of sources below, and keep trusted Google suggestions in a distinct block. | ✓ |
| Source list only | Simpler layout, but weaker claim-to-source linkage inside the answer text. | |
| Dedicated grounded-result card | Strong separation from normal assistant messages, but adds a second response pattern to the chat UI. | |

**User's choice:** Show inline citation markers in the answer, a source list below, and a separate Search Suggestions block.
**Notes:** This locks the success-state structure for grounded responses.

### When a user clicks a Google Search Suggestion, what should happen?

| Option | Description | Selected |
|--------|-------------|----------|
| Fill composer, wait for submit | Preserve explicit user intent and keep search execution tied to a deliberate send action. | ✓ |
| Auto-run a new grounded-search turn | Faster, but creates an implicit tool-execution path from one click. | |
| Ask for confirmation before running | Adds safety, but introduces a new confirmation flow. | |

**User's choice:** Clicking a suggestion fills the composer and waits for manual submit.
**Notes:** Suggestions are an assistive input, not an execution trigger.

### How much detail should each cited source show under the answer?

| Option | Description | Selected |
|--------|-------------|----------|
| Title + domain only | Keep the list compact and easy to scan. | ✓ |
| Title + domain + snippet | Helps inspect grounding quickly, but adds more visual weight and persisted display data. | |
| Title + domain + full passage | Too heavy for chat and risks overwhelming the response surface. | |

**User's choice:** Show source title and domain only.
**Notes:** Source snippets and full passages are intentionally excluded from the default UI.

### How explicitly should the UI mark that this was a Google-grounded answer?

| Option | Description | Selected |
|--------|-------------|----------|
| Compact `Google-grounded` badge | Makes grounded vs normal responses obvious while fitting existing compact status patterns. | ✓ |
| Rely on citations and suggestions only | Simpler, but less obvious at a glance. | |
| Prominent banner | Very explicit, but visually heavier than current UI patterns. | |

**User's choice:** Add a compact `Google-grounded` badge on the assistant response.
**Notes:** The badge is part of the required success-state distinction between grounded and ordinary answers.

---

## Failure and fallback behavior

### If search is denied by scope or coordinator policy, what should the chat show?

| Option | Description | Selected |
|--------|-------------|----------|
| Visible tool-denied response | Tell the user search was blocked by policy and that no search was run. | ✓ |
| Generic request error | Hide the policy reason behind a generic failure. | |
| Fall back to direct LLM answer | Smoother UX, but weakens the explicit tool-control boundary. | |

**User's choice:** Show a visible tool-denied response in the conversation and make clear that no search was run.
**Notes:** Denied tool execution should be explicit and fail closed.

### If answer text is returned without required grounding metadata, what should the app do?

| Option | Description | Selected |
|--------|-------------|----------|
| Distinct grounding-unavailable failure | Refuse to show the text as a grounded result. | |
| Show as normal assistant answer without citations | Treat it as ordinary assistant output, not a grounded result. | ✓ |
| Retry once, then degrade | Add resilience before falling back to a degraded state. | |

**User's choice:** Show it as a normal assistant response without citations.
**Notes:** Also remove the grounded badge and Search Suggestions, and add the note `có thể tham khảo` because the result is spontaneous and source attribution is unclear.

### If search/Gemini is unavailable or the worker times out completely, how should the response behave?

| Option | Description | Selected |
|--------|-------------|----------|
| Search-specific error | Tell the user search is unavailable and suggest retrying or switching to a normal question. | ✓ |
| Automatic fallback to direct chat | Continue smoothly, but blur the line between searched and unsearched answers. | |
| Ask before switching to normal chat | More explicit, but adds a confirmation step. | |

**User's choice:** Show a search-specific error and tell the user to retry or switch to a normal question.
**Notes:** Search capability failures stay visibly distinct from direct-chat outcomes.

### For search unavailable or timeout errors, how should the app let the user retry?

| Option | Description | Selected |
|--------|-------------|----------|
| Inline retry button | Keep the failure and retry action attached to the same conversation turn. | ✓ |
| User retypes manually | Simplest implementation, but slower and easier to abandon. | |
| Automatic backend retry | Hides complexity from the user, but obscures tool-execution behavior. | |

**User's choice:** Show the error inline in the conversation with a `Thử lại tìm kiếm` button.
**Notes:** Retry remains user-driven and local to the failed turn.

---

## the agent's Discretion

- Search trigger model for entering the Google Search path versus normal direct chat.
- Search trace visibility beyond the locked grounded badge, citations, source list, and Search Suggestions behavior.
- Precise copy, iconography, and component composition for denied, degraded, and retry states.
- Capability-check mechanics, grounding persistence shape, and coordinator budget thresholds.

## Deferred Ideas

None - discussion stayed within phase scope.
