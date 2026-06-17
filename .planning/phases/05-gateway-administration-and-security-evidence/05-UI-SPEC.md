---
phase: 5
slug: gateway-administration-and-security-evidence
status: approved
shadcn_initialized: false
preset: target shadcn/ui new-york + neutral
created: 2026-06-14
reviewed_at: 2026-06-14
---

# Phase 5 — UI Design Contract

> Visual and interaction contract for the Phase 5 frontend reset. This file is the canonical UI source of truth for the Final Product Hardening, OAuth, Gateway, Administration, and Security Evidence phase, and it also supersedes earlier shared-shell styling while preserving approved behavior from Phases 1–4.

---

## Contract Intent

Phase 5 is a full frontend visual reset, not incremental polish.

1. Replace the current light terracotta shell with a new shadcn/ui-based visual system inspired by:
   - chat/app reference: `D:/ADMIN/Documents/matmahoc/@DO_AN/Simpagent/.planning/debug/ui-ref/modern`
   - login reference: `D:/ADMIN/Documents/matmahoc/@DO_AN/Simpagent/.planning/debug/ui-ref/login`
2. Preserve functional requirements already established in prior phases:
   - local email/password auth remains supported
   - Google and GitHub OAuth login are supported when configured by Phase 5 backend settings
   - explicit Google Search mode when permitted
   - no separate Python mode toggle unless planning artifacts later change the behavior contract
   - distinct Search and Python result states
   - strict admin access gating and redacted evidence
3. Extend one shared visual language across all of these surfaces:
   - authentication pages
   - conversation shell and sidebar navigation
   - Google Search rendering
   - Python tool rendering
   - admin/settings/evidence pages required by Phase 5
4. Remove unsupported reference-template features from implementation:
   - no unsupported social sign-in buttons beyond configured Google and GitHub OAuth
   - no dark-mode toggle in v1
   - no folders/templates/voice/attachments placeholders
   - no settings popover that hides admin evidence in cramped UI
   - no raw logs, raw provider payloads, raw HTML, or secret-bearing debugging chrome

This phase should feel like one cohesive product system built around the approved brand assets, not a patchwork of old screens.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | shadcn/ui official only, required before implementation |
| Current repo state | `frontend/components.json` does not exist as of 2026-06-14 |
| Target preset | `new-york`, `baseColor: neutral`, `cssVariables: true`, `iconLibrary: lucide` |
| Component library | shadcn/ui primitives wrapped in local semantic components |
| Icon library | Lucide React, outline icons only |
| Font | Be Vietnam Pro, self-hosted with `next/font/local` |
| Theme | Light theme only in Phase 5 |
| HTML language | Set root document language to English: `lang="en"` |
| Browser title | Keep product/browser title string `Simpagent` until a later planning artifact explicitly renames the product |
| Brand assets | `D:/ADMIN/Documents/matmahoc/@DO_AN/Image_for_frontend_design/Brand_identity/auroraguard_primary_logo_transparent.png`, `D:/ADMIN/Documents/matmahoc/@DO_AN/Image_for_frontend_design/Brand_identity/auroraguard_logo_mark_transparent.png` |
| Favicon assets | Use files from `D:/ADMIN/Documents/matmahoc/@DO_AN/Image_for_frontend_design/favicon_io` |

### Required Initialization Rule

Before any UI implementation task starts, initialize shadcn/ui in `frontend/` with a preset compatible with:

- style: `new-york`
- base color: `neutral`
- CSS variables: enabled
- TSX + RSC: enabled
- aliases rooted at `@/components`, `@/components/ui`, `@/lib`

Do not pull any third-party registry block into this phase.

### Component Strategy

Use shadcn primitives under local semantic wrappers so the codebase reads in product terms, not primitive names.

