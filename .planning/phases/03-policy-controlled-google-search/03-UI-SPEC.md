---
phase: 3
slug: policy-controlled-google-search
status: approved
shadcn_initialized: false
preset: none
created: 2026-06-11
---

# Phase 3 - UI Design Contract

> Visual and interaction contract for Policy-Controlled Google Search. This is the canonical Phase 3 UI source of truth for planning and implementation.

---

## Contract Intent

Phase 3 adds one explicit search behavior to the Phase 2 chat shell:

1. User chooses between normal chat and Google Search before sending a turn.
2. Authorized search turns remain visually distinct from normal assistant answers.
3. Grounded results show inline citation markers, a compact source list, and a separate Search Suggestions block.
4. Missing-grounding, denied, unavailable, provider-failure, and timeout states remain distinguishable.
5. Retry and suggestion actions remain explicit user intent; nothing auto-runs a new search turn.

This phase extends the chat shell introduced in Phase 2. If that shell does not exist yet, implement the minimum shell defined here: page header, scrollable message thread, sticky composer, and assistant/user message surfaces. Do not introduce dashboard chrome, admin evidence screens, Python controls, source snippets, or hidden future tool toggles in Phase 3.

The visual direction continues the current local design system already in the repository: light surfaces, Be Vietnam Pro, compact status pills, restrained terracotta accents, teal keyboard focus, and inline alerts instead of heavy banners or modal flows.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | Local project components |
| Preset | Not applicable; `components.json` does not exist |
| Component library | Local semantic components built with React and Tailwind CSS v4 |
| Optional upstream source | None required in this phase |
| Third-party registry blocks | Forbidden |
| Icon library | Lucide React, outline icons only, `strokeWidth={1.75}` |
| Font | Be Vietnam Pro, self-hosted with `next/font/local`; fallback `system-ui, sans-serif` |
| Theme | Light theme only in Phase 3 |

### Component Strategy

Reuse and extend the local component approach that already exists in `frontend/components/account-access/`.

| Component | Responsibility |
|-----------|----------------|
| `ChatShell` | Page frame, conversation-pane layout, and sticky composer region |
| `ConversationHeader` | Conversation title, current mode context, and compact readiness state |
| `MessageThread` | Ordered user and assistant turns with stable spacing and scroll behavior |
| `UserMessageCard` | User turn bubble; no tool metadata |
| `AssistantMessageCard` | Base assistant bubble shell for direct and search-backed answers |
| `ToolModeSwitch` | Two-option segmented control: normal chat vs Google Search |
| `MessageComposer` | Textarea, helper text, submit action, and pending state |
| `GroundedAnswer` | Assistant answer body plus badge, source list, and Search Suggestions |
| `CitationMarker` | Inline numeric evidence marker tied to a specific source row |
| `SearchSourceList` | Ordered list of `title + domain` source rows only |
| `SearchSuggestionList` | Dedicated suggestion block rendered from trusted search fields only |
| `SearchFailureCard` | Denied, unavailable, provider-failure, and timeout surfaces |
| `ActionButton` | Reuse the existing local primary, secondary, and quiet button variants |
| `InlineAlert` | Reuse the existing inline alert pattern for failed or blocked search turns |
| `StatusBadge` | Reuse the existing compact badge pattern for `Google-grounded` and readiness states |

If Phase 2 already created equivalents, extend them instead of duplicating them under new names.

### Visual Motif

Continue the current soft-card + compact-status language:

- Main conversation surfaces use light cards with 1px teal-tinted borders and restrained shadows.
- Search evidence appears as a vertical stack under the assistant answer: badge row, answer body, source list, then suggestion block.
- Use warm terracotta accent only for search-specific emphasis, never as the default color for all controls.
- Keep search feedback inline with the assistant turn; do not use full-width banners, popovers, drawers, or modals for normal search outcomes.

---

## Spacing Scale

All layout spacing uses this scale:

| Token | Value | Usage |
|-------|-------|-------|
| `space-1` | 4px | Citation marker inset, tiny inline gaps |
| `space-2` | 8px | Badge padding, compact button gaps, helper spacing |
| `space-3` | 16px | Default element spacing, block gaps, card padding on mobile |
| `space-4` | 24px | Message-group spacing, composer padding, section separation |
| `space-5` | 32px | Desktop pane padding, nested card padding |
| `space-6` | 48px | Major thread breaks and wide layout gaps |
| `space-7` | 64px | Desktop page padding and large shell spacing |

Exceptions:

- Interactive controls have a minimum target size of `44x44px`.
- Composer textarea minimum height is `104px`.
- Assistant and user message shells use a `24px` radius.
- Source rows and nested suggestion/source cards use a `16px` radius.
- Citation markers use a minimum `24x24px` hit area.

Do not introduce arbitrary spacing values outside this scale.

---

## Typography

Use exactly four text sizes and two weights.

| Role | Size | Weight | Line Height | Usage |
|------|------|--------|-------------|-------|
| Label / Meta | 14px | 400 or 600 | 1.45 | Badges, helper text, domains, status labels, citation numbers |
| Body | 16px | 400 or 600 | 1.55 | Message text, buttons, suggestions, alerts |
| Section Heading | 20px | 600 | 1.3 | Composer section title, source/suggestion headings |
| Page / Conversation Heading | 28px | 600 | 1.2 | Main chat heading only |

Rules:

- Use weight `600` only for headings, segmented-control labels, buttons, source titles, and the `Google-grounded` badge.
- Assistant and user message paragraphs stay left-aligned.
- Maximum readable measure for assistant prose is `68ch`.
- Citation markers use the 14px meta size, not a separate icon treatment.
- Markdown code blocks, inline code, and tables keep the Phase 2 renderer defaults; search-specific metadata never changes code typography.

---

## Color

### Core Palette

| Role | Value | Usage |
|------|-------|-------|
| Dominant 60% | `#FFFFFF` | Main canvas, conversation background, composer base |
| Secondary 30% | `#F9FCFD` | Message surfaces, source list, suggestion cards, sidebar/nav if present |
| Accent 10% | `#C56F58` | Search-specific emphasis only |
| Ink | `#16211D` | Primary text and the default primary CTA background |
| Muted ink | `#5F716E` | Supporting copy, domains, helper text |
| Line | `#D8EBEF` | Card borders and quiet dividers |
| Line strong | `#B7D6DD` | Input and segmented-control borders |
| Accent deep | `#9E503B` | Accent text and hover/focus emphasis for search evidence |
| Accent soft | `#F7EDEA` | Active search mode background, citation-marker fill, subtle search emphasis |
| Focus | `#0B6B5D` | Keyboard focus ring only |
| Success | `#166534` | Ready/success state text |
| Success soft | `#ECFDF3` | Success badge background |
| Warning | `#8A5A00` | Denied or limited-state text |
| Warning soft | `#FFF6D8` | Warning alert background |
| Destructive | `#B42318` | Search failure text only |
| Destructive soft | `#FFF1F0` | Search failure alert background |

### Color Distribution

- 60% dominant canvas: page background, conversation pane, sticky composer region.
- 30% secondary surfaces: message cards, nested evidence blocks, optional sidebar/nav surfaces.
- 10% accent: search mode selected state, citation markers, the `Google-grounded` badge treatment, suggestion hover/selected treatment, and the `Thử lại tìm kiếm` emphasis path.

Accent is reserved for those elements only. Generic primary buttons remain ink-based, matching the current `ActionButton` pattern already in the repo.

### Search-Specific Usage Rules

- `Google-grounded` uses a success-toned badge shell with subtle accent-tinted evidence details beneath it.
- Denied states use warning colors, not destructive red.
- Provider failure, timeout, and unavailable states use destructive colors plus exact explanatory copy.
- Missing-grounding fallback uses neutral message styling and a muted note; it must not borrow the grounded success palette.
- Focus rings stay teal `#0B6B5D`, even when the element is accent-colored.

