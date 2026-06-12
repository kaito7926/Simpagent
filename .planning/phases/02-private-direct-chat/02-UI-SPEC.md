---
phase: 2
slug: private-direct-chat
status: draft
shadcn_initialized: false
preset: none
created: 2026-06-11
---

# Phase 2 - UI Design Contract

> Visual and interaction contract for the Private Direct Chat phase. This document defines the authenticated chat workspace, the English copy contract, and the transition from the Phase 1 account-access shell into a real owner-only chat product.

---

## Contract Intent

Phase 2 delivers one complete browser journey:

1. A visitor can still register, sign in, restore a session, and sign out through the existing Phase 1 session boundary.
2. After authentication, the product becomes a chat-first workspace instead of an account card.
3. The user can start a conversation immediately from an empty authenticated state.
4. The user can browse only their own conversations from a left history rail on desktop or a drawer on smaller screens.
5. The user can read safe Markdown/code responses, understand pending and failed states, retry a failed response, and delete a conversation with a short undo window.

This phase is a private direct-chat product, not a model lab, multi-tool cockpit, or admin dashboard. It must not introduce search mode, Python mode, archive/search/rename management, streaming-only affordances, fake future tool toggles, or visually hidden functionality that belongs to later phases.

The visual direction should feel familiar enough for a modern chat product to be learnable within seconds, while remaining visibly SimpAgent-branded and legally distinct from ChatGPT and Claude. Familiar interaction patterns are acceptable; copied layouts, copied copy, copied visual identity, or cloned onboarding are not.

---

## Research Boundary and Distinctness Guardrails

### Inspiration Boundary

Use broad public chat-product conventions (specifically from studying Claude.ai and ChatGPT.com) as inspiration for interactive flows:

- **Claude-inspired Calmness & Document Focus:** Clean, spaced document flow, a soft neutral background canvas that prevents glare, and simple typography hierarchy.
- **ChatGPT-inspired Dynamic Controls:** Collapsible left sidebar for maximizing conversation focus, a sticky input box centered at the bottom of the viewport, and optimistic UI transitions.
- **Chronological History Grouping:** Grouping conversation list into timeframes ("Today", "Yesterday", "Previous 7 Days", etc.) to structure history.
- **Micro-interactions:** Hover-triggered row action menus to prevent clutter, and clean clipboard copy success status checks in code blocks.

### Distinctness Guardrails

The executor must keep the workspace recognizably SimpAgent and legally distinct:

- Keep a visible SimpAgent lockup in the sidebar header on desktop and the mobile top bar on smaller screens.
- Use the warm neutral/coral-accent visual system instead of Claude's cream monochrome or ChatGPT's dark/gray default branding.
- Use card-and-rail surfaces (tinted panels, clean borders) rather than a pixel-for-pixel clone of any competitor thread layout.
- Use plain, direct English copy that references privacy, ownership, and clarity instead of competitor marketing slogans.
- Do not copy competitor logos, icons, product names, starter prompts, empty-state wording, or onboarding card structures.

### Primary Focal Points

- **Empty authenticated state:** the centered composer card in the main thread area is the first visual anchor.
- **Active conversation:** the newest assistant response and the sticky composer form the primary interaction stack.
- **Secondary anchor:** the active conversation row in the sidebar, identified by a left accent rail and surface tint.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | Small local React component set |
| Preset | Not applicable; `components.json` does not exist |
| Component library | Local semantic components built with React and Tailwind CSS |
| Optional upstream source | Official shadcn primitives only, if shadcn is initialized later |
| Third-party registry blocks | Forbidden |
| Icon library | Lucide React, outline icons only, `strokeWidth={1.75}` |
| Font | Be Vietnam Pro via `next/font/local`, fallback `system-ui, sans-serif` |
| Theme | Light theme only in Phase 2 |

### Component Strategy

Add only the components needed for the Phase 2 journey.

