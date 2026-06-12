---
phase: 4
slug: isolated-python-execution
status: approved
shadcn_initialized: false
preset: none
created: 2026-06-12
---

# Phase 4 - UI Design Contract

> Visual and interaction contract for the Python-execution extension to the chat experience. This contract governs only the Python-specific additions; it must preserve the existing visual language established by earlier phases.

---

## Contract Intent

Phase 4 does not redesign the application shell. It adds one new capability to the existing chat flow:

1. The user asks for Python in natural language through the normal composer.
2. The interface clearly distinguishes Python-tool behavior from direct assistant replies and Google-grounded Search.
3. The user can understand success, denial, infrastructure failure, blocked imports, and hard-limit termination without reading raw logs.
4. The user can inspect bounded raw execution details and download only approved small artifacts.
5. The interface never suggests that the user controls runtime policy, package installation, or multi-tool chaining.

This phase must not add a separate "Run Python" mode toggle, a notebook UI, shell-like console chrome, package-install controls, freeform file browser, or a combined Search-then-Python turn.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | Small local React component set |
| Preset | Not applicable; preserve existing local Tailwind patterns |
| Component library | Local semantic components built with React and Tailwind CSS |
| Optional upstream source | Official shadcn components only if Phase 2/3 later initialize shadcn |
| Third-party registry blocks | Forbidden |
| Icon library | Lucide React, outline icons only |
| Font | Be Vietnam Pro, consistent with current frontend |
| Theme | Light theme only in v1 |

### Component Strategy

Reuse the current semantic approach from `frontend/components/account-access/**`: small focused components, explicit state styling, and no framework-heavy UI abstractions.

| Component | Responsibility |
|-----------|----------------|
| `PythonResultCard` | Main bounded execution result container inside the chat stream |
| `PythonStatusBadge` | Success, denied, running, failed, and limit-reached treatment |
| `PythonSummaryRow` | One-line summary, duration, and profile metadata |
| `PythonDetailsToggle` | Expand/collapse bounded stdout, stderr, and execution metadata |
| `PythonArtifactList` | Approved artifact links and optional inline preview affordances |
| `ToolDeniedCard` | Dedicated missing-permission and policy-denied presentation |
| `LimitReachedCard` | Exact limit that ended execution, plus safe retry guidance |
| `PolicyErrorCard` | Blocked import or disallowed behavior explanation |

Do not add a generic command palette, terminal emulator, code editor, notebook tab strip, or new dashboard shell in Phase 4.

### Visual Motif

Use an "execution spine" motif that extends the restrained security language from Phase 1:

- A slim left border on Python cards identifies tool execution without overpowering the chat layout.
- Status badges and metadata chips carry most of the state meaning.
- Raw execution details live behind progressive disclosure rather than occupying the whole message surface.
- The motif appears only on Python-related cards, never on all assistant messages.

Do not introduce neon terminal themes, faux shell prompts, matrix-style visuals, or hacker-themed backgrounds.

---

## Spacing Scale

Continue the established 4px base scale:

| Token | Value | Usage |
|-------|-------|-------|
| `space-1` | 4px | Inline icon gaps, micro-meta spacing |
| `space-2` | 8px | Badge padding, compact row spacing |
| `space-3` | 16px | Default content gap inside cards |
| `space-4` | 24px | Card padding and section separation |
| `space-5` | 32px | Expanded detail grouping |
| `space-6` | 48px | Major desktop section breaks |

Exceptions:

- Primary interactive targets remain at least 44x44px.
- Expand/collapse controls may use text + icon, but the clickable area must still meet target sizing.
- Artifact preview thumbnails, if added, must align to the same spacing scale rather than ad-hoc dimensions.

---

## Typography

Preserve the current frontend hierarchy:

| Role | Size | Weight | Line Height | Usage |
|------|------|--------|-------------|-------|
| Meta | 14px | 400/600 | 1.45 | Duration, profile, status labels, artifact metadata |
| Body | 16px | 400/600 | 1.55 | Summary text, denial explanations, detail content |
| Section heading | 20px | 600 | 1.3 | Expanded detail section labels |
| Message heading | 16px | 600 | 1.45 | Python card title line |

Rules:

- Execution metadata may use tabular numerals but should not switch to a separate terminal font.
- Raw stdout/stderr blocks may use a monospace code face only inside the expanded detail region.
- Do not center Python result text; all execution surfaces remain left-aligned.

---

## Color

Preserve the existing calm palette and reserve new accents only for Python execution surfaces.

| Role | Value | Usage |
|------|-------|-------|
| Dominant | `#F4F6F2` | Page and quiet chat canvas |
| Secondary | `#FFFFFF` | Message surfaces and cards |
| Accent | `#0B6B5D` | Safe/success tool state, active disclosure, artifact focus |
| Warning | `#8A5A00` | Running/limited caution states |
| Warning soft | `#FFF6D8` | Running and limit-reached surfaces |
| Destructive | `#B42318` | Denied/policy/runtime hard-failure text |
| Destructive soft | `#FFF1F0` | Denied and blocked-policy card backgrounds |
| Muted ink | `#53615B` | Supporting metadata and helper copy |