---

## Layout Contract

### Base Shell

- Search is not a separate top-level page. It lives inside the Phase 2 chat route and active conversation pane.
- If a conversation list exists, keep it. Phase 3 changes only the active conversation pane and composer behavior.
- The active pane contains, in order: header, scrollable thread, sticky composer.
- Keep the current light gradient canvas used by the repo; do not introduce a dark chat canvas for search.

### Desktop: 1024px and Wider

- If a sidebar exists, it may be up to `320px` wide.
- Active conversation pane max width: `880px`.
- Active pane horizontal padding: `32px`.
- Thread vertical gap between turns: `24px`.
- Nested source and suggestion blocks appear directly under the grounded answer, separated by `16px`.
- Sticky composer spans the active pane width and uses a solid or near-solid surface with a top border; do not use glassmorphism.

### Tablet: 640px to 1023px

- Single active pane column.
- Horizontal padding: `24px`.
- Source list and suggestion blocks remain stacked below the answer and fill the message width.
- The mode switch sits above the textarea, never beside it.

### Mobile: Below 640px

- Horizontal padding: `16px`.
- Thread bottom padding must leave room for the sticky composer.
- Suggestion buttons and retry actions become full width.
- Citation markers remain inline; they must not force horizontal scroll.
- No source row, suggestion block, or composer control may overflow a `320px` viewport.

### Message Geometry

- Assistant cards align left and use a bordered light surface.
- User cards may keep the Phase 2 user-bubble style, but search metadata never appears on user turns.
- Grounded search evidence blocks stay inside the assistant message card; they do not break into a separate timeline item.
- Failed or denied search turns occupy the assistant-turn position and use the same width as other assistant messages.

---

## Information Architecture

Search is an explicit per-turn mode inside the existing chat workflow.

| Surface | Requirement |
|---------|-------------|
| Conversation route | Reuse the Phase 2 chat route; no dedicated `/search` page |
| Conversation header | May show compact search readiness context, but must not expose model IDs, provider details, or raw diagnostics |
| Message thread | Shows direct chat, grounded search, degraded fallback, and blocked search turns in chronological order |
| Composer | Owns the explicit mode switch and the phase-specific submit labels |
| Source links | Live only inside grounded assistant turns |
| Search Suggestions | Live only inside grounded assistant turns with trusted suggestion data |

Document title remains the Phase 2 chat title. Switching the composer between normal chat and Google Search must not change the page title.

---

## Search Entry Contract

### Tool Mode Switch

Render a two-option segmented control above the composer textarea.

| Option | Label | Helper copy |
|--------|-------|-------------|
| Direct chat | `Hỏi bình thường` | `Không dùng tìm kiếm bên ngoài.` |
| Google Search | `Tìm bằng Google` | `Dùng khi cần thông tin hiện tại và nguồn dẫn.` |

Rules:

- Only one option may be active at a time.
- Use the same compact segmented-button language as the existing auth mode switch.
- Selected search mode uses `Accent soft` background, accent text, and a subtle bottom inset.
- Switching modes retains the current draft text.
- While a turn is pending, lock the mode switch and submit button.
- Do not surface Python in Phase 3 and do not reserve empty layout space for it.

### Availability and Authorization Visibility

- If the authenticated user model does not contain the known `tool:websearch` scope, the normal UI may omit the search option.
- Any stale-session, backend, or coordinator denial must still render a visible denied search turn inline in the conversation.
- Search readiness may be hinted in compact helper text, but the backend remains authoritative for whether a submitted search turn actually runs.

### Submit Labels

| Active mode | Default CTA | Pending CTA |
|-------------|-------------|-------------|
| Direct chat | `Gửi câu hỏi` | `Đang gửi...` |
| Google Search | `Tìm bằng Google` | `Đang tìm bằng Google...` |