| Component | Responsibility |
|-----------|----------------|
| `ChatWorkspaceShell` | Root authenticated shell, responsive layout, mobile drawer state |
| `ChatSidebar` | Conversation list, new-chat action, pagination, active-row state |
| `ChatSidebarRow` | One conversation summary row with title, meta, and active styling |
| `ChatMobileBar` | Small-screen top bar with menu button and SimpAgent lockup |
| `ChatDrawer` | Mobile/tablet conversation navigation |
| `ChatThread` | Scroll region for ordered messages and state rows |
| `ChatEmptyState` | Authenticated empty state with heading, body, suggestion chips, and composer |
| `MessageRow` | User/assistant message surface and role-specific spacing |
| `MessageMarkdown` | Safe Markdown rendering path for assistant content |
| `CodeBlock` | Highlighted fenced-code block with copy action |
| `AssistantPendingRow` | Pending assistant placeholder |
| `AssistantErrorRow` | Failed assistant row with retry action and correlation ID |
| `ChatComposer` | Multiline composer, helper text, send action, pending lockout |
| `ConversationMenu` | Delete action only for Phase 2 |
| `UndoToast` | Short-lived delete undo surface |
| `SidebarAccountMenu` | Current user summary and logout action pinned to sidebar bottom |

Do not create a global model picker, tool palette, settings dock, agent step timeline, admin side panel, or reusable future-phase workspace abstractions in this phase.

---

## Spacing Scale

All layout spacing uses this scale:

| Token | Value | Usage |
|-------|-------|-------|
| `space-1` | 4px | Inline icon gap, chip offset |
| `space-2` | 8px | Compact control spacing, metadata gap |
| `space-3` | 16px | Default gaps, mobile padding, message internals |
| `space-4` | 24px | Card padding, section separation |
| `space-5` | 32px | Empty-state spacing, sidebar section separation |
| `space-6` | 48px | Major thread spacing, desktop breathing room |
| `space-7` | 64px | Large empty-state vertical rhythm |

Exceptions:

- Interactive controls have a minimum target size of 44x44px.
- Text inputs and the primary send button are 48px high minimum.
- Sidebar and composer borders are 1px.
- Accent rails are 3px.
- Card radius is 16px, input/button radius is 12px, pill/chip radius is 999px.

Do not introduce arbitrary spacing tokens outside this scale.

---

## Typography

Use exactly four text sizes and two weights.

| Role | Size | Weight | Line Height | Usage |
|------|------|--------|-------------|-------|
| Label / Meta | 14px | 600 | 1.45 | Sidebar meta, field labels, chips, correlation labels |
| Body | 16px | 400 | 1.6 | Message content, form inputs, body copy, buttons |
| Section Heading | 20px | 600 | 1.3 | Empty-state heading, sidebar section heading, dialog title |
| Page Heading | 28px | 600 | 1.2 | Main authenticated empty-state heading and translated auth-shell heading |

Rules:

- Use weight 600 only for headings, labels, buttons, active conversation titles, and message-role identifiers when shown.
- Keep body text left-aligned.
- Maximum comfortable reading width for assistant prose is 70 characters.
- Use a monospace fallback only inside fenced code blocks; do not introduce a separate code text size.
- Avoid all-caps labels except the small SimpAgent eyebrow if preserved from Phase 1.

---

## Color

### Core Palette

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `#F6F7F9` | App canvas, thread background, empty-state field |
| Secondary (30%) | `#FFFFFF` | Sidebar, composer surface, assistant cards, menus, drawers |
| Accent (10%) | `#C56F58` | Primary send action, active conversation rail, selected chips, focused composer ring |
| Destructive | `#B42318` | Delete action, destructive confirmation, failure emphasis only |
| Ink | `#16211D` | Primary text |
| Muted ink | `#5F716E` | Supporting text and metadata |
| Surface line | `#D8EBEF` | Borders and separators |
| Accent soft | `#F7EDEA` | Active-row surface tint, selected-chip surface |
| Success | `#166534` | Safe success text only |
| Success soft | `#ECFDF3` | Undo-success or recovery background |
| Warning | `#8A5A00` | Pending or caution metadata |
| Warning soft | `#FFF6D8` | Pending helper background |
| Danger soft | `#FFF1F0` | Failed assistant row background |

### Color Distribution

- 60% dominant canvas: viewport background and thread canvas.
- 30% secondary white: sidebar, thread cards, composer, menus, and drawer surfaces.
- 10% accent: send CTA, active conversation marker, selected suggestion chip, focused composer, and active interactive emphasis.

