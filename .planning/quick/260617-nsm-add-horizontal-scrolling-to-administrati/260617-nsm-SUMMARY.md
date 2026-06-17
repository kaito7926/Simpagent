---
status: complete
date: 2026-06-17
commit: uncommitted
---

# Quick Task 260617-nsm Summary

## Completed

- Updated `EvidenceTable` so the visible horizontal scrollbar rail follows the rendered table width.
- Set wider desktop table widths for Users, Tool executions, and Gateway evidence.
- Kept evidence detail actions and mobile card fallback unchanged.
- Added SSR test assertions that the requested Administration tables expose horizontal scroll regions.

## Files changed

- `frontend/components/admin/EvidenceTable.tsx`
- `frontend/components/chat/ChatWorkspace.tsx`
- `frontend/app/globals.css`
- `frontend/tests/admin-evidence.test.tsx`

## Verification

- `npm run typecheck`
- `npm run test -- tests/admin-evidence.test.tsx`

## Notes

- No commit was created because the worktree already contains unrelated uncommitted changes.
