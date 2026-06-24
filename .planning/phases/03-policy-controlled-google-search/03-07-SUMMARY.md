---
phase: 03-policy-controlled-google-search
plan: "07"
subsystem: frontend-search-admin
tags: [nextjs, react, typescript, provider-honest-ui, websearch, admin-orchestration]
requires:
  - phase: 03-06
    provides: admin runtime provider override contract with default, override, effective provider, and readiness fields
  - phase: 03-03
    provides: baseline chat shell, search session controller, grounded rendering, and degraded search state components
provides:
  - provider-aware frontend chat contracts for Gemini and Firecrawl websearch turns
  - provider-honest grounded, missing-grounding, denied, unavailable, failed, and timeout rendering
  - admin settings controls for default, override, effective provider, readiness, set, and clear flows
affects: [phase-03-search, frontend-chat, admin-settings, provider-honest-ux, phase-03-validation]
tech-stack:
  added: []
  patterns:
    - provider metadata is carried through typed frontend view models
    - Google-only suggestions and badges are gated to Gemini grounded turns
    - admin orchestration transport stays snake_case while component state uses camelCase
key-files:
  created: []
  modified:
    - frontend/lib/admin-api.ts
    - frontend/lib/chat-session.ts
    - frontend/components/settings/SettingsPage.tsx
    - frontend/components/chat/ChatWorkspace.tsx
    - frontend/components/chat/ConversationHeader.tsx
    - frontend/components/chat/ToolModeSwitch.tsx
    - frontend/components/chat/GroundedAnswer.tsx
    - frontend/components/chat/SearchFailureCard.tsx
    - frontend/components/chat/AssistantMessageCard.tsx
    - frontend/components/chat/MessageList.tsx
    - frontend/components/chat/SearchSourceList.tsx
    - frontend/components/chat/SearchSuggestionList.tsx
    - frontend/tests/search-session.test.ts
    - frontend/tests/search-rendering.test.tsx
    - frontend/tests/admin-evidence.test.tsx
key-decisions:
  - "Use backend provider metadata as the only source for Gemini versus Firecrawl labels."
  - "Keep Google Search Suggestions and the Google-grounded badge limited to Gemini grounded turns."
  - "Expose provider override controls through the existing Settings orchestration card pattern instead of a new admin surface."
requirements-completed: [SRCH-03, SRCH-04, SRCH-06, SRCH-07]
duration: 13 min
completed: 2026-06-23
---

# Phase 03 Plan 07: Provider-Honest Frontend Search UX Summary

**Provider-aware chat and admin rendering that preserves Gemini evidence UI while keeping Firecrawl labels and failures honest.**

## Performance

- **Duration:** 13 min
- **Started:** 2026-06-23T06:58:32Z
- **Completed:** 2026-06-23T07:11:55Z
- **Tasks:** 2/2
- **Files modified:** 15

## Accomplishments

- Added RED frontend tests for provider metadata, Gemini-only Google evidence affordances, Firecrawl-honest grounded labels, Vietnamese failure copy, and secret-free admin provider controls.
- Extended chat-session transport and assistant view models with `gemini` / `firecrawl` provider metadata.
- Updated grounded, missing-grounding, denied, unavailable, provider-failed, and timeout UI so Firecrawl is never mislabeled as Google-grounded.
- Added admin settings controls for default provider, runtime override, effective provider, readiness, set-to-Gemini, set-to-Firecrawl, and clear-override flows.

## Task Commits

1. **Task 1 RED: Provider-honest frontend expectations** - `a125182` (test)
2. **Task 2 GREEN: Provider-aware frontend contracts and rendering** - `b0b881f` (feat)

## Files Created/Modified