Accent is reserved for those elements only. Do not color every button, icon, badge, or border with the accent. Secondary actions should remain neutral. Destructive red is reserved only for delete/failure surfaces and must never compete with the primary send action.

---

## Layout Contract

### Global Route Model

Phase 2 still uses the root route `/` as the public and authenticated entry point.

| State | Main content |
|-------|--------------|
| `checking_session` | Phase 1 account-access shell with English loading copy |
| `anonymous_login` | English login form |
| `anonymous_register` | English registration form |
| `registration_accepted` | Generic English acceptance state |
| `authenticated_empty` | Chat workspace empty state with centered composer |
| `authenticated_thread` | Chat workspace with active conversation |
| `authenticated_pending` | Active conversation plus pending assistant row and disabled composer |
| `authenticated_failed` | Active conversation plus failed assistant row with retry |
| `session_expired` | English login form with expired-session alert |
| `core_not_ready` | Phase 1 shell, translated to English, with disabled auth controls |

The route must not bounce the user to a separate dashboard path immediately after login. The authenticated state replaces the account-focused card with the chat workspace in place.

### Desktop: 1024px and Wider

- `min-height: 100dvh`.
- Outer page padding: 24px.
- Authenticated shell uses a two-column layout with a collapsible sidebar: 320px sidebar and one flexible thread column.
- The sidebar can be collapsed to maximize active thread focus (inspired by both ChatGPT and Claude). A collapse/expand toggle button is located at the top-left. When collapsed, the sidebar slides off-screen, and the thread column expands to fill the viewport while retaining its centered 880px readable area. A floating, low-contrast expand button remains visible at the top-left of the viewport to reopen it.
- Sidebar and thread are separate scroll regions.
- Main thread column includes a max readable content width of 880px, centered within the available area.
- Sticky composer sits at the bottom of the thread column with 24px bottom padding.
- The mobile drawer does not exist at this breakpoint.

### Tablet: 640px to 1023px

- Single thread column fills the page.
- A top bar appears with menu button, SimpAgent lockup, and a `New chat` action.
- Conversation navigation moves into a slide-over drawer.
- The thread column keeps 24px page padding and a sticky composer.
- The drawer occupies at most 360px width, uses a smooth transition on slide-in, and covers the thread without shifting layout, accompanied by a semi-transparent blur backdrop (`backdrop-blur-sm`).

### Mobile: Below 640px

- Single thread column with 16px horizontal padding and 16px bottom safe-area-aware composer padding.
- The mobile top bar remains visible while the thread scrolls.
- Drawer becomes full-width or nearly full-width, leaving a small dismissal edge only if platform-safe, and locks scroll behind the overlay.
- Message surfaces stack vertically with no horizontal scrolling at 320px width.
- Composer actions remain text-labeled or include a visible label fallback; no icon-only primary send control.

---

## Information Architecture

### Authenticated Workspace Structure

The authenticated shell has exactly three permanent regions:

1. **Conversation navigation**
   - left sidebar on desktop
   - drawer on tablet/mobile
2. **Active thread region**
   - empty state or conversation history
3. **Composer region**
   - centered in empty state
   - sticky at the bottom in active threads

### Sidebar Order

Desktop sidebar order is fixed:

1. SimpAgent lockup
2. `New chat` primary action
3. Conversation list, grouped chronologically (e.g., "Today", "Yesterday", "Previous 7 Days", "Older")
4. `Load more conversations` pagination action when another page exists
5. Sidebar account menu with current email and `Sign out` at the bottom

The account/security area must remain secondary to the chat flow and visually separated by a top border or larger spacing block.

### Conversation Row Contract

Each conversation row contains:

- truncated title derived from the first user message
- last-updated metadata in muted text
- optional state label only when needed: `Pending reply` or `Retry available`

Rules:

- Title truncates to one line on mobile and two lines on desktop.
- Active row uses a left accent rail (`border-l-3 border-[#C56F58]`) and `Accent soft` background (`#F7EDEA`).
- Hover and focus states use subtle surface shifts, not a full accent fill.
- Row action menu (triple-dot button `MoreVertical` from Lucide) is hidden by default and only visible when the row is hovered or focused. Clicking this icon button opens a dropdown containing the `Delete conversation` action. This prevents visual clutter in the list when browsing.
- No rename, archive, or search controls appear in Phase 2.

