---
phase: 02-private-direct-chat
plan: "04"
subsystem: ui
tags: [nextjs, react, typescript, chat, auth-session, responsive-ui]
requires:
  - phase: 02-03
    provides: durable owner-scoped direct-chat send, retry, pending, and failed-turn APIs
provides:
  - Authenticated chat-first browser workspace with responsive conversation navigation
  - Typed chat API helpers routed exclusively through AuthSessionController.authorizedJson
  - Composer-first create, active-thread send, reload, pending, failed, retry, and session-expiry states
affects: [02-05, 02-06, 02-07, 03-policy-controlled-google-search]
tech-stack:
  added: []
  patterns: [memory-only authenticated chat client, optimistic pending row with durable failure reload, responsive sidebar and mobile drawer]
key-files:
  created:
    - frontend/lib/chat-types.ts
    - frontend/lib/chat-api.ts
    - frontend/components/chat/ChatWorkspace.tsx
    - frontend/components/chat/ChatThread.tsx
    - frontend/components/chat/ChatComposer.tsx
    - frontend/components/chat/MessageList.tsx
    - frontend/components/chat/AssistantStateRows.tsx
  modified:
    - frontend/components/account-access/AccountAccessShell.tsx
    - frontend/lib/auth-session.ts
    - frontend/app/globals.css
    - frontend/app/layout.tsx
key-decisions:
  - "All chat API helpers receive AuthSessionController and use authorizedJson, preserving memory-only access tokens and refresh-on-401 behavior."
  - "The browser shows an optimistic pending assistant row during the non-streaming request, then reloads durable history after provider failure."
  - "Authenticated sessions replace the account card in place with the chat workspace; anonymous and recovery states remain on the root route."
patterns-established:
  - "Chat mutations generate one crypto.randomUUID client_message_id per submit and reuse the persisted ID for retry."
  - "Provider failure UI displays only safe fixed copy and a correlation reference loaded from persisted message metadata."
requirements-completed: [CHAT-01, CHAT-03, CHAT-05, CHAT-07, CHAT-09, CHAT-11]
duration: 17 min
completed: 2026-06-12
---

# Phase 02 Plan 04: Authenticated Chat Workspace Summary

**Responsive chat-first workspace with authorized session routing, composer-first creation, durable reload, and inline pending or retryable failure states**

## Performance

- **Duration:** 17 min
- **Started:** 2026-06-12T09:14:41Z
- **Completed:** 2026-06-12T09:31:13Z
- **Tasks:** 2
- **Files modified:** 30

## Accomplishments

- Replaced the authenticated account panel with a usable SimpAgent chat workspace on the root route.
- Added typed list, detail, create-with-message, send, and retry helpers that all pass through the existing session controller.
- Implemented exact English empty, loading, pending, failed, retry, session-ended, and reload copy with responsive desktop and mobile navigation.
- Preserved the backend-owned provider boundary with no model, provider, tool, upload, voice, citation, or streaming controls.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create RED chat workspace and session-routing tests** - `a6f50b0` (test)
2. **Task 2: Implement authenticated chat-first browser workspace** - `8b171cb` (feat)

**Plan metadata:** this docs commit

## Files Created/Modified

- `frontend/lib/chat-types.ts` - Defines conversation, message, status, page, and input DTOs.
- `frontend/lib/chat-api.ts` - Provides authorized chat API helpers without a local token-storage path.
- `frontend/components/chat/ChatWorkspace.tsx` - Owns conversation navigation, send/retry state, reload recovery, and session routing.
- `frontend/components/chat/ChatThread.tsx` - Renders composer-first empty and active thread states.
- `frontend/components/chat/ChatComposer.tsx` - Implements exact composer copy, keyboard behavior, validation, and pending lockout.
- `frontend/components/chat/MessageList.tsx` - Renders ordered user and assistant message surfaces.
- `frontend/components/chat/AssistantStateRows.tsx` - Renders safe pending and failed assistant rows with retry and reference code.
- `frontend/components/account-access/AccountAccessShell.tsx` - Routes authenticated sessions into ChatWorkspace and retains account recovery flows.
- `frontend/app/globals.css` - Adds warm neutral/coral responsive workspace, drawer, thread, state-row, and composer styling.
- `frontend/app/layout.tsx` - Changes browser language and metadata to English chat product copy.

## Decisions Made

