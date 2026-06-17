---
status: complete
date: 2026-06-17
commit: uncommitted
---

# Quick Task 260617-ij4 Summary

## Completed

- Added a scoped `onWheel` handler to the Administration evidence table horizontal scroll region.
- The handler updates `scrollLeft` directly in Chrome when the table has horizontal overflow.
- The handler only prevents the parent page scroll while the table can actually move horizontally; once the table reaches either edge, normal page scrolling can continue.
- Added `overscroll-behavior-x: contain` to keep horizontal wheel movement inside the evidence table scroll region.

## Files changed

- `frontend/components/admin/EvidenceTable.tsx`
- `frontend/app/globals.css`

## Verification

- `npm run typecheck`
- `npm run test -- tests/admin-evidence.test.tsx`

## Notes

- No commit was created because the worktree already contains unrelated uncommitted changes.