---

## Thread and Message Contract

### Empty Authenticated State

The empty authenticated state is composer-first.

Visible order:

1. Page heading
2. One-sentence privacy/value body
3. Optional suggestion chips
4. Composer card

Exact empty-state copy:

- Heading: `Start a private chat`
- Body: `Ask a question to create your first conversation. Messages stay inside your own workspace.`

Suggestion chips are optional but, if shown, must use exactly these starter labels:

- `Draft a customer reply`
- `Explain an error message`
- `Rewrite this clearly`

Suggestion chips are styled as modern, light cards (`bg-white border border-[#D8EBEF] rounded-xl px-4 py-3 text-left hover:border-[#C56F58] hover:bg-[#F7EDEA] transition-all cursor-pointer shadow-sm`). Selecting a suggestion chip inserts the text into the composer textarea and auto-focuses it; it does not auto-submit.

### Active Thread State

- Messages render in chronological order from top to bottom.
- The newest content stays closest to the sticky composer.
- Thread loading should preserve layout stability; do not flash placeholder rows over already-loaded content.
- Assistant content may use Markdown, tables, task lists, and fenced code blocks.
- Raw HTML must never become executable DOM.

### Message Surface Rules

#### User message

- Right-aligned within the readable column.
- Uses a warm, lightly tinted surface distinct from assistant cards: styled with a soft warm background (`bg-[#F7EDEA] text-[#16211D]`) and asymmetric rounded corners (`rounded-2xl rounded-tr-none border border-[#F5E2DD]`).
- Maximum width: 720px.
- Plain text line wrapping must remain readable; long unbroken text wraps safely.

#### Assistant message

- Left-aligned card surface within the readable column.
- Maximum width: 880px.
- Uses the neutral secondary surface: styled with a white background (`bg-white`), a thin border (`border border-[#D8EBEF]`), and asymmetric rounded corners (`rounded-2xl rounded-tl-none`).
- Markdown content controls spacing between paragraphs, lists, tables, and code blocks, with high-quality line height (`leading-relaxed`).

#### Pending assistant row

- Appears immediately after the persisted user message.
- Uses one spinner plus the exact label `Generating response...`.
- Does not fake typing dots or random skeleton paragraphs.
- Composer becomes disabled for that conversation while pending.

#### Failed assistant row

Must show:

- Title: `The reply could not be completed.`
- Body: `Try again. If the issue continues, use the reference code below when asking for support.`
- Primary recovery CTA: `Retry response`
- Correlation label: `Reference code: {correlationId}`

Failed assistant row is styled as a warning card with `Danger soft` background (`bg-[#FFF1F0]`), a thick red left border (`border-l-4 border-[#B42318]`), and a Lucide warning icon next to the title. The reference code is displayed inside a clean inline monospace tag (`bg-red-100 px-2 py-0.5 rounded text-sm`).
The failed row must remain inline inside the thread so history reload preserves the state.

### Code Block Contract

- Fenced code blocks render in an inert card with syntax highlighting.
- Styled as a dark container (`bg-[#1E293B] rounded-lg overflow-hidden my-3`).
- A top header bar is styled with a deeper background (`bg-[#0F172A] px-4 py-2 border-b border-neutral-700/50 flex justify-between items-center`), displaying the language (e.g., "PYTHON" or "TYPESCRIPT" in uppercase, 12px, semibold, text-neutral-400) on the left, and a copy button on the right containing a clipboard icon and "Copy code" text.
- On copy success, the icon changes to a green checkmark, text changes to "Copied!" for 2 seconds, and screen readers receive polite status feedback.
- Code blocks never execute and never render HTML as DOM.

---

## Composer Contract

### Primary Behavior

- The composer is always available in the empty authenticated state.
- The first successful submit creates the conversation and its first user message in one logical action.
- In an active thread, the composer stays sticky at the bottom of the thread column.
- The control is a multiline textarea that grows from 56px up to 200px before scrolling internally.

### Composer Visual Layout

- The composer is structured as a single integrated card container (`bg-white border border-[#D8EBEF] rounded-2xl p-3 shadow-md focus-within:ring-2 focus-within:ring-[#C56F58]/20 focus-within:border-[#C56F58] transition-all`).
- The multiline textarea is positioned at the top of the card container, with no scrollbar showing while growing.
- A bottom utility bar spans the width of the container, housing:
  - Small, helper text or status indicators on the left.
  - The "Send message" button on the right.
