# Quick Task 260617-gsv: Fix Administration evidence table horizontal clipping

Date: 2026-06-17

## Must haves

- Administration tables use the available workspace width instead of being constrained to a narrow centered column.
- Users and Gateway evidence tables no longer appear cut off while there is unused space around them.
- Keep the existing Administration navigation, data contracts, and table behavior.

## Tasks

1. Inspect the admin workspace shell and identify the container causing the width clamp.
2. Replace the narrow admin content/header wrapper with a wider responsive container.
3. Run targeted frontend checks and record any unrelated blockers.