- Used the existing client-side session controller rather than introducing a second auth or token abstraction.
- Kept the non-streaming request path but rendered an immediate optimistic pending row so users understand the in-flight state.
- Reloaded the persisted conversation after provider errors so failed assistant metadata remains the source of truth for retry and correlation display.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Translated shared account and readiness surfaces**
- **Found during:** Task 2
- **Issue:** The plan required an English Phase 2 browser surface, but several shared Phase 1 account, readiness, API fallback, and session messages remained Vietnamese outside the listed file set.
- **Fix:** Translated the reusable visible copy and updated the corresponding prior tests while preserving security semantics.
- **Files modified:** `frontend/components/account-access/*`, `frontend/lib/api.ts`, `frontend/lib/auth-session.ts`, `frontend/lib/readiness.ts`, `frontend/tests/auth-session.test.ts`, `frontend/tests/readiness.test.ts`, `frontend/app/layout.tsx`
- **Verification:** Full frontend suite passed with 15 tests; the root layout now declares `lang="en"`.
- **Committed in:** `8b171cb`

**2. [Rule 3 - Blocking] Added SSR test runtime and type support**
- **Found during:** Task 2 GREEN verification
- **Issue:** The repository's `tsx` SSR tests used the classic React transform and lacked a `react-dom/server` declaration, causing runtime and typecheck failures.
- **Fix:** Added explicit React imports to rendered components and a narrow local declaration for `renderToStaticMarkup` without adding a dependency.
- **Files modified:** rendered account/chat components, `frontend/types/react-dom-server.d.ts`
- **Verification:** Focused chat tests, full frontend tests, typecheck, and Next.js production build passed.
- **Committed in:** `8b171cb`

**3. [Rule 1 - Bug] Corrected the RED test's absent-localStorage assertion**
- **Found during:** Task 2 GREEN verification
- **Issue:** Node has no `localStorage`, so optional access returned `undefined` while the test incorrectly required `null`.
- **Fix:** Normalized the absent value to `null`; the assertion still proves no access token was written.
- **Files modified:** `frontend/tests/chat-workspace.test.ts`
- **Verification:** The first-submit authorization test passed and source scans found no chat `localStorage` or `sessionStorage` path.
- **Committed in:** `8b171cb`

**4. [Rule 1 - Bug] Rendered the usable empty state before hydration**
- **Found during:** Task 2 GREEN verification
- **Issue:** Initial server markup showed only the conversation loading label, violating the composer-first first-screen contract.
- **Fix:** Server rendering now shows `No conversations yet` and the active composer; the client effect owns subsequent list loading.
- **Files modified:** `frontend/components/chat/ChatWorkspace.tsx`
- **Verification:** Exact empty-workspace SSR test passed.
- **Committed in:** `8b171cb`

**5. [Rule 1 - Bug] Corrected inconsistent generated progress state**
- **Found during:** Plan closeout
- **Issue:** The state SDK returned 80% but wrote 17% in frontmatter and left the visible progress line and last activity stale.
- **Fix:** Reconciled STATE.md to 12/15 completed plans, 80%, Plan 05 current position, and Plan 04 last activity.
- **Files modified:** `.planning/STATE.md`
- **Verification:** State now consistently reports Plan 5 of 7 and 80% progress.
- **Committed in:** plan metadata commit

---

**Total deviations:** 5 auto-fixed (4 bugs/blockers, 1 missing critical contract completion).
**Impact on plan:** Changes were limited to correctness, testability, and the required English browser experience; no product scope or provider controls were added.

## Issues Encountered

- Docker Compose continued to report a pre-existing orphan `simpagent-postgres-test-1` container. It was not removed and did not affect verification.
- The frontend image copies source at build time, so it was rebuilt before each container verification cycle.

## User Setup Required

None - no new packages, environment variables, provider settings, or external services were added.

## Known Stubs

None. Empty state values are intentional UI/session defaults with active data sources and recovery paths.

## Verification

- Focused frontend: `docker compose run --rm frontend npm run test -- tests/chat-workspace.test.ts tests/chat-session-routing.test.ts` passed with `5 passed`.
- Full frontend: `docker compose run --rm frontend npm run test` passed with `15 passed`.
- TypeScript: `docker compose run --rm frontend npm run typecheck` passed.
- Production build: `docker compose run --rm frontend npm run build` compiled and generated the root route successfully.
- Backend regression: `docker compose run --rm backend pytest -q tests/integration/chat/test_message_send.py tests/security/test_chat_provider_failure.py -x` passed with `8 passed`.
- Security scan: chat helpers contain five `authorizedJson` call sites and no `localStorage`, `sessionStorage`, raw HTML, host execution, or embedded credential path.

## Next Phase Readiness

Ready for Plan 02-05 to add the dedicated safe Markdown and code rendering pipeline inside completed assistant messages.

## Self-Check: PASSED

- All key created files and the summary exist on disk.
- Task commits `a6f50b0` and `8b171cb` exist in git history.
- Focused and full frontend tests, typecheck, production build, and the backend regression subset passed.
- Stub and threat-surface scans found no unresolved blocker.

---
*Phase: 02-private-direct-chat*
*Completed: 2026-06-12*
