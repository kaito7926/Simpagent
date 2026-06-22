---
phase: 04-isolated-python-execution
plan: "04"
subsystem: frontend
tags: [nextjs, react, chat-ui, python-tooling]
requires:
  - phase: 04-isolated-python-execution
    provides: typed Python execution DTO contract
provides:
  - dedicated Python, deny, and limit chat surfaces
  - typed presenter for Python execution envelopes
  - Next.js preview route for reviewed Python execution states
  - frontend tests for Python-card rendering distinctions
affects: [04-03, chat-renderer, frontend-verification]
tech-stack:
  added: [next.js, react, typescript, lucide-react]
  patterns: [typed-presenter, dedicated-tool-cards, bounded-detail-disclosure]
key-files:
  created:
    - frontend/app/chat/page.tsx
    - frontend/components/chat/ChatPreviewShell.tsx
    - frontend/components/chat/MessageBubble.tsx
    - frontend/components/chat/PythonResultCard.tsx
    - frontend/components/chat/PythonStatusBadge.tsx
    - frontend/components/chat/PythonDetailsToggle.tsx
    - frontend/components/chat/PythonArtifactList.tsx
    - frontend/components/chat/ToolDeniedCard.tsx
    - frontend/components/chat/LimitReachedCard.tsx
    - frontend/lib/chat/tool-copy.ts
    - frontend/lib/chat/tool-results.ts
    - frontend/tests/python-result-card.test.tsx
  modified:
    - frontend/app/globals.css
key-decisions:
  - "Kept the existing light design language and added a Python-only execution motif instead of redesigning the whole shell."
  - "Exposed the work as a dedicated preview route at /chat until the real backend chat orchestration from 04-03 is wired in."
  - "Removed frontend-only artifact preview fields so the presenter stays aligned with the backend execution envelope from 04-01."
  - "Used live-region semantics and bounded disclosure so Python states remain distinct without turning the UI into a notebook or terminal."
patterns-established:
  - "Python execution state is mapped once in a typed presenter and rendered through dedicated surfaces instead of scattered status checks."
  - "Denied, limit-reached, and general Python execution states have separate cards and copy paths."
  - "Only approved artifact types are surfaced as downloads, with raw stdout/stderr kept behind disclosure."
requirements-completed: [CHAT-12, SBOX-07]
completed: 2026-06-12T03:56:48.7993810+07:00
---

# Phase 4: Plan 04 Summary

**The Next.js frontend now has dedicated Python execution UI surfaces, a typed presenter for the backend result envelope, and a `/chat` preview route that shows running, success, denial, policy, limit, and infrastructure states without introducing a Python mode toggle or notebook shell.**

## Accomplishments

- Added dedicated chat components for Python result, tool denial, limit reached, artifact downloads, status badges, and bounded execution details.
- Added `frontend/lib/chat/tool-copy.ts` and `frontend/lib/chat/tool-results.ts` so Python execution envelopes map through one typed presenter layer before rendering.
- Added `frontend/app/chat/page.tsx` as a preview route with representative messages for `running`, `succeeded`, `policy_error`, `denied`, `limit_reached`, and `infra_failure`.
- Extended `frontend/tests/python-result-card.test.tsx` to cover dedicated surfaces, distinct copy, artifact rendering, bounded details, and busy/live-region behavior.
- Updated `frontend/app/globals.css` with the Python execution motif, chat layout styling, and explicit keyboard focus treatment for artifact downloads.

## Decisions Made

- Kept the preview inside the existing frontend instead of replacing the root account-access page, so current work remains compatible with later backend wire-up.
- Localized the Python-specific user-facing copy to Vietnamese while keeping technical identifiers such as `stdout`, `stderr`, `csv`, `json`, and `tool:python`.
- Deferred inline artifact preview because the reviewed backend contract currently exposes only safe artifact metadata and download paths, not preview excerpts.

## Verification

- `git diff --check` passed.
- Automated frontend verification from the plan was **not run** because this machine does not currently provide `node`, `npm`, `pnpm`, `yarn`, `bun`, or `deno`, so `npm run typecheck` and `npm run test -- python-result-card` could not execute.
- Docker-backed verification was also not attempted for this frontend plan because the required Node toolchain is absent in the host session.

## Next Readiness

- Phase `04-03` can now wire real Python execution results into the typed presenter without redesigning the UI.
- Once a JavaScript runtime is available, the immediate follow-up commands are `npm install`, `npm run typecheck`, and `npm run test -- python-result-card` inside `frontend/`.

---
*Phase: 04-isolated-python-execution*
*Completed: 2026-06-12*