Accent reserved for:

- The Python execution spine
- Successful Python status badge
- The expanded-details trigger
- Keyboard focus for artifact actions

Do not recolor all chat bubbles or all tool output surfaces with the accent.

---

## Layout Contract

### In-Stream Placement

- Python cards appear inline in the normal chat timeline where the assistant response belongs.
- A Python card uses the same outer message width as a normal assistant response so the conversation rhythm stays consistent.
- The top row contains: Python label, status badge, and duration/profile metadata.
- The summary body follows immediately below and is always visible.
- Raw details are collapsed by default behind a text-first disclosure trigger.
- Artifact links render below the summary when present and above raw output details.

### Mobile

- Cards remain full width within the chat column.
- Metadata wraps to multiple lines rather than causing horizontal scroll.
- Artifact actions stack vertically when needed.
- Raw output containers may scroll horizontally inside their own region but must not push the page horizontally.

### Desktop

- Metadata may sit on one line when space allows.
- Approved image artifacts may use a small inline preview next to download links if the layout remains stable.
- Expanded details should not exceed the chat column width or create side-by-side panes.

---

## Information Architecture

Phase 4 adds Python-specific states to the existing chat interaction model.

### Entry Rules

- The composer remains natural-language only.
- There is no explicit "Run Python" switch, tab, or dropdown in v1.
- If a prompt requires both Search and Python but does not already include enough data for a Python-only run, the UI must show a denial/explanation state rather than silently chaining tools.

### Response Types the User Must Distinguish

| Type | Required visual signal |
|------|------------------------|
| Direct assistant reply | Existing normal assistant rendering |
| Google-grounded Search | Existing Search citation/suggestion rendering from Phase 3 |
| Python execution | Dedicated Python result card |

### Python States

| State | UI surface | Meaning |
|-------|------------|---------|
| `running` | Python result card with warning treatment | Execution has been accepted and is in progress |
| `succeeded` | Python result card with success/neutral treatment | Execution finished within policy |
| `denied` | Tool-denied card | User lacked permission or policy blocked the action before execution |
| `policy_error` | Policy error card | Code asked for blocked imports or disallowed behavior |
| `limit_reached` | Limit-reached card | A named hard limit stopped execution |
| `infra_failure` | Python result card with failure treatment | Worker or sandbox infrastructure failed safely |

The UI must never reuse the same presentation for `denied` and `infra_failure`.

---

## Copywriting Contract

All user-facing Python copy is Vietnamese. Technical identifiers such as `csv`, `json`, `stdout`, or profile names may remain English.

| Element | Copy |
|---------|------|
| Python card eyebrow | `Python giới hạn` |
| Running label | `Đang thực thi` |
| Success label | `Hoàn tất` |
| Denied label | `Bị từ chối` |
| Limit label | `Vượt giới hạn` |
| Infra failure label | `Không thể chạy` |
| Details trigger closed | `Xem chi tiết thực thi` |
| Details trigger open | `Ẩn chi tiết thực thi` |
| Artifact section heading | `Tệp đầu ra` |
| Blocked import title | `Import này không được phép trong môi trường Python giới hạn.` |
| Search+Python deny body | `Yêu cầu này cần cả dữ liệu tìm kiếm và Python. Ở phiên bản hiện tại, hệ thống chỉ cho phép một công cụ trong mỗi lượt.` |

### Card Body Guidance

- Success summary explains what completed, not just that a process ended.
- Denial copy states that policy prevented the action and, when appropriate, suggests asking an administrator for the required tool permission.
- Limit-reached copy names the exact limit, such as time, memory, output, or process count.
- Infrastructure failure copy never exposes stack traces, image names, host paths, or container IDs.

---

## Artifact Contract

- Only small approved artifact types such as `csv`, `json`, `txt`, and `png` may be downloadable in Phase 4.
- Each artifact row shows file name, safe type label, and size.
- Unknown or blocked artifact types must not appear as downloadable links.
- The UI must not expose a file explorer, arbitrary path names, or a retained workspace browser.

If inline preview is implemented:

- `png` may show a bounded thumbnail preview.
- Text/data artifacts may show only a short excerpt in expanded details.
- Preview is optional; download safety is mandatory.

---

## Accessibility Contract

- Status must be conveyed by label and copy in addition to color.
- Running and failure transitions should use polite or assertive live regions according to severity.
- The details disclosure must be keyboard-operable and announce expanded/collapsed state.
- Artifact actions require visible focus styles and clear link text.
- Raw output regions must have accessible labels such as `stdout` and `stderr`.

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** approved 2026-06-12