| Semantic wrapper | Base primitives | Responsibility |
|------------------|----------------|----------------|
| `BrandLockup` | `Card`, `Avatar`, `Badge` | Shared product/logo presentation across auth, sidebar, and admin pages |
| `AuthShell` | `Card`, `Input`, `Label`, `Button`, `Alert` | Login/register layout with readiness and trust messaging |
| `AppSidebar` | `Sheet`, `ScrollArea`, `Button`, `DropdownMenu`, `Tooltip` | Desktop rail + mobile drawer for app navigation |
| `ConversationList` | `ScrollArea`, `Button`, `AlertDialog` | Grouped conversations with delete confirmation and undo feedback |
| `SearchModeTabs` | `Tabs` or `ToggleGroup` | Explicit direct chat vs Google Search mode switch |
| `ComposerDock` | `Textarea`, `Button`, `Badge`, `Separator` | Sticky message composer with helper text and pending state |
| `MessageCard` | `Card`, `Badge` | User and assistant message surfaces |
| `SearchEvidenceCard` | `Card`, `Badge`, `Button`, `Separator` | Grounded answer, sources, and suggestion chips |
| `PythonResultCard` | `Card`, `Badge`, `Collapsible`, `Button` | Python summaries, artifacts, limit, denial, and infra states |
| `AdminMetricCard` | `Card`, `Badge` | Aggregate operational and security counts |
| `EvidenceTable` | `Table`, `Badge`, `Button`, `Skeleton` | Bounded admin lists for users, evidence, and tool activity |
| `EvidenceDetailDrawer` | `Sheet`, `Separator`, `Code` styling | Redacted detail view for a selected row |
| `OrchestrationSettingCard` | `Card`, `Badge`, `Button`, `AlertDialog` | Guardrail and trusted-supervisor controls with explicit confirmation |
| `StatePanel` | `Card`, `Alert`, `Empty` treatment | Loading, empty, forbidden, degraded, and error states |

---

## Visual Motif

Adopt the structure of the chat reference and the calm aurora accents of the login reference.

- Canvas: off-white, slightly cool neutral background.
- Primary surfaces: white cards with subtle borders and soft shadow.
- Accent: aurora blue reserved for focus, active nav, selected search mode, citations, primary action emphasis, and Python execution spine.
- Brand glow: use blurred cyan/blue halos only behind hero/logo areas, never behind long-form body text.
- Geometry:
  - app shell radius: `24px`
  - major cards: `20px`
  - nested cards / source rows / evidence rows: `16px`
  - pills and chips: `999px`
- Motion:
  - hover/focus transitions: `140–180ms ease-out`
  - sidebar collapse and mobile sheet: `200–240ms ease-out`
  - no parallax, marquee, or perpetual decorative animation
  - honor `prefers-reduced-motion`

The result should feel premium, quiet, and security-oriented, not playful or neon-terminal themed.

### Primary Visual Hierarchy

For the authenticated experience, the visual focal point order is locked as:

1. active conversation or evidence pane
2. sticky composer or active filter/action bar
3. sidebar, account chrome, and secondary admin controls

Implementation must keep the user’s current task surface visually dominant; navigation and control chrome may support the workflow, but must never overpower the active content pane.

---

## Spacing Scale

Declared values use a strict 4px base.

| Token | Value | Usage |
|-------|-------|-------|
| `xs` | 4px | Inline icon gaps, chip insets, tiny metadata spacing |
| `sm` | 8px | Compact control gaps, badge padding, small row spacing |
| `md` | 16px | Default content spacing, card internals, mobile padding |
| `lg` | 24px | Major card padding, section breaks, desktop turn spacing |
| `xl` | 32px | Desktop shell gaps, large blocks, auth split spacing |
| `2xl` | 48px | Hero spacing, admin page section separation |
| `3xl` | 64px | Page-level breathing room on desktop |

### Exceptions

- Minimum interactive target: `44x44px` — accessibility minimum for touch and keyboard-adjacent hit targets
- Sidebar row minimum height: `48px` — preserves tap comfort and readable two-line conversation metadata in the collapsible rail
- Data table row height: `56px` — required to fit badge + metadata + action affordance without crowding dense admin evidence lists
- Sticky composer minimum expanded height: `72px` — preserves comfortable multi-line drafting and mode/helper copy without collapsing into a cramped single-line bar
- Auth card maximum width: `456px` — keeps login/register forms readable and reference-inspired without stretching fields into low-trust empty space on desktop

