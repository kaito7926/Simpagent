# Phase 2: Private Direct Chat - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-11
**Phase:** 2-private-direct-chat
**Areas discussed:** Chat workspace shape, Conversation lifecycle, Send/retry/idempotency behavior, Assistant response rendering and safety

---

## Chat Workspace Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Chat-first app shell | After login, show a full chat workspace with conversation list, active thread, and composer; account/security info becomes secondary. | yes |
| Keep account panel plus chat | Preserve the Phase 1 account-access layout and add chat beside or below it. | |
| Minimal single-thread view | Start with one conversation screen and defer sidebar/navigation complexity. | |

**User's choice:** Chat-first app shell.
**Notes:** User requested Vietnamese agent-user communication but English website UI. User also requested using Playwright to clone ChatGPT.com; this was narrowed to using Playwright to inspect public interaction patterns as inspiration only, without copying branding, assets, content, or pixel-perfect design.

| Option | Description | Selected |
|--------|-------------|----------|
| Left sidebar on desktop, drawer on mobile | Conversation list stays visible on wider screens; mobile uses a drawer/menu. | yes |
| Top conversation switcher | Simpler layout but weaker history scanning. | |
| No sidebar initially | Only current conversation plus history button/list view. | |

**User's choice:** Left sidebar on desktop, drawer on mobile.

| Option | Description | Selected |
|--------|-------------|----------|
| Composer-first empty state | Ready composer; first submit creates the conversation. | yes |
| Explicit new conversation button first | User must create a conversation before composer appears. | |
| Template prompts | Show starter prompt chips. | partial |

**User's choice:** ChatGPT-style composer-first empty state, with optional simple suggestions.

| Option | Description | Selected |
|--------|-------------|----------|
| Bottom of sidebar | Account menu/logout at bottom of sidebar. | yes |
| Top-right header menu | Account menu in chat header. | |
| Keep visible account card | Preserve visible account/security card. | |

**User's choice:** Bottom of sidebar.

---

## Conversation Lifecycle

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-title from first user message | Generate short local title from first user message. | yes |
| Generic timestamp title | Example: New chat plus date/time. | |
| Untitled until assistant responds | Set title only after successful assistant response. | |

**User's choice:** Auto-title from first user message.

| Option | Description | Selected |
|--------|-------------|----------|
| Soft delete with immediate hide | Set `deleted_at`, hide from UI/list, retain data. | |
| Hard delete immediately | Physically remove conversation and messages. | |
| Soft delete with undo toast | Hide immediately and expose short undo affordance. | yes |

**User's choice:** Soft delete with undo toast.

| Option | Description | Selected |
|--------|-------------|----------|
| Cursor pagination with stable newest-first order | Page newest conversations first with stable cursor pagination. | yes |
| Load all conversations | Simpler but not scalable. | |
| Date groups only, no explicit pagination UI | Visual grouping while pagination remains implicit. | |

**User's choice:** Cursor pagination with stable newest-first order.

| Option | Description | Selected |
|--------|-------------|----------|
| Keep rename/archive/search out of scope | Only create/list/retrieve/delete. | |
| Allow manual rename only | Add minimal rename because auto title may be wrong. | requested |
| Allow archive as delete alternative | Add archive semantics. | |

**User's choice:** User requested manual rename. It was deferred because v2 `PROD-01` owns rename/archive/search.

---

## Send/Retry/Idempotency Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Client request ID plus backend idempotency | Frontend generates `client_message_id`/idempotency key; backend prevents duplicate provider work. | yes |
| Disable button only | Frontend disables composer while pending. | |
| Backend transaction lock only | Backend protects ordering but not duplicate submit semantics. | |

**User's choice:** Client request ID plus backend idempotency.

| Option | Description | Selected |
|--------|-------------|----------|
| Lock current thread until response finishes | No next send in same conversation while pending. | yes |
| Allow queueing next user message | Queue later user messages. | |
| Allow typing but disable send | Draft allowed; send disabled. | |

**User's choice:** Lock current thread until response finishes.

| Option | Description | Selected |
|--------|-------------|----------|
| Retry same turn without duplicating user message | Retry provider call for persisted user message only. | yes |
| Let user resend as new message | Treat retry as a new user message. | |
| Auto-retry silently once, then show error | Hidden retry before visible failure. | |

**User's choice:** Retry same turn without duplicating user message.

| Option | Description | Selected |
|--------|-------------|----------|
| Inline failed assistant placeholder | Error row in thread with retry and correlation ID. | yes |
| Toast only | Failure appears outside the message thread. | |
| Global banner above composer | Failure appears above composer. | |

**User's choice:** Inline failed assistant placeholder.

| Option | Description | Selected |
|--------|-------------|----------|
| One in-flight assistant turn per conversation | Reject/conflict while a conversation has a pending turn. | yes |
| Allow concurrent turns with DB sequence lock | Permit concurrent turns but protect ordering. | |
| Queue server-side | Add server-side queueing. | |

**User's choice:** One in-flight assistant turn per conversation.

---

## Assistant Response Rendering and Safety

| Option | Description | Selected |
|--------|-------------|----------|
| CommonMark-style basics plus fenced code | Paragraphs, lists, links, blockquotes, inline/fenced code. | |
| Minimal text plus code only | Reduced formatting support. | |
| Rich GitHub-flavored Markdown tables/task lists | Adds GFM tables/task lists. | yes |

**User's choice:** Rich GitHub-flavored Markdown tables/task lists.

| Option | Description | Selected |
|--------|-------------|----------|
| Disable raw HTML completely | Escape raw HTML; code blocks display HTML as code. | enforced |
| Sanitize and allow safe HTML subset | Allow selected HTML. | requested |
| Render HTML only in code blocks | Show HTML as code only. | |

**User's choice:** User requested safe HTML subset. It was narrowed to disabling raw HTML completely because the project security baseline forbids rendering arbitrary model/user HTML into the DOM.

| Option | Description | Selected |
|--------|-------------|----------|
| Syntax-highlight plus copy button | Highlight code and expose copy affordance. | yes |
| Plain code block only | No highlighting/copy affordance. | |
| Syntax-highlight only, no copy | Highlight without copy. | |

**User's choice:** Syntax-highlight plus copy button.

| Option | Description | Selected |
|--------|-------------|----------|
| Safe external links with new tab | Allow safe schemes and `noopener noreferrer`; unsafe URLs render as text. | yes |
| Disable all links | Render links as plain text. | |
| Allow internal/external normally | No extra scheme restrictions. | |

**User's choice:** Safe external links with new tab.

| Option | Description | Selected |
|--------|-------------|----------|
| Silent safe rendering | Render safe version without warning. | yes |
| Show small content sanitized note | Notify user that content changed. | |
| Replace whole message with safety error | Block message entirely. | |

**User's choice:** Silent safe rendering.

---

## the agent's Discretion

- Exact sidebar breakpoints, drawer behavior, prompt suggestion copy, title truncation length, undo toast duration, cursor token shape, API field names, conflict status code, and specific Markdown/code libraries.

## Deferred Ideas

- Manual conversation rename, archive, and search are deferred to v2 `PROD-01`.
- Google Search labeling/citations remain Phase 3.
- Python tool responses remain Phase 4.
- Streaming response behavior remains deferred until disconnect, persistence, and proxy behavior are planned.
- Safe HTML subset rendering remains deferred unless a future phase adds a dedicated threat model and XSS tests.
