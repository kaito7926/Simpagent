# Quick Task 260615-owm: Fix frontend workspace audit findings

**Date:** 2026-06-15
**Source audit:** `artifacts/frontend-workspace-audit-2026-06-15.md`

## Must Haves

- Remove duplicate desktop/mobile chrome so each viewport has one brand and one new-chat action.
- Fix workspace page metadata so Settings is labeled as Settings.
- Remove or hide dead sidebar sections and keep the sidebar focused on working actions.
- Consolidate trusted supervisor/orchestration mutation controls into Settings.
- Remove admin-only and disabled placeholder controls from the chat composer tools menu.
- Replace scaffold/admin roadmap copy with product-ready preview or empty states.
- Normalize visible brand naming to `SimpAgent`.
- Ensure admin metrics do not claim live telemetry unless backed by live values.

## Implementation Tasks

1. Update chat workspace chrome and page metadata in `frontend/components/chat/ChatWorkspace.tsx`.
2. Simplify sidebar navigation and remove redundant admin mutation controls in `frontend/components/chat/ChatSidebar.tsx`.
3. Tighten chat composer tools to only actionable user tools in `frontend/components/chat/ChatComposer.tsx`.
4. Polish Settings administrative controls and brand copy in affected frontend components.
5. Run frontend typecheck/tests where feasible and document verification.
