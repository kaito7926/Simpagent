---
phase: 02-private-direct-chat
plan: "06"
subsystem: chat-rendering
tags: [nextjs, react, markdown, xss, dependency-audit, docker]
requires:
  - phase: 02-05
    provides: authenticated chat workspace and conversation navigation
provides:
  - Safe assistant Markdown rendering with GFM tables, task lists, and fenced code blocks
  - Inert syntax-highlighted code blocks with copy feedback
  - URL scheme allowlisting and raw HTML inerting for stored assistant content
  - Backend contract coverage proving the API returns raw JSON content, not rendered HTML
affects: [02-07, 03-policy-controlled-google-search]
tech-stack:
  added:
    - react-markdown@10.1.0
    - remark-gfm@4.0.1
    - react-syntax-highlighter@16.1.1
    - "@types/react-syntax-highlighter@15.5.13"
  updated:
    - next@16.2.9
    - next/postcss override to postcss@8.5.10
  patterns:
    - safe client Markdown renderer
    - inert unsafe-link fallback
    - backend raw-content rendering contract
key-files:
  created:
    - frontend/.dockerignore
    - frontend/components/chat/CodeBlock.tsx
    - frontend/components/chat/MessageMarkdown.tsx
    - backend/tests/security/test_chat_rendering_contract.py
  modified:
    - .gitignore
    - frontend/app/globals.css
    - frontend/components/chat/MessageList.tsx
    - frontend/package.json
    - frontend/package-lock.json
    - frontend/tests/chat-markdown.test.ts
key-decisions:
  - "Assistant Markdown is rendered only through a safe client component with no rehype-raw or dangerouslySetInnerHTML."
  - "Raw HTML tags are backslash-escaped before Markdown parsing so they remain visible text and cannot enter HTML-block parsing."
  - "Only http, https, and mailto hrefs become anchors; unsafe and relative hrefs render as inert text."
  - "Next was patched to 16.2.9 and its nested PostCSS was overridden to 8.5.10 to keep npm audit at zero findings."
patterns-established:
  - "MessageList renders assistant completed content through MessageMarkdown while user messages remain plain React text."
  - "CodeBlock owns syntax highlighting and clipboard-only copy behavior; displayed code is never evaluated."
  - "Frontend Docker builds ignore host node_modules, .next, and TypeScript build info."
requirements-completed: [CHAT-03, CHAT-10]
duration: 104 min
completed: 2026-06-12
---

# Phase 02 Plan 06: Safe Markdown and Code Rendering Summary

**Assistant responses now render useful Markdown and inert code without allowing raw HTML, event handlers, unsafe URL schemes, or executable code paths.**

## Performance

- **Duration:** 104 min
- **Started:** 2026-06-12T10:52:00Z
- **Completed:** 2026-06-12T12:36:00Z
- **Tasks:** 3
- **Files modified:** 10

## Accomplishments

- Added RED frontend coverage for GFM tables, task lists, fenced code, copy labels, raw HTML inerting, safe links, unsafe links, and absence of `dangerouslySetInnerHTML`.
- Added backend security contract coverage proving conversation detail returns stored message content as JSON strings with no `rendered_html`, `sanitized_html`, or sanitizer-warning fields.
- Added `MessageMarkdown` with `react-markdown`, `remark-gfm`, no `rehype-raw`, explicit URL allowlisting, inert unsafe links, and raw HTML tag escaping before Markdown parsing.
- Added `CodeBlock` with Prism syntax highlighting, uppercase language labels, dark code-card styling, and clipboard-only `Copy code` / `Copied!` behavior.
- Updated assistant completed messages to use the Markdown renderer while leaving user messages as plain React-escaped text.
- Added frontend Docker ignore rules so Compose builds do not copy host `node_modules`, `.next`, or TypeScript build cache into Linux images.
- Patched `next` to `16.2.9` and added a narrow `next -> postcss@8.5.10` npm override after audit surfaced existing high/moderate dependency findings.

## Dependency Gate

The blocking package legitimacy checkpoint completed before manifest changes.

- `react-markdown@10.1.0`: MIT, source `remarkjs/react-markdown`, safe-by-default renderer, React 18+ peer.
- `remark-gfm@4.0.1`: MIT, source `remarkjs/remark-gfm`, provides tables/task lists/fenced-code-adjacent GFM behavior.
- `react-syntax-highlighter@16.1.1`: MIT, source `react-syntax-highlighter/react-syntax-highlighter`, React syntax highlighting.
- `@types/react-syntax-highlighter@15.5.13`: MIT, source DefinitelyTyped, required for TypeScript.

No `rehype-raw` package was added.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create RED Markdown, code, and rendering-contract tests** - `1294b05` (test)
2. **Task 3: Implement safe Markdown and inert code rendering** - `3debfb5` (feat)

**Plan metadata:** this docs commit

## Files Created/Modified