Do not use a generic `Gửi` label when Google Search mode is active.

---

## Grounded Answer Contract

### Successful Grounded Search Turn

When live grounding evidence is present, render the assistant turn in this exact order:

1. Compact badge row with `Google-grounded`
2. Assistant answer markdown with inline citation markers
3. `Nguồn tham khảo` block with ordered source rows
4. `Gợi ý tìm kiếm tiếp theo` block, only if trusted suggestion data exists

No other search trace should appear in the user-facing message body.

### Badge

- Exact label: `Google-grounded`
- Style: compact pill using the existing `StatusBadge` pattern
- Tone: success shell with search-specific accent detail allowed inside the message
- Placement: top of assistant message, before answer text

Only successful grounded turns receive this badge.

### Citation Markers

- Render markers inline in the answer body as numeric markers such as `[1]`, `[2]`.
- Style them as compact accent-soft pills with 14px semibold text.
- Markers must be keyboard focusable.
- Activating a marker moves focus to the matching source row inside the same message.
- Markers must not open external pages directly.
- Keep markers inline with text; do not float them in a separate margin rail.

### Source List

Heading: `Nguồn tham khảo`

Rules:

- Render an ordered list.
- Each row shows only `title + domain`.
- Do not show snippets, full passages, timestamps, favicons, or host-specific metadata.
- Title uses 16px semibold.
- Domain uses 14px regular muted text.
- The full row is the external link target and must have a minimum `44px` height.
- Source links open in a new tab and must use safe external-link behavior.

### Search Suggestions

Heading: `Gợi ý tìm kiếm tiếp theo`

Rules:

- Render Search Suggestions in a dedicated block separate from the answer markdown and separate from the source list.
- Suggestions must be rendered only from trusted Google grounding fields; never merge raw provider HTML into markdown.
- Each suggestion uses a compact local button pattern.
- Clicking a suggestion fills the composer, switches the mode to `Tìm bằng Google`, focuses the textarea, and waits for explicit user submission.
- Suggestion clicks must not auto-run a new search turn.

Announcement after a suggestion click:

`Đã điền gợi ý tìm kiếm vào ô soạn. Nhấn "Tìm bằng Google" để tiếp tục.`

If no trusted suggestion data exists, omit the entire block.

---

## Search Outcome Matrix

| Backend state | Visual treatment | Exact required copy | Action |
|---------------|------------------|---------------------|--------|
| `grounded` | Assistant message with success badge, citation markers, source list, optional suggestions | Badge: `Google-grounded` | None |
| `missing_grounding` | Normal assistant message with no badge, no citations, no suggestions | `Kết quả này có thể tham khảo vì chưa có nguồn xác thực rõ ràng.` | None |
| `denied` | Assistant-turn warning card using `InlineAlert` | Title: `Tìm kiếm đã bị chặn` Body: `Yêu cầu này không được phép dùng Google Search. Không có lượt tìm kiếm nào được thực hiện.` | None |
| `search_unavailable` | Assistant-turn destructive card using `InlineAlert` | Title: `Tìm kiếm hiện không khả dụng` Body: `Gemini Google Search chưa sẵn sàng cho lượt này. Hãy thử lại tìm kiếm hoặc chuyển sang câu hỏi bình thường.` | `Thử lại tìm kiếm` |
| `provider_failed` | Assistant-turn destructive card using `InlineAlert` | Title: `Tìm kiếm đã thất bại` Body: `Không thể hoàn tất lượt tìm kiếm này từ dịch vụ tìm kiếm. Hãy thử lại tìm kiếm hoặc chuyển sang câu hỏi bình thường.` | `Thử lại tìm kiếm` |
| `timeout` | Assistant-turn destructive card using `InlineAlert` | Title: `Tìm kiếm đã quá thời gian chờ` Body: `Không nhận được kết quả từ Google Search trong thời gian cho phép. Hãy thử lại tìm kiếm hoặc chuyển sang câu hỏi bình thường.` | `Thử lại tìm kiếm` |