- The "Send message" button is styled as a circular CTA button with a Lucide `ArrowUp` icon.
  - When the textarea is empty or only whitespace, the button is in a disabled state (light gray background, gray icon, default cursor).
  - When characters are typed, it dynamically transitions to a filled accent background (`bg-[#C56F58]`) and a white icon with a scale transition and hover pointer.

### Exact Copy

| Element | Copy |
|---------|------|
| Field label | `Message` |
| Placeholder | `Message SimpAgent` |
| Primary CTA | `Send message` |
| Disabled helper while pending | `Wait for the current reply to finish before sending another message.` |
| Empty validation | `Write a message before sending.` |

### Interaction Rules

- `Enter` sends the message.
- `Shift+Enter` inserts a new line.
- The send action is disabled when the field is empty, only whitespace, or the conversation already has a pending assistant turn.
- Do not provide upload, voice, model, tool, or mode controls in Phase 2.
- If the same conversation is pending, the helper text appears above the composer controls.
- Preserve draft text during drawer open/close or thread-scroll changes.
- Clear the draft only after a successful accepted send.

---

## Conversation Deletion and Undo Contract

Phase 2 supports delete only.

### Delete Action

- Location: conversation row menu in sidebar or drawer
- Destructive label: `Delete conversation`
- Confirmation title: `Delete conversation`
- Confirmation body: `This removes the conversation from your sidebar now. You can undo for a short time.`
- Confirm CTA: `Delete conversation`
- Dismiss CTA: `Keep conversation`

### Undo Toast

After a successful delete, show a temporary undo toast.

Exact copy:

- Title: `Conversation deleted`
- Action: `Undo`

Rules:

- Duration: 6 seconds.
- On desktop, the toast appears near the lower-left edge of the thread column.
- On mobile, it appears above the composer.
- Undo restores the row without a page refresh.
- The deleted conversation disappears from the list immediately, even before the undo window ends.

---

## Auth-Shell Translation Contract

Phase 2 keeps the Phase 1 auth/session behavior but the browser UI copy becomes English.

Use these exact labels for the updated shell:

| State / Element | Exact copy |
|-----------------|------------|
| Login heading | `Sign in to SimpAgent` |
| Login body | `Use your local account to open a protected session.` |
| Registration heading | `Create account` |
| Registration body | `New accounts start with the Standard User role. Roles and scopes are not selectable here.` |
| Registration accepted heading | `Request received` |
| Registration accepted body | `If this address can be registered, you can continue to sign in.` |
| Authenticated account heading before workspace loads | `You are signed in` |
| Session expired heading | `Session ended` |
| Session expired body | `Your session is no longer valid. Sign in again to continue.` |
| Logout success | `You signed out of this session.` |
| Network failure | `Can't reach the server. Check that the local stack is running and try again.` |
| Generic server failure | `The server couldn't complete this request. Try again.` |

The English translation must preserve the Phase 1 security semantics: generic failures remain generic, duplicate registration remains indistinguishable, and protected-session behavior remains unchanged.

---

## Copywriting Contract

| Element | Exact copy |
|---------|------------|
| Sidebar primary CTA | `New chat` |
| Sidebar empty state | `No conversations yet` |
| Sidebar empty-state body | `Your first message will create a conversation here.` |
| Pagination CTA | `Load more conversations` |
| Empty state heading | `Start a private chat` |
| Empty state body | `Ask a question to create your first conversation. Messages stay inside your own workspace.` |
| Thread loading label | `Loading conversation...` |
| Pending state | `Generating response...` |
| Failed state title | `The reply could not be completed.` |
| Failed state body | `Try again. If the issue continues, use the reference code below when asking for support.` |
| Retry CTA | `Retry response` |
| Delete confirmation | `Delete conversation: This removes the conversation from your sidebar now. You can undo for a short time.` |
| Sign-out action | `Sign out` |

Do not replace these with generic labels such as `Submit`, `Retry`, `Delete`, `OK`, or `Cancel` without the declared noun.

---

## State and Feedback Contract