- `backend/tests/security/test_chat_rendering_contract.py` - Proves adversarial stored content remains raw JSON content and backend does not return rendered/sanitized HTML fields.
- `frontend/tests/chat-markdown.test.ts` - Covers GFM rendering, raw HTML inerting, safe/unsafe links, copy labels, code block rendering, and source-level no-raw-HTML guardrails.
- `frontend/components/chat/MessageMarkdown.tsx` - Implements the safe Markdown renderer, raw HTML tag escaping, scheme allowlist, inert unsafe links, and GFM plugin usage.
- `frontend/components/chat/CodeBlock.tsx` - Implements inert Prism-highlighted code display and copy feedback.
- `frontend/components/chat/MessageList.tsx` - Routes assistant completed messages through `MessageMarkdown`; keeps user messages plain.
- `frontend/app/globals.css` - Styles Markdown spacing, tables, inline code, dark code cards, and copy button focus states.
- `frontend/package.json` / `frontend/package-lock.json` - Add approved rendering packages, patch Next, and override Next's nested PostCSS to a fixed version.
- `.gitignore` - Ignores TypeScript build info.
- `frontend/.dockerignore` - Keeps host build artifacts out of frontend Docker image builds.

## Decisions Made

- Kept Markdown rendering in the browser boundary. The backend stores and returns raw content only, making frontend rendering the sole DOM conversion point.
- Escaped raw HTML tags before Markdown parsing instead of enabling raw HTML parsing or adding a sanitizer that would need to parse HTML.
- Rendered unsafe links as text instead of anchors so blocking is silent and readable.
- Used a narrow npm override for `next`'s transitive PostCSS rather than widening unrelated dependencies.

## Deviations from Plan

### Auto-fixed Issues

**1. [Dependency Security] Patched existing Next/PostCSS audit findings**
- **Found during:** Docker `npm ci` verification.
- **Issue:** The existing `next@16.2.0` produced high/moderate audit findings, and `next@16.2.9` still pinned vulnerable nested `postcss@8.4.31`.
- **Fix:** Updated `next` to exact `16.2.9` and added a scoped npm override for `next -> postcss@8.5.10`.
- **Verification:** `npm audit --json` returned zero vulnerabilities, and Docker `npm ci` reported `found 0 vulnerabilities`.
- **Committed in:** `3debfb5`

**2. [Build Hygiene] Added frontend Docker context ignore rules**
- **Found during:** Local npm install/build verification.
- **Issue:** The frontend Docker context had no ignore file, so local `node_modules` and `.next` could pollute Linux image builds.
- **Fix:** Added `frontend/.dockerignore` and ignored `*.tsbuildinfo`.
- **Verification:** `docker compose build frontend` used a small context and installed dependencies inside the image.
- **Committed in:** `3debfb5`

**3. [Test Precision] Adjusted RED assertions for real highlighter output**
- **Found during:** GREEN implementation.
- **Issue:** Prism highlighting splits code across spans, and escaped raw HTML may display inert attribute text.
- **Fix:** Updated tests to assert token presence across markup and no executable event-handler attribute inside an actual tag.
- **Verification:** Frontend Markdown tests passed while still rejecting executable HTML and unsafe hrefs.
- **Committed in:** `3debfb5`

---

**Total deviations:** 3 auto-fixed.
**Impact on plan:** All deviations tighten the planned security/build guarantees without changing the user-facing scope.

## Issues Encountered

- The first Docker test runs used stale images until the frontend/backend test images were rebuilt.
- Docker Compose continued to report pre-existing orphan containers. They were not removed and did not affect verification.
- `next build` prints its standard suggestion to update `tsconfig.json` inside the container, but source `tsconfig.json` remains compatible with direct `npm run typecheck`.

## User Setup Required

Rebuild the frontend image through the normal project command so Docker installs the new frontend packages:

```bash
docker compose up --build
```

No new secrets or environment variables were added.

## Known Stubs

None for direct-chat Markdown rendering. Search citations and sandbox output rendering remain later-phase work.

## Verification

- RED frontend: `docker compose run --rm frontend npm run test -- frontend/tests/chat-markdown.test.ts` failed before implementation on missing `@/components/chat/CodeBlock`.
- Backend contract: `docker compose -f compose.test.yaml run --rm backend-test pytest tests/security/test_chat_rendering_contract.py` passed with `1 passed`.
- Local focused frontend: `npm run test -- tests/chat-markdown.test.ts tests/chat-workspace.test.ts` passed with `12 passed`.
- Local frontend typecheck: `npm run typecheck` passed.
- Local dependency audit: `npm audit --json` returned zero vulnerabilities.
- Docker frontend build image: `docker compose build frontend` passed and `npm ci` reported `found 0 vulnerabilities`.
- Docker frontend tests: `docker compose run --rm --no-deps frontend npm run test` passed with `24 passed`.
- Docker frontend typecheck: `docker compose run --rm --no-deps frontend npm run typecheck` passed.
- Docker frontend production build: `docker compose run --rm --no-deps frontend npm run build` passed.
- Docker backend contract: `docker compose -f compose.test.yaml run --rm backend-test pytest tests/security/test_chat_rendering_contract.py` passed with `1 passed`.

## Next Phase Readiness

Ready for Plan 02-07 to complete Phase 02 verification and documentation around the private direct-chat slice. Direct chat now has owner-scoped history, retry/error handling, responsive navigation, safe Markdown/code rendering, and clean dependency audit status.

## Self-Check: PASSED

- `MessageMarkdown` and `CodeBlock` exist and are wired into assistant message rendering.
- No `rehype-raw` or `dangerouslySetInnerHTML` is used in the renderer source.
- Unsafe schemes and relative links do not become anchors.
- Raw HTML tags render as inert text.
- Backend does not return rendered HTML fields.
- Task commits `1294b05` and `3debfb5` exist in git history.
- Docker frontend tests, typecheck, production build, and backend rendering contract passed.

---
*Phase: 02-private-direct-chat*
*Completed: 2026-06-12*