Do not introduce arbitrary spacing values outside this scale.

---

## Typography

Use exactly four text sizes and two weights.

| Role | Size | Weight | Line Height | Usage |
|------|------|--------|-------------|-------|
| Label / Meta | 14px | 400 or 600 | 1.45 | Chips, timestamps, domains, helper text, table labels |
| Body | 16px | 400 or 600 | 1.55 | Message text, forms, buttons, row content, admin summaries |
| Heading | 24px | 600 | 1.25 | Card titles, section headings, page subheads |
| Display | 32px | 600 | 1.15 | Auth hero heading, main chat heading, admin overview title |

### Rules

- Only weights `400` and `600` are allowed.
- Vietnamese UI copy must remain left-aligned except for small auth hero lockups.
- Use monospace only for:
  - correlation IDs
  - code blocks
  - Python `stdout` / `stderr`
- Do not use uppercase for long text blocks; reserve uppercase micro-labels for tiny section markers only.
- No extra decorative serif font from the reference templates.

---

## Color

### Core Palette

| Role | Value | Usage |
|------|-------|-------|
| Dominant 60% | `#F6F8FB` | App canvas, auth background, admin page background |
| Secondary 30% | `#FFFFFF` | Cards, sidebar, sticky composer, tables, drawers |
| Accent 10% | `#2F6BFF` | Active nav, selected search mode, citation markers, primary emphasis |
| Accent soft | `#EAF1FF` | Selected rows, active pills, subtle evidence emphasis |
| Accent glow | `#A7E5FF` | Decorative hero glow only |
| Ink | `#0F172A` | Primary text, dark user bubble, high-contrast neutral surfaces |
| Muted ink | `#5B6B83` | Secondary copy, helper text, timestamps |
| Border | `#DCE5F0` | Card borders, separators, input lines |
| Success | `#166534` | Success text and positive tool/admin states |
| Success soft | `#ECFDF3` | Success chip and positive background |
| Warning | `#9A6700` | Caution, pending, limit, unavailable-but-recoverable states |
| Warning soft | `#FFF7D6` | Warning surfaces |
| Destructive | `#B42318` | Denial, hard failure, high-risk confirmation |
| Destructive soft | `#FFF1F0` | Destructive alert backgrounds |
| Focus | `#2F6BFF` | Keyboard focus ring only |

### Accent Reserved For

Use the accent only for these elements:

1. active sidebar item border/fill
2. selected Google Search mode pill
3. primary submit and save buttons
4. inline citation markers `[1]`, `[2]`
5. Python execution spine and success emphasis
6. active admin filter pill
7. visible keyboard focus ring
8. logo glow accents and notched highlights in hero areas

Primary action ownership is locked: submit, save, confirm, and other top-priority CTA buttons use `Accent` as the background token. `Ink` remains the default text/high-contrast neutral token and may style dark user bubbles or quiet secondary emphasis, but it must not compete with Accent-owned primary CTA styling.

Accent is not allowed on every button, every icon, or every message bubble.

### Theme Rules

- Keep the phase light-only. Do not ship a dark-mode toggle.
- Decorative gradients may use `accent glow`, but all readable text still sits on solid surfaces.
- Error meaning must come from copy plus icon/badge, never from red alone.

---

## Shared Layout Contract

### Authentication Pages

Use a desktop two-column composition that borrows the aura and centered card posture of the login reference while preserving the project’s readiness and security context.

- Desktop `>= 1024px`:
  - max shell width: `1200px`
  - left trust column: flexible, minimum `480px`
  - right auth card column: `420–456px`
- Mobile / tablet:
  - single column stack
  - hero first, auth card second
- Auth card treatment:
  - white card, `20px` radius, `24px` padding mobile, `32px` desktop
  - logo at top center of the card
  - form fields full width, `48px` minimum input height
  - configured Google and GitHub OAuth buttons appear above the local email/password divider
  - provider buttons are hidden or disabled with factual copy when the corresponding backend provider is not configured