| Condition | Exact copy | Recovery |
|-----------|------------|----------|
| Conversation list loading | `Loading conversations...` | none |
| Conversation history loading | `Loading conversation...` | none |
| Empty conversation list | `No conversations yet` | `New chat` or first send |
| Send validation | `Write a message before sending.` | keep focus in composer |
| Pending lockout | `Wait for the current reply to finish before sending another message.` | wait until completion or failure |
| Provider failure | `The reply could not be completed.` | `Retry response` |
| Safe correlation available | `Reference code: {correlationId}` | display inline in failed row |
| Delete success | `Conversation deleted` | `Undo` |
| Reload after deleted conversation selected | `This conversation is no longer available.` | return to empty state or nearest remaining conversation |

Rules:

- Use inline thread states and one undo toast; do not add a noisy toast stack.
- Error and failed-turn states use `role=alert`.
- Non-urgent loading and copied states use `aria-live=polite`.
- Never show raw provider messages, stack traces, or secrets.
- Layout width must remain stable when button labels change.

---

## Accessibility Contract

- Target WCAG 2.2 AA.
- Change the document language to English for the browser UI in Phase 2.
- Preserve the visible-on-focus skip link pattern.
- Use semantic landmarks: `main`, `nav`, `aside`, `section`, `form`, `label`, `button`, `dialog` or accessible drawer semantics.
- Every composer, menu, retry, delete, and pagination action must be keyboard reachable.
- The mobile drawer must trap focus only while open and return focus to the menu trigger on close.
- Primary actions must keep a visible text label; icon-only actions require an equal accessible-name fallback and are not allowed for the main send action.
- Status meaning must never rely on color alone; use labels such as `Pending reply` or `Retry available` where state markers appear.
- At 200% zoom on 1280px width, sidebar, drawer, thread, and composer must remain operable without horizontal scrolling.
- Tables inside Markdown must become horizontally scrollable within the message card instead of forcing page-level overflow.
- Under `prefers-reduced-motion: reduce`, remove drawer slide motion and loading spin while preserving textual status feedback.

---

## What Must Not Be Shown

Phase 2 must not display or expose:

- another user's conversations, inferred conversation existence, or message counts
- model pickers, provider names, raw provider request IDs, or raw error bodies
- search toggles, Python toggles, tool traces, citations, or agent-step UI
- rename, archive, search, share, export, or branch controls
- raw HTML rendered from assistant or user content
- unsafe URLs such as `javascript:` or dangerous `data:` links as clickable anchors
- token values, refresh status internals, JWT claims, or hidden diagnostics
- fake streaming cursors, typing theatrics, or placeholder tool outputs when the backend is using a non-streaming JSON path
- branded elements, copy, or starter prompts copied from ChatGPT or Claude

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| Local project components | Components listed in this contract | Source is authored and reviewed in-repository |
| shadcn official | None required by this contract | Allowed only from the official shadcn registry after initialization |
| Third-party registries | None | Prohibited |

If implementation later initializes shadcn, it may use only official primitives equivalent to Button, Input, Textarea, Drawer/Sheet, Dropdown Menu, Scroll Area, Separator, Alert, Badge, and Toast. It must not import full chat templates or dashboard blocks.

---

## Source Traceability

| Source | Decisions Applied |
|--------|-------------------|
| `02-CONTEXT.md` | Chat-first shell, desktop sidebar/mobile drawer, English copy, account menu in sidebar bottom, first-send create flow, delete undo, pending/failed retry states, Markdown/code safety |
| `02-RESEARCH.md` | Sticky composer, owner-only history, persisted assistant state, OpenAI-compatible direct-chat flow, active-thread workspace direction |
| `02-VALIDATION.md` | States that need dedicated UI and test coverage: retry, pending, safe Markdown, session continuity, pagination stability |
| `ROADMAP.md` | Phase 2 boundary and exclusion of search, Python, archive/search, and streaming-first UX |
| `REQUIREMENTS.md` | `AUTHZ-03`, `AUTHZ-05`, `AUTHZ-06`, and `CHAT-01` through `CHAT-11` |
| Current frontend (`frontend/app/layout.tsx`, `frontend/app/globals.css`, `frontend/components/account-access/**`) | Existing font, spacing discipline, local-component approach, and Phase 1 auth-shell continuity |

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending review
