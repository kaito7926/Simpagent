# Quick Task 260617-nsm: Add horizontal scrolling to Administration tables

Date: 2026-06-17

## Must haves

- Users, Tool executions, and Gateway evidence tables expose a horizontal scroll region in the Administration workspace.
- The visible scrollbar can move across the full rendered table width, not only a fixed fallback width.
- Existing evidence data, drawer actions, and mobile fallback behavior remain unchanged.

## Tasks

1. Inspect the shared evidence table component and Administration view configuration.
2. Update the table scroll wrapper so its visible rail tracks the rendered table width.
3. Set appropriate desktop minimum widths for Users, Tool executions, and Gateway evidence.
4. Run targeted frontend tests and type checking.