- Retain readiness and security summary content, but restyle it as calm cards instead of old utilitarian panels.

Do not copy unsupported login-reference providers, forgot-password links, or legal placeholders unless backend support exists.

### Application Shell

Use a single shared shell across chat, settings, and admin pages.

- Desktop sidebar width: `296px`
- Collapsed sidebar width: `76px`
- Mobile drawer width: `320px` max
- Main content max width:
  - chat thread: `880px`
  - admin content canvas: `1120px`
- Sidebar behavior:
  - collapsible on desktop
  - slide-in sheet on mobile
  - grouped navigation, brand lockup at top, account block at bottom

### Chat Thread

- Active thread content width: `760px` comfortable reading zone inside the wider pane
- Turn spacing: `24px`
- Message cards:
  - assistant: white surface, thin border, soft shadow
  - user: dark ink surface with white text, or deep neutral bubble visually distinct from assistant
- Sticky composer sits at bottom of active pane on a solid surface; no glassmorphism.

### Admin Surfaces

Admin pages reuse the same shell and occupy the main pane.

- Page header block at top: title + short purpose line + optional action area
- Filter bar directly below header, sticky on desktop only when list length requires it
- Evidence content uses:
  - metrics cards
  - bounded tables on desktop
  - stacked evidence cards on mobile
- Detail inspection uses a right-side sheet or drawer, not a full-page route for each row.

---

## Information Architecture

| Surface | Access | Layout | Purpose |
|---------|--------|--------|---------|
| Auth shell | Anonymous | split hero + auth card | Login, register, readiness, trust signals |
| Chat shell | Authenticated | sidebar + active pane + sticky composer | Direct chat, Google Search, Python result timeline |
| Account settings | Authenticated | shell page | Identity, role, scopes, session status, sign out |
| Admin overview | `admin:read` | shell page | Aggregate security and operations metrics |
| Users | `admin:read` / `admin:write` | shell page with table + drawer | View users and apply bounded access changes |
| Security events | `admin:read` | shell page with filters | Review forbidden access, replay, sandbox, policy, and failed-login evidence |
| Tool executions | `admin:read` | shell page with filters | Review Search/Python tool summaries and durations |
| Gateway evidence | `admin:read` | shell page with filters | Review rate-limit and correlation-ID evidence |
| Orchestration settings | `admin:read` / `admin:write` | shell page with setting cards | Control guardrail and trusted-supervisor state |

### Navigation Labels

All user-facing navigation labels are English.

- `Chat`
- `Account settings`
- `Admin`
- `Overview`
- `Users`
- `Security events`
- `Tool executions`
- `Gateway evidence`
- `Orchestration`

If the current implementation stays on a single route for authenticated content, the shell must still behave as if these are first-class surfaces, not buried popovers.

---

## Interaction Contract

### Sidebar and Conversation Navigation

- Use the chat reference’s collapsible rail pattern as the base interaction.
- Group conversations by time in Vietnamese:
  - `Hôm nay`
  - `Hôm qua`
  - `7 ngày qua`
  - `Cũ hơn`
- Conversation row shows:
  - title
  - compact secondary line with state or message count
- Active row uses accent-soft background and a `3px` accent border.
- New conversation button sits at the top of the conversation section.
- Delete remains a secondary row action, never the default tap target.

### Composer

- Keep the Phase 3 explicit Search mode selection.
- Search mode control appears above the textarea as a pill/tabs row.
- Submit labels:
  - direct: `Gửi câu hỏi`
  - search: `Tìm bằng Google`
  - pending direct: `Đang gửi...`
  - pending search: `Đang tìm bằng Google...`
- Keep input natural-language first.
- Do not add:
  - Python toggle
  - attachments button
  - microphone button
  - schedule/apps controls

### Google Search Rendering

Preserve the Phase 3 behavior contract and restyle it inside the new shell.

Successful grounded search turn order:

1. `Google-grounded` badge row
2. assistant answer body with inline citations
3. `Nguồn tham khảo`
4. `Gợi ý tìm kiếm tiếp theo` when trusted suggestions exist

Rules:

- Citation markers stay inline, keyboard focusable, and jump to the matching source row.
- Source list shows only `title + domain`.
- Suggestion chips fill the composer and wait for explicit submit.
- Search states remain distinct:
  - grounded
  - missing grounding
  - denied
  - unavailable
  - provider failed
  - timeout

### Python Rendering

Preserve the Phase 4 behavior contract and add one Phase 5 admin-sensitive denial state.

Required Python states:

| State | Treatment |
|------|-----------|
| `running` | warning card with spinner/badge |
| `succeeded` | bordered success card with spine |
| `denied` | destructive denial card |
| `policy_error` | destructive policy card |
| `limit_reached` | warning limit card |
| `infra_failure` | destructive infra card |
| `trusted_supervisor_disabled` | destructive denial card linked to orchestration state |

Rules:

- Python output remains inline in the chat timeline.
- No terminal chrome, no notebook tabs, no file browser.
- Artifacts appear as safe rows below the summary.
- Raw execution details remain collapsed by default.
- Admin-disabled trusted-supervisor state must clearly say that the block came from admin configuration, not from user prompt failure.

### Admin Tables and Evidence

- Desktop evidence uses tables with sticky headers.
- Mobile evidence converts each row into a stacked card with the same fields in the same order.
- Each row must expose:
  - primary label
  - secondary context
  - severity/status badge
  - correlation ID when available
  - `Xem chi tiết` action
- Detail drawer shows only redacted, allowlisted fields.
- Never show secrets, full bearer tokens, raw prompts, raw request bodies, or provider payload dumps.

### Orchestration Controls

- Present `Guardrail safety` and `Trusted supervisor Agent` as separate cards.
- Show current state with a badge.
- Do not use naked inline switches with immediate destructive effect.
- Enabling may commit directly with a success toast.
- Disabling always requires confirmation dialog with consequence text.

---

## Search Outcome Matrix

| Backend state | Surface | Required copy |
|---------------|---------|---------------|
| `grounded` | assistant evidence card | badge `Google-grounded` |
| `missing_grounding` | normal assistant card + muted note | `Kết quả này có thể tham khảo vì chưa có nguồn xác thực rõ ràng.` |
| `denied` | warning evidence card | `Tìm kiếm đã bị chặn` + `Yêu cầu này không được phép dùng Google Search. Không có lượt tìm kiếm nào được thực hiện.` |
| `search_unavailable` | destructive evidence card | `Tìm kiếm hiện không khả dụng` |
| `provider_failed` | destructive evidence card | `Tìm kiếm đã thất bại` |
| `timeout` | destructive evidence card | `Tìm kiếm đã quá thời gian chờ` |

Retry remains attached to the failed Search card only.

---

## Admin Evidence Contract

### Overview Metrics

Show these as first-class cards at the top of admin overview:

- `Active users`
- `Security events`
- `Tool executions`
- `Last 24 hours`
- `Valid correlation references`
- `429 / rate limit`

Each card contains:

- title
- main count
- compact delta or time scope
- one-line meaning

### Users Table

Required columns:

- `Email`
- `Role`
- `Scopes`
- `Status`
- `Created`
- `Actions`

Edit pattern:

- row action opens side drawer
- drawer shows role, scopes, active state, demo indicator
- role/status changes are never inline-editable in the table itself

### Security Events Table

Required columns:

- `Event type`
- `Severity`
- `User`
- `Description`
- `Correlation ID`
- `Time`

Required quick filters:

- `All`
- `Failed sign-ins`
- `Access denied`
- `Refresh replay`
- `429 / rate limit`
- `Python / sandbox`
- `Google Search`

### Tool Executions Table

Required columns:

- `Tool`
- `Status`
- `User`
- `Conversation`
- `Input summary`
- `Output summary`
- `Duration`
- `Correlation ID`
- `Time`

### Gateway Evidence Page

Show two layers:

1. compact overview cards for rate-limit, request-size, and correlation-ID evidence
2. latest evidence list with the same drawer pattern as other admin lists

The page is read-only in Phase 5.

---

## Copywriting Contract

All user-facing copy is English. The product name remains `Simpagent`, and technical identifiers such as `stdout`, `stderr`, `csv`, or `json` may remain unchanged.

### Core UI Copy

| Element | Copy |
|---------|------|
| Auth hero heading | `Secure AI assistance for internal work.` |
| Auth body | `Use Google, GitHub, or your local email and password to enter a protected workspace.` |
| Google login CTA | `Continue with Google` |
| GitHub login CTA | `Continue with GitHub` |
| Local auth divider | `Or use local credentials` |
| Login CTA | `Sign in securely` |
| Register CTA | `Create account` |
| Sidebar primary CTA | `Start new chat` |
| Sidebar label | `Conversations` |
| Account settings label | `Account settings` |
| Protected session label | `Protected session` |
| Chat empty heading | `Start a secure conversation` |
| Chat empty body | `Ask your first question to create a new conversation in your protected workspace.` |
| No conversations | `No conversations yet` |
| No conversations body | `Your first conversation will appear here after you send a message.` |
| Search mode label | `Response mode` |
| Direct mode label | `Direct chat` |
| Search mode label 2 | `Google Search` |
| Source heading | `Sources` |
| Suggestions heading | `Suggested follow-up searches` |
| Admin overview heading | `Security overview` |
| Users empty | `No users match the current filter.` |
| Evidence empty | `No evidence matches the current filter.` |
| Forbidden state | `You do not have permission to view this area.` |
| Forbidden state body | `Use an account with the required access or contact an administrator.` |
| Generic network error | `Can't reach the server. Check that the local stack is running and try again.` |
| Generic server error | `The request could not be completed. Try again. If the issue continues, use the reference code when contacting an administrator.` |
| Correlation label | `Reference code` |

### Destructive Confirmations

| Action | Confirmation copy |
|--------|-------------------|
| Delete conversation | `Delete this conversation?` Body: `The conversation will leave the current list immediately. If supported, you can still undo right after deletion.` Confirm: `Delete conversation` |
| Deactivate user | `Deactivate this account?` Body: `The user will not be able to continue until the account is reactivated.` Confirm: `Deactivate account` |
| Promote to admin | `Grant administrator access?` Body: `This account will gain access to administrative data and configuration actions.` Confirm: `Grant administrator access` |
| Disable trusted supervisor | `Disable trusted supervisor Agent?` Body: `Python turns that depend on this supervision layer will be denied until it is enabled again.` Confirm: `Disable trusted supervisor` |
| Disable guardrail safety | `Disable guardrail safety?` Body: `You are removing one layer of safety checks before tool orchestration.` Confirm: `Disable guardrail safety` |

### Copy Rules

- Keep tone factual, calm, and security-oriented.
- Never imply that denied Search/Python requests actually executed.
- Never expose internal service names, Docker details, raw stack traces, or secret-bearing identifiers.
- Keep copy factual, concise, and implementation-truthful; avoid fake placeholder controls or unsupported promises.

---

## Accessibility Contract

- Target WCAG 2.2 AA.
- All primary navigation, mode pills, row actions, citations, and admin filters are keyboard reachable.
- Use semantic buttons, tabs, tables, dialogs, and sheets from shadcn primitives.
- Sidebar collapse/expand controls require accessible names.
- Search and Python state differences must be conveyed by text + badge + structure, not color alone.
- Correlation IDs must be selectable and copyable.
- Evidence drawers must trap focus and return focus to the triggering row action.
- At `200%` zoom:
  - sidebar, chat thread, composer, and evidence rows must reflow without horizontal page scroll
  - horizontal scrolling is allowed only inside code/output blocks and large tables
- `prefers-reduced-motion` disables non-essential transitions and pulse animations.

---

## What Must Not Be Shown

The Phase 5 refresh must not render:

- unsupported social login buttons beyond configured Google and GitHub OAuth
- Google or GitHub login buttons that submit when the corresponding backend provider is not configured
- forgot-password links that do not work
- dark-mode toggle
- folders, templates, voice, attachments, schedule, or app-launcher placeholders from the reference templates
- raw Google HTML, raw grounding JSON, or provider metadata dumps
- raw sandbox file paths, container IDs, or package-install suggestions
- bearer tokens, cookies, passwords, API keys, or unredacted request bodies
- full prompt content in admin evidence if backend only exposes safe summaries
- a separate `Run Python` mode switch unless future planning artifacts explicitly approve that behavior

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | `button`, `input`, `label`, `textarea`, `card`, `badge`, `tabs`/`toggle-group`, `scroll-area`, `sheet`, `dialog`, `alert-dialog`, `dropdown-menu`, `tooltip`, `separator`, `table`, `collapsible`, `skeleton` | official only, no third-party registry, initialize before implementation — 2026-06-14 |
| Third-party registries | none | forbidden for this phase |

---

## Source Traceability

| Source | Decisions Applied |
|--------|-------------------|
| `D:/ADMIN/Documents/matmahoc/@DO_AN/Simpagent/.planning/STATE.md` | Phase 5 readiness, shipped Phases 1–4 context, current admin gap |
| `D:/ADMIN/Documents/matmahoc/@DO_AN/Simpagent/.planning/ROADMAP.md` | Phase 5 goal, required evidence/admin scope, gateway focus |
| `D:/ADMIN/Documents/matmahoc/@DO_AN/Simpagent/.planning/PROJECT.md` | security product framing, local-auth constraints, Vietnamese docs requirement |
| `D:/ADMIN/Documents/matmahoc/@DO_AN/Simpagent/.planning/REQUIREMENTS.md` | `AUTHZ-02`, `GATE-01`..`GATE-08`, `OBS-01`..`OBS-07`, and prior chat/search/python requirements that must survive the visual reset |
| `D:/ADMIN/Documents/matmahoc/@DO_AN/Simpagent/.planning/phases/03-policy-controlled-google-search/03-UI-SPEC.md` | Search state distinctions, citation order, suggestions behavior |
| `D:/ADMIN/Documents/matmahoc/@DO_AN/Simpagent/.planning/phases/04-isolated-python-execution/04-UI-SPEC.md` | Python state model, artifacts, detail disclosure, no Python mode toggle |
| Current frontend files | confirmed current visual system is local CSS, English-heavy copy, no project `components.json`, and current shell needs full replacement |
| Reference chat template | collapsible rail, roomy chat shell, sticky composer posture |
| Reference login template | centered auth card, logo-first composition, calm aurora background accents |
| User objective | complete refresh, shadcn/ui choice, brand asset paths, favicon paths, cross-surface scope |

---

## Acceptance Checklist

### Visual

- [ ] Uses the new shared light system with aurora-blue accent instead of the current terracotta theme.
- [ ] Applies one shell language across auth, chat, Search, Python, and admin pages.
- [ ] Uses the approved brand and favicon assets.
- [ ] Keeps cards, rails, and drawers visually cohesive with consistent radii and shadows.

### Interaction

- [ ] Search remains explicit and visually distinct.
- [ ] Python stays visually distinct and still has no dedicated toggle in this phase.
- [ ] Admin evidence pages are page-based, filterable, and detail-on-demand.
- [ ] Security-sensitive toggles use confirmation dialogs before destructive state changes.

### Security

- [ ] No unsupported template features are surfaced as fake controls.
- [ ] No raw secrets, provider payloads, or unredacted evidence appear in the UI.
- [ ] Evidence detail views remain bounded and correlation-aware.
- [ ] Access-denied admin states are visible and explicit.

### Accessibility

- [ ] Keyboard and focus handling are complete across shell, chat, and admin flows.
- [ ] State meaning never depends on color alone.
- [ ] 200% zoom and mobile layouts remain readable.
- [ ] Reduced-motion preference is respected.

---

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: PASS
- [x] Dimension 4 Typography: PASS
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS

**Approval:** approved 2026-06-14
