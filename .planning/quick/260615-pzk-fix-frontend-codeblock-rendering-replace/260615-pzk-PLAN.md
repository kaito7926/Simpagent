---
status: in_progress
date: 2026-06-15
---

# Quick Task 260615-pzk: Fix frontend codeblock rendering, replace logos, and center signed-out notice

## Must Haves

- Fix assistant markdown code block rendering so fenced code preserves formatting and does not inherit unsafe global word-breaking.
- Replace SimpAgent mark/logo image uses with the provided AuroraGuard mark asset in the chat and sign-in surfaces.
- Center the "You signed out of this session." message on the sign-in page.
- Verify frontend tests and typecheck after changes.

## Tasks

1. Update code block styling/rendering in `frontend/components/chat/CodeBlock.tsx` and `frontend/app/globals.css`.
2. Copy the provided logo into `frontend/public/brand/` and update frontend image references, including the top sign-in logo.
3. Run targeted frontend validation and record the result in summary.
