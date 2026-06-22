# Quick Task 260617-deh: Improve Administration and Settings UI layout/text containment, add OAuth icons, and switch font

Date: 2026-06-17

## Must haves

- Administration and Settings surfaces look more organized without changing product workflow.
- Text in cards, pills, badges, tables, drawers, and action rows stays inside its container.
- Google and GitHub OAuth buttons include small, aligned provider icons.
- The app uses a Vietnamese-friendly font already present in the frontend.

## Tasks

1. Update app font wiring to use the local Be Vietnam Pro variable font for the sans stack while preserving the mono stack.
2. Add focused admin/settings CSS component classes and small markup refinements for safer wrapping, responsive layout, and cleaner surfaces.
3. Replace OAuth button icon rendering with compact, fixed-size provider marks and verify frontend type/tests.
