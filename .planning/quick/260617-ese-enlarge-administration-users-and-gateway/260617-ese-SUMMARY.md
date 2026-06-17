---
status: complete
date: 2026-06-17
commit: uncommitted
---

# Quick Task 260617-ese Summary

## Completed

- Added optional desktop width and important-column configuration to `EvidenceTable`.
- Enlarged the Users table to `1060px` minimum width and highlighted `Email`, `Role`, and `Status`.
- Enlarged the Gateway evidence table to `1160px` minimum width and highlighted `Type`, `Route`, `Plugin`, and `Status codes`.
- Added scoped `.evidence-table` CSS so words are not aggressively broken inside desktop evidence table cells.

## Files changed

- `frontend/components/admin/EvidenceTable.tsx`
- `frontend/components/chat/ChatWorkspace.tsx`
- `frontend/app/globals.css`

## Verification

- Passed: `npx tsx --test --test-name-pattern "admin evidence primitives|workspace renders backend-backed users" tests/admin-evidence.test.tsx`
- Blocked: `npm run typecheck` and full `npm run test -- tests/admin-evidence.test.tsx` currently fail because `frontend/lib/admin-api.ts` is missing `trusted_supervisor_enabled` and `setTrustedSupervisorEnabled`, while `ChatWorkspace` and the admin evidence test still reference them. This blocker is outside this table UI change.

## Notes

- No commit was created because the worktree already contains unrelated uncommitted changes.