Rules:

- `missing_grounding` must look like an ordinary assistant answer plus a muted note. It must not look like a failed tool turn and must not carry the grounded badge.
- `denied` must clearly state that no search was executed.
- `search_unavailable`, `provider_failed`, and `timeout` must be visually distinct from each other through heading copy, not color alone.
- Only `search_unavailable`, `provider_failed`, and `timeout` receive a retry control.

### Optional Detail Line

If the backend supplies a safe correlation ID for a failed search turn, show it as muted detail text:

`Mã tham chiếu: {correlationId}`

Do not show correlation IDs on successful or missing-grounding assistant turns.

---

## Retry Contract

`Thử lại tìm kiếm` is attached to the failed assistant turn, not the composer.

Rules:

- Retry reuses the original user prompt and the Google Search mode.
- Retry updates the same assistant-turn slot in place; it must not duplicate the user message.
- Pending retry label: `Đang thử lại...`
- While retry is running, disable the retry button for that turn only.
- Manual edits in the composer create a new turn instead of mutating the failed one.

Denied turns never receive a retry button.

---

## Empty, Loading, and Copywriting Contract

| Element | Exact copy |
|---------|------------|
| Search mode section label | `Chế độ trả lời` |
| Direct mode label | `Hỏi bình thường` |
| Search mode label | `Tìm bằng Google` |
| Primary search CTA | `Tìm bằng Google` |
| Empty state heading | `Chưa có lượt tìm kiếm` |
| Empty state body | `Chọn "Tìm bằng Google", nhập câu hỏi cần thông tin hiện tại rồi gửi.` |
| Search loading status | `Đang tìm thông tin có nguồn dẫn...` |
| Source list heading | `Nguồn tham khảo` |
| Suggestions heading | `Gợi ý tìm kiếm tiếp theo` |
| Missing-grounding note | `Kết quả này có thể tham khảo vì chưa có nguồn xác thực rõ ràng.` |
| Generic search failure fallback | `Không thể hoàn tất lượt tìm kiếm này. Hãy thử lại tìm kiếm hoặc chuyển sang câu hỏi bình thường.` |
| Destructive confirmation | None; Phase 3 introduces no destructive confirmation flow |

Additional copy rules:

- Keep all surrounding UI copy in Vietnamese.
- Preserve the exact English badge label `Google-grounded`.
- Do not claim that a degraded answer is verified, current, or fully sourced when grounding is absent.
- Do not use slangy or playful copy for denied or degraded states; the tone remains factual and calm.

---

## Accessibility Contract

- Target WCAG 2.2 AA.
- Use semantic buttons for the mode switch with `aria-pressed`; do not use clickable `div` elements.
- Grounded evidence blocks remain inside the normal assistant-turn reading order.
- Citation markers must be keyboard focusable and have accessible names such as `Nguồn 1`, `Nguồn 2`.
- Source rows must announce title plus domain.
- Suggestion buttons must announce that they fill the composer instead of auto-submitting.
- Denied and failed search turns use `role="alert"` through the existing `InlineAlert` pattern.
- Success and missing-grounding notes use polite live regions only when they first appear.
- Focus returns to the composer textarea after a suggestion click.
- Retry focus remains on the retried turn until the request settles; do not yank focus to the top of the page.
- At 200% zoom, grounded messages, source rows, and suggestion buttons must wrap without horizontal scroll.
- Search meaning must never rely on color alone; badge text, source list, alert headings, and helper copy carry the distinction.

---

## What Must Not Be Shown

The Phase 3 UI must not display or expose:

- Raw grounding JSON, `groundingMetadata`, or `searchEntryPoint.renderedContent`
- Source snippets, quoted passages, or copied page text in the default source list
- Internal tool traces, retry counters, token cost, capability credentials, provider endpoints, model IDs, or search policy internals
- Hidden or automatic search execution triggered by suggestion clicks
- A `Google-grounded` badge on missing-grounding, denied, unavailable, provider-failure, or timeout turns
- Python controls, multi-tool selectors, or future tool placeholders
- Raw HTML from search or model responses
- Click-tracking UI, tracking parameters, or analytics copy attached to source links or suggestion clicks
- Prompt-injection text presented as trusted UI chrome

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| Local project components | Search-specific components listed in this contract plus existing `ActionButton`, `InlineAlert`, and `StatusBadge` patterns | Source is authored and reviewed in-repository |
| shadcn official | None | Not initialized for this phase by user decision on 2026-06-11 |
| Third-party registries | None | Forbidden |

---

## Acceptance Checklist

### Visual

- [ ] Uses Be Vietnam Pro and the current local light theme already present in `frontend/app/globals.css`.
- [ ] Keeps the compact badge, alert, and status language already established in the repo.
- [ ] Reserves terracotta accent for search-specific emphasis only.
- [ ] Keeps grounded evidence nested under the assistant answer instead of splitting it into a separate page or modal.

### Interaction

- [ ] Search is an explicit per-turn mode, not an automatic route.
- [ ] Suggestion clicks fill the composer and wait for submit.
- [ ] Grounded turns show badge, citations, sources, and suggestions in the required order.
- [ ] Missing-grounding turns show no badge, no citations, and no suggestions.
- [ ] Denied turns clearly state that no search executed.
- [ ] Unavailable, provider-failure, and timeout turns are visibly distinct and support inline retry.
- [ ] Retry updates the failed assistant slot instead of duplicating the user turn.

### Security

- [ ] No raw Google HTML, grounding JSON, snippets, or provider internals appear in the chat UI.
- [ ] Source links show title and domain only.
- [ ] Search Suggestions remain separate from markdown and never auto-execute.
- [ ] Search-specific UI does not expose policy internals, secrets, or typed capability boundaries.

### Accessibility

- [ ] Mode switch, citation markers, source rows, suggestion buttons, and retry actions are fully keyboard accessible.
- [ ] Search meaning never depends on color alone.
- [ ] Mobile and 200% zoom layouts keep grounded evidence readable with no horizontal scroll.
- [ ] Alerts and status messages use appropriate live-region behavior.

---

## Source Traceability

| Source | Decisions Applied |
|--------|-------------------|
| `03-CONTEXT.md` | Inline citation markers, `title + domain` source list, dedicated Search Suggestions block, suggestion prefill without auto-run, compact `Google-grounded` badge, denied/missing-grounding/unavailable/timeout behaviors |
| `03-AI-SPEC.md` | Explicit search mode, distinct grounded vs degraded states, retry attached to the failed turn, no raw provider HTML, no extra user-facing tool trace beyond the approved evidence surfaces |
| `REQUIREMENTS.md` | `AUTHZ-04`, `AUTHZ-07`, `AGNT-01` through `AGNT-07`, `SRCH-01` through `SRCH-08`, and the requirement to visibly distinguish grounded, missing-grounding, failure, and unavailable states |
| `ROADMAP.md` | Phase 3 boundary: search inside chat only, no Python/admin/gateway UI |
| `01-CONTEXT.md` | Standard users typically receive `tool:websearch`; execution-time authorization must still be rechecked immediately before search |
| `frontend/app/globals.css` | Current token palette, light theme, Be Vietnam Pro, compact radii, and spacing scale already implemented in the repo |
| `frontend/components/account-access/*.tsx` | Existing local `ActionButton`, `InlineAlert`, `StatusBadge`, and segmented-control interaction patterns |
| User decision on 2026-06-11 | Preserve the local component system; do not initialize shadcn |

---

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: PASS
- [x] Dimension 4 Typography: PASS
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS

**Approval:** approved 2026-06-11
