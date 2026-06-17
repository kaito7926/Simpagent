---
status: resolved
trigger: "Administration evidence table mouse wheel does not scroll horizontally; implement JavaScript horizontal wheel scrolling"
created: 2026-06-17
updated: 2026-06-17
---

# Debug Session: Administration Horizontal Wheel Scroll

## Symptoms

- Expected behavior: in the Administration tab, Users, Tool executions, and Gateway evidence tables can be scrolled left and right with mouse/trackpad wheel input.
- Actual behavior: the horizontal scrollbar exists, but wheel scrolling and custom-thumb dragging can still fail to move the table horizontally.
- Error messages: none reported.
- Timeline: after adding visible horizontal table scrollbars.
- Reproduction: open an Administration evidence table with horizontal overflow and use mouse/trackpad wheel input over the table.

## Current Focus

- hypothesis: Some Administration table wrappers report no native horizontal overflow, so drag code clamps the target scrollLeft to 0 even when table content is visually clipped.
- test: make the custom scrollbar state-driven and verify the table markup exposes a transformable scroll content layer.
- expecting: wheel input, track clicks, keyboard input, and dragging the custom thumb move the table left/right even when browser-native horizontal overflow is unreliable.
- next_action: verify the JavaScript scroll model with typecheck and focused frontend tests.
- reasoning_checkpoint: User asked for a JavaScript/Next.js implementation if browser horizontal page scrolling cannot be relied on.
- tdd_checkpoint: add a component-level test for wheel-to-horizontal scroll behavior if the existing test stack can exercise DOM events.

## Evidence

- 2026-06-17: `EvidenceTable` has `onScroll` synchronization between the table scroll region and the rail, but no `onWheel` handler.
- 2026-06-17: Existing SSR tests only assert scroll-region markup and widths, not wheel behavior.
- 2026-06-17: The custom thumb could appear but not move because the drag handler used `tableScroll.scrollWidth - tableScroll.clientWidth`; in the broken layout that value can be 0.

## Eliminated

- hypothesis: The table lacks a horizontal scroll region.
  reason: The markup and CSS already create `.evidence-table-scroll` and `.evidence-table-scroll-rail`; the reported issue is wheel interaction.

## Resolution

- root_cause: `EvidenceTable` ban đầu phụ thuộc vào native horizontal overflow để tính `maxScrollLeft`. Khi wrapper/card bị layout hoặc clip theo cách khiến `scrollWidth - clientWidth` trả về 0, custom thumb vẫn hiện nhưng mọi thao tác drag bị clamp về 0 nên bảng không dịch sang phải/trái.
- fix: thêm JavaScript horizontal scroll model trong `EvidenceTable`: đo width hiển thị từ viewport/shell/track, giữ `scrollLeft` trong React state, clamp bằng `contentWidth - viewportWidth`, render bảng trong `.evidence-table-scroll-content`, và dịch nội dung bằng `transform: translateX(...)`. Custom thumb, track click, keyboard, và wheel handler đều cập nhật cùng state này thay vì phụ thuộc hoàn toàn vào native overflow.
- verification: `npm run typecheck`; `npm run test -- tests/admin-evidence.test.tsx`
- files_changed: `frontend/components/admin/EvidenceTable.tsx`, `frontend/app/globals.css`, `frontend/tests/admin-evidence.test.tsx`, `.planning/debug/resolved/admin-horizontal-wheel-scroll.md`