- `frontend/lib/admin-api.ts` - Adds provider fields and the websearch provider override wrapper.
- `frontend/lib/chat-session.ts` - Carries provider metadata through transport normalization and assistant view models.
- `frontend/components/settings/SettingsPage.tsx` - Renders and controls the provider override contract without secret-bearing details.
- `frontend/components/chat/ChatWorkspace.tsx` - Maps admin orchestration provider fields and updates overrides through Settings.
- `frontend/components/chat/GroundedAnswer.tsx`, `SearchFailureCard.tsx`, `ToolModeSwitch.tsx`, and `ConversationHeader.tsx` - Render provider-honest labels and Vietnamese state copy.
- `frontend/components/chat/AssistantMessageCard.tsx`, `MessageList.tsx`, `SearchSourceList.tsx`, and `SearchSuggestionList.tsx` - Ensure persisted chat history uses the same provider-aware evidence rendering.
- `frontend/tests/search-session.test.ts`, `search-rendering.test.tsx`, and `admin-evidence.test.tsx` - Lock the D-13 chat/admin frontend contract.

## Verification

- RED gate: `cd frontend && npm test -- tests/search-session.test.ts tests/search-rendering.test.tsx tests/admin-evidence.test.tsx` - failed as expected on missing provider wrapper, dropped provider metadata, Google-only labels, and missing admin controls.
- Task 2 and plan-level: `cd frontend && npm test -- tests/search-session.test.ts tests/search-rendering.test.tsx tests/admin-evidence.test.tsx && npm run typecheck` - `22 passed`; `tsc --noEmit` passed.

## Decisions Made

- Provider display is metadata-driven. The frontend defaults unknown legacy search metadata to Gemini for backward compatibility, but uses explicit `firecrawl` metadata whenever present.
- Firecrawl grounded turns use `Firecrawl-grounded` and omit Search Suggestions; Gemini grounded turns retain `Google-grounded` and trusted suggestions.
- The admin provider control stays in Settings under the existing orchestration control pattern instead of adding a new admin route or navigation surface.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Wired persisted conversation rendering into provider-aware search cards**
- **Found during:** Task 2
- **Issue:** Updating only `GroundedAnswer` and `SearchFailureCard` would fix controller/render tests while completed chat history in `MessageList` could still render search turns as generic assistant Markdown.
- **Fix:** Added `assistantTurnFromMessage` mapping and routed persisted `message.metadata.search` through `AssistantMessageCard`, plus localized source/suggestion subcomponents.
- **Files modified:** `frontend/lib/chat-session.ts`, `frontend/components/chat/MessageList.tsx`, `frontend/components/chat/AssistantMessageCard.tsx`, `frontend/components/chat/SearchSourceList.tsx`, `frontend/components/chat/SearchSuggestionList.tsx`
- **Verification:** Focused frontend suite and typecheck passed.
- **Committed in:** `b0b881f`

**2. [Rule 2 - Missing Critical] Removed secret-shaped wording from admin helper copy**
- **Found during:** Task 2
- **Issue:** The first provider-control copy used the phrase "secret-free"; the no-secret assertion correctly treated that as secret-shaped UI text.
- **Fix:** Reworded the helper copy to "redacted" while keeping the admin state secret-free by data contract.
- **Files modified:** `frontend/components/settings/SettingsPage.tsx`
- **Verification:** `admin-evidence.test.tsx` no-secret assertion passed.
- **Committed in:** `b0b881f`

---

**Total deviations:** 2 auto-fixed (2 Rule 2).
**Impact on plan:** Both fixes were required for correctness and D-13 security honesty. No new dependency, endpoint, or public tool surface was added.

## Issues Encountered

- Existing planning files already had unrelated Phase 7 changes in the worktree. Metadata staging was kept narrow so this plan does not commit unrelated Phase 7 planning artifacts.

## Known Stubs

None.

## Threat Flags

None - this plan introduced no new network endpoint, auth boundary, schema change, or secret-handling surface.

## User Setup Required

None - no new environment variables or external service configuration were added.

## Next Phase Readiness

Ready for `03-08`: dual-provider smoke and validation can now assert that backend provider selection and frontend provider-honest rendering agree end to end.

## Self-Check: PASSED

- Verified task commits exist: `a125182` and `b0b881f`.
- Verified focused frontend command passed: `22 passed`.
- Verified TypeScript typecheck passed.
- Verified no created source files are missing; this plan modified existing frontend files only.

---
*Phase: 03-policy-controlled-google-search*
*Completed: 2026-06-23*
