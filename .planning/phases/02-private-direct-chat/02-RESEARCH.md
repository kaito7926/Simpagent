# Phase 2: Private Direct Chat - Research

**Researched:** 2026-06-11
**Domain:** Owner-only direct LLM chat, idempotent message delivery, safe Markdown rendering, and chat-first browser UX on top of the Phase 1 auth/session foundation
**Confidence:** HIGH for ownership, idempotency, persistence, and rendering boundaries; MEDIUM for live provider behavior because no real OpenAI-compatible credentials were available in this session

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** After login, the product becomes a chat-first workspace instead of keeping the Phase 1 account-access panel as the primary UI.
- **D-02:** Conversation navigation uses a left sidebar on desktop and a drawer or menu pattern on mobile.
- **D-03:** The empty authenticated state is composer-first: the user can type immediately, and the first submit creates the conversation.
- **D-04:** The account menu and logout action live at the bottom of the sidebar, making account/security details secondary to the chat flow.
- **D-05:** Website UI copy for Phase 2 must be English.
- **D-06:** Use Playwright only to inspect public `chatgpt.com` interaction patterns as inspiration. Do not copy OpenAI branding, assets, or pixel-perfect layouts.
- **D-07:** Conversation titles are generated locally from the first user message. Phase 2 must not call the LLM only to title a conversation.
- **D-08:** Conversation deletion is a soft delete using `deleted_at`, hidden immediately from the list, with a short undo toast in the frontend.
- **D-09:** Conversation history uses cursor pagination with stable newest-first ordering.
- **D-10:** Manual rename remains deferred with archive/search in v2 `PROD-01`.
- **D-11:** Each submit carries a frontend-generated `client_message_id` or idempotency key.
- **D-12:** A conversation permits only one in-flight assistant turn at a time.
- **D-13:** Retry after provider failure reuses the already-persisted user message and attempts the assistant response again without creating a second user message.
- **D-14:** Provider failures appear inline as a failed assistant placeholder or error row with a retry button and support correlation ID.
- **D-15:** The backend must not persist a fabricated successful assistant message when the provider fails.
- **D-16:** Backend concurrency control must protect `sequence_no` ordering and return a conflict or pending state rather than allowing concurrent turns in the same conversation.
- **D-17:** Markdown rendering supports GitHub-flavored Markdown, including tables, task lists, and fenced code blocks.
- **D-18:** Raw HTML is disabled completely.
- **D-19:** Code blocks include syntax highlighting and a copy button.
- **D-20:** Links are sanitized so only safe schemes become links.
- **D-21:** External links open in a new tab with `rel="noopener noreferrer"`.
- **D-22:** Sanitizer blocking is silent: render only the safe version.

### Claude's Discretion
- Choose exact route shapes, React component splits, cursor token format, conflict status code, API field names, and Markdown/code libraries.
- Choose whether the failed assistant placeholder is modeled as a message row with explicit status fields or as an equivalent persisted turn artifact, provided history reload and retry remain deterministic.
- Choose exact context-window trimming rules, title truncation length, sidebar breakpoint, and undo-toast timing, provided they preserve the locked UX and safety constraints.

### Deferred Ideas (OUT OF SCOPE)
- Manual rename, archive, and search
- Google Search labels/citations
- Python tool responses
- Streaming responses
- Safe HTML subset rendering
</user_constraints>

## Summary

Phase 2 should extend the verified Phase 1 session boundary into a real chat product without weakening any ownership or browser-safety guarantees. The safest thin slice is not "build all conversation CRUD first, then wire the LLM later". Instead, the phase should be planned as vertical slices around one real user journey: an authenticated user opens the chat workspace, submits the first message, gets one durable assistant response or one durable retryable failure row, and later reloads only their own history. That slice then expands into pagination, deletion, mobile navigation, rendering hardening, and adversarial verification.

The most important engineering decision is to treat each user turn as a persisted state machine, not as a fire-and-forget provider call. The backend should accept or reuse one user message by `client_message_id`, create one assistant placeholder in a `pending` state, release the transaction, call the provider, then update the same placeholder to `completed` or `failed`. That pattern satisfies `CHAT-05`, `CHAT-06`, `CHAT-07`, and decisions `D-11` through `D-16` more reliably than trying to keep the whole provider call inside one long database transaction.

The existing codebase already provides the right anchors: `resolve_principal` enforces current-user fail-closed semantics, `evaluate_required_scopes` already encodes the scope-check pattern, `Conversation` / `Message` / `ToolExecution` ORM models already exist, `ApiError` already gives a stable error envelope with correlation IDs, and `AuthSessionController.authorizedJson` already implements memory-only bearer usage plus one refresh retry. Phase 2 should reuse those boundaries rather than introducing a parallel auth or error path.

**Primary recommendation:** Plan Phase 2 in this order: owner-safe conversation schema and tests, first real send/retry slice with the OpenAI-compatible adapter, chat-first frontend workspace and navigation, safe Markdown/code rendering plus delete/pagination polish, then assembled two-user/provider-failure verification.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| `chat:read` and `chat:write` enforcement | FastAPI authorization dependencies | PostgreSQL owner-scoped queries | Scope alone is insufficient; owner and scope must be checked in the same request path. |
| Conversation ownership and soft deletion | PostgreSQL repository queries | FastAPI routes/services | BOLA safety depends on owner-constrained reads/writes, not post-fetch filtering. |
| Idempotent send and retry | PostgreSQL transaction + service layer | Frontend request IDs | Frontend generates the key; backend must be authoritative for dedupe and ordering. |
| One in-flight turn per conversation | PostgreSQL row locking and persisted pending state | Frontend composer disable state | UI can prevent accidental repeats, but only the DB-backed service can safely serialize concurrent requests. |
| OpenAI-compatible provider call | Local adapter in backend | Settings / provider status | Phase 2 direct chat does not need full agent orchestration or provider-side conversation state. |
| Markdown and code safety | Frontend rendering pipeline | Backend error/message shaping | HTML must never become executable DOM; unsafe URLs must never become live links. |
| Conversation list pagination | Backend cursor contract | Frontend sidebar state | Stable newest-first order must come from the same ordering keys the DB uses. |
| Error and retry UX | Backend persisted failure state | Frontend inline rendering | Retry must target a known failed turn with a correlation-bearing error. |

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|---|---|---|
| AUTHZ-03 | Chat reads require `chat:read`, chat mutations require `chat:write`. | Reuse `resolve_principal` plus `evaluate_required_scopes`; add explicit route-level scope gates. |
| AUTHZ-05 | Queries constrain resource ID and authenticated owner in the same data-access operation. | Owner-scoped repository methods for list/get/delete/send/retry; never fetch by conversation ID alone. |
| AUTHZ-06 | User cannot infer, read, modify, append to, or delete another user's conversations/messages. | Two-user security tests, hidden soft-deleted rows, zero provider calls after denied access. |
| CHAT-01 | User can create a conversation they own. | Composer-first first-turn API or explicit create API tied to authenticated user. |
| CHAT-02 | User can list their own conversations in stable, paginated order. | Cursor pagination on `(updated_at, id)` with newest-first ordering and owner constraint. |
| CHAT-03 | User can retrieve one owned conversation and its ordered message history. | Owner-checked retrieve route returning ordered messages by `sequence_no`. |
| CHAT-04 | User can delete an owned conversation according to documented retention policy. | `deleted_at` soft delete, immediate UI hide, and owner-scoped delete route. |
| CHAT-05 | User can send a message without duplicate submission creating duplicate provider work. | `client_message_id` uniqueness and replay-safe dedupe path. |
| CHAT-06 | Backend persists accepted user messages and successful assistant responses with durable order and safe metadata. | Sequence allocation plus explicit pending/completed turn state. |
| CHAT-07 | Provider failure never creates a fabricated successful assistant message and returns a stable correlation-bearing error. | Failed assistant placeholder row or equivalent persisted failed turn artifact. |
| CHAT-08 | Configured OpenAI-compatible chat works through `LLM_API_BASE`, `LLM_API_KEY`, `LLM_MODEL`, timeout, and retry settings. | Thin `openai` SDK adapter behind app-owned error mapping. |
| CHAT-09 | Frontend supports registration/login/logout, conversation navigation, composition, pending states, retryable errors, and history reload. | Reuse Phase 1 session controller and evolve authenticated state into a chat workspace. |
| CHAT-10 | Frontend renders Markdown and code blocks while sanitizing raw HTML, scripts, handlers, and dangerous URLs. | `react-markdown` + GFM + explicit safe-link/URL policy, no raw HTML plugin. |
| CHAT-11 | Chat supports a correct non-streaming JSON response path. | Direct request/response route; streaming stays deferred. |
</phase_requirements>

## Project Constraints (from AGENTS.md, PROJECT.md, AI-SPEC)

- Keep memory-only browser access tokens and cookie-backed refresh handling from Phase 1.
- Keep FastAPI as the authoritative authorization boundary even if Kong later performs coarse checks.
- Keep documentation language Vietnamese overall, but Phase 2 website UI copy is explicitly English.
- Use an OpenAI-compatible adapter for direct chat and keep Google ADK / tools out of this phase.
- Never log secrets, raw bearer tokens, cookies, provider keys, or unbounded raw chat content.
- Prefer a maintainable prototype over introducing full agent, streaming, or multi-tool complexity early.

## Standard Stack for Phase 2

| Area | Recommended Addition or Reuse | Why |
|---|---|---|
| Backend direct chat | `openai>=2,<3` | Matches the existing AI-SPEC contract for an OpenAI-compatible adapter. |
| Backend API style | Existing FastAPI + SQLAlchemy 2 + PostgreSQL repositories | Matches Phase 1 patterns and existing test harness. |
| Frontend workspace | Existing Next.js 16 + React 19 client workspace | The auth/session controller is already client-side and fits a chat workspace. |
| Markdown | `react-markdown` + `remark-gfm` | Supports GFM features while keeping raw HTML disabled by default. |
| Link sanitization | `rehype-sanitize` or an equivalent explicit URL policy | Safe links require positive allowlisting, not passive trust. |
| Code highlighting | A lightweight client-safe highlighter such as `react-syntax-highlighter` light build or an equivalent | Supports fenced code with copy affordance without executing code. |
| Browser tests | Existing `tsx --test` frontend tests plus backend pytest | Fits the current repository test style without introducing a second test runner by default. |

## Recommended Route Surface

Use routes that preserve the original brief while matching the composer-first UX:

- `POST /api/conversations`
  - creates an empty conversation when explicitly requested
  - OR accepts the first message payload so the empty-state submit can create the conversation and first turn atomically
- `GET /api/conversations?limit=&cursor=`
  - returns newest-first owner-only conversation summaries with stable cursor pagination
- `GET /api/conversations/{conversation_id}`
  - returns one owner-checked conversation and ordered message history
- `DELETE /api/conversations/{conversation_id}`
  - soft deletes by setting `deleted_at`
- `POST /api/conversations/{conversation_id}/messages`
  - accepts `{content, client_message_id}` for normal sends
- `POST /api/conversations/{conversation_id}/messages/{client_message_id}/retry`
  - retries the failed assistant generation for the already-persisted user turn

The exact shape can vary, but the first empty-state submit should be one logical user action with one provider-work dedupe boundary.

## Recommended Data Model Evolution

The existing Phase 1 foundation already has `conversations` and `messages`. Phase 2 should extend them rather than adding a parallel chat store.

### Conversations
Keep:
- `id`, `user_id`, `title`, `created_at`, `updated_at`, `deleted_at`

Use:
- `updated_at` as the primary newest-first ordering key for the sidebar
- `deleted_at IS NULL` in all normal list/get/send paths

### Messages
Keep:
- `id`, `conversation_id`, `sequence_no`, `role`, `content`, `metadata`, `created_at`

Add the minimum fields needed for safe turn state:
- `client_message_id` nullable, set on user messages and unique per conversation when present
- `status` with a closed set such as `pending | completed | failed`

Keep provider and error details inside safe metadata, not broad new columns, for example:
- `model`
- `provider_request_id`
- `finish_reason`
- `prompt_tokens`
- `completion_tokens`
- `error_code`
- `correlation_id`

This is enough to model:
- one persisted user message
- one assistant placeholder in `pending`
- retry of the same failed placeholder
- one durable completed assistant response without duplicates

## Architecture Patterns

### Pattern 1: Owner-Scoped Repository Methods

Every conversation and message route should delegate to repository methods that take `user_id` as an input and constrain ownership in SQL, not after fetching rows.

Safe patterns:
- `SELECT ... FROM conversations WHERE id = :conversation_id AND user_id = :user_id AND deleted_at IS NULL`
- `UPDATE conversations SET deleted_at = now() WHERE id = :conversation_id AND user_id = :user_id AND deleted_at IS NULL`
- `SELECT ... FROM messages JOIN conversations ON ... WHERE conversations.user_id = :user_id AND conversations.id = :conversation_id`

Unsafe anti-patterns:
- fetch by `conversation_id`, then compare `conversation.user_id` in Python
- send provider context before the owner check is complete
- reveal different 403/404 shapes that let a second user infer whether a conversation exists

### Pattern 2: Stable Newest-First Cursor Pagination

Use `updated_at DESC, id DESC` for sidebar ordering. Cursor payload should carry both ordering fields so ties stay deterministic.

Recommended cursor contents:
- `updated_at`
- `id`

Recommended query predicate:
- `(updated_at, id) < (:cursor_updated_at, :cursor_id)` when ordering newest-first

Do not paginate by offset. Offset becomes unstable when recent conversations update while the user scrolls.

### Pattern 3: Idempotent Send and Retry State Machine

Use this service flow for a normal send:

1. Resolve principal and require `chat:write`.
2. Lock the owner-checked conversation row.
3. If a `pending` assistant message already exists in that conversation, return a stable conflict or pending response.
4. If a user message already exists for `(conversation_id, client_message_id)`, return the existing turn state without a second provider call.
5. Insert the user message.
6. Insert one assistant placeholder with the next `sequence_no` and `status=pending`.
7. Commit.
8. Build bounded context from owner-checked local history only.
9. Call the provider.
10. Update the same assistant placeholder to `completed` with content, or to `failed` with safe metadata and correlation ID.
11. Commit and return the updated conversation state.

Use this service flow for retry:

1. Resolve principal and require `chat:write`.
2. Lock the owner-checked conversation row.
3. Find the existing user message by `client_message_id` plus its paired assistant placeholder.
4. Refuse retry if the turn is already `pending` or already `completed`.
5. Change the failed assistant placeholder back to `pending`.
6. Commit.
7. Rebuild context from the same persisted user message and prior successful turns.
8. Call the provider.
9. Update the same placeholder to `completed` or `failed`.

This keeps the history durable and prevents duplicate user rows.

### Pattern 4: Thin OpenAI-Compatible Adapter

Implement Phase 2 direct chat behind one local adapter, for example:
- `backend/app/ai/chat_adapter.py`
- `backend/app/ai/prompts.py`
- `backend/app/ai/schemas.py`

The adapter should:
- build one bounded non-streaming chat-completions request
- accept only local persisted turns as context
- never pass tools, search params, file params, or MCP config
- map provider exceptions to app-owned error codes such as `provider_unreachable`, `provider_rate_limited`, `provider_empty_response`, or `provider_status_error`
- return safe metadata for persistence and UI display

Do not rely on provider-side stored conversation state in Phase 2. The local database is the source of truth for ownership, history, retry, and deletion.

### Pattern 5: Chat Workspace Evolution on the Frontend

The safest frontend move is to preserve the existing Phase 1 session controller and replace only the authenticated view.

Recommended split:
- keep `frontend/app/page.tsx` thin
- keep `AuthSessionController` as the single token/refresh authority
- refactor `AccountAccessShell` into a top-level session/workspace controller
- create a new `frontend/components/chat/` subtree for:
  - chat layout shell
  - conversation sidebar
  - mobile drawer
  - message list
  - composer
  - retry row
  - empty state
  - account menu

This avoids duplicating login/logout/session-expiry handling.

### Pattern 6: Safe Markdown and Code Rendering

Use a positive-allowlist renderer:
- `react-markdown`
- `remark-gfm`
- no `rehype-raw`
- explicit URL sanitation so only `http`, `https`, and `mailto` become live links

Required behaviors:
- raw HTML stays inert text
- fenced code renders as inert text with syntax highlighting and copy
- `javascript:` and dangerous `data:` URLs do not become clickable links
- external links open with `target="_blank"` and `rel="noopener noreferrer"`
- there is no `dangerouslySetInnerHTML` in the message rendering path

### Pattern 7: English Product Copy, Vietnamese Project Docs

Phase 1 frontend copy is Vietnamese. Phase 2 must switch the browser UI to English while keeping planning and project documentation Vietnamese. Avoid mixed-language user-facing UI. The research, plan, and docs can stay Vietnamese if the project requires it, but rendered product controls and alerts should be English for this phase.

## Implementation Order

1. **Schema and test harness extension**
   - extend the `messages` contract for turn state and idempotency
   - add backend integration/security tests for owner-scoped CRUD, send dedupe, retry, provider failure, and two-user BOLA denial
2. **First real backend chat slice**
   - implement conversation create/list/get/delete plus first-turn send with idempotent provider call and persisted assistant placeholder
3. **Frontend chat-first workspace**
   - reuse session controller and swap the authenticated Phase 1 card for a real chat workspace with desktop sidebar and mobile drawer
4. **Rendering and UX hardening**
   - add safe Markdown/code rendering, copy button, retry rows, empty state, pending state, delete undo, and history reload
5. **Assembled verification**
   - verify two-user isolation, duplicate submit behavior, provider failure handling, and browser-safe rendering in the full stack

## Anti-Patterns to Avoid

- Building all conversation CRUD before introducing the provider-backed send path. That creates horizontal planning instead of a real user slice.
- Using only frontend button disabling for dedupe. It does not stop network retries, refreshes, or concurrent tabs.
- Holding a database transaction open for the full provider request. That increases lock time and makes failure handling fragile.
- Fetching a conversation by ID, then checking ownership in Python. That is a direct BOLA footgun.
- Persisting provider error strings, raw exception bodies, full prompts, or full assistant text in logs or security events.
- Allowing `rehype-raw`, `dangerouslySetInnerHTML`, or unconstrained URL rendering in message content.
- Treating a failed assistant placeholder as a successful assistant message.
- Recreating auth/session logic in the chat workspace instead of reusing `AuthSessionController`.
- Introducing search, tools, streaming, or rename/archive/search work into this phase.

## Open Questions and Gating Notes

1. **UI design contract gate**
   - Phase 2 is a frontend-bearing phase and `.planning/config.json` keeps the UI safety gate enabled.
   - Resolved on 2026-06-11: `D:\ADMIN\Documents\matmahoc\@DO_AN\Simpagent\.planning\phases\02-private-direct-chat\02-UI-SPEC.md` exists and defines the Phase 2 UI design contract.
   - Planning may proceed with `02-UI-SPEC.md` as the authoritative frontend contract for chat workspace layout, English copy, responsive navigation, delete undo, pending/failed states, and safe rendering.

2. **Live provider compatibility**
   - No credentialed OpenAI-compatible probe was possible in this session.
   - The adapter should therefore be planned behind deterministic mocks/fakes plus integration points. A credentialed smoke check remains required only in an environment that has valid provider credentials; no-credential environments must rely on deterministic fake-provider smoke evidence and must not claim live-provider compatibility.

## Validation Architecture

### Test Framework

| Property | Value |
|---|---|
| Framework | Existing pytest backend suite plus `tsx --test` frontend tests |
| Backend quick run | `docker compose run --rm backend pytest -q tests/integration/chat -x` |
| Backend security run | `docker compose run --rm backend pytest -q tests/security/test_chat_authorization.py tests/security/test_chat_idempotency.py tests/security/test_chat_rendering_contract.py -x` |
| Frontend quick run | `docker compose run --rm frontend npm run test -- tests/chat-workspace.test.ts tests/chat-markdown.test.ts` |
| Frontend typecheck | `docker compose run --rm frontend npm run typecheck` |
| Assembled smoke | `docker compose up --build --wait && docker compose run --rm backend pytest -q tests/smoke/test_private_direct_chat.py` |

### Critical Scenarios

1. Two-user BOLA denial for list/get/delete/send/retry paths.
2. Duplicate submit with identical `client_message_id` results in one user message and at most one successful assistant row.
3. Retry after provider failure reuses the original user message and does not create another user row.
4. A pending assistant turn blocks a second send in the same conversation.
5. Provider failures persist a retryable failed turn with a correlation ID and no fabricated assistant success.
6. Markdown payloads containing raw HTML, event handlers, `javascript:` URLs, and dangerous `data:` URLs remain inert.
7. Conversation list pagination remains newest-first and stable as new conversations update.
8. Auth/session expiry still routes through the existing refresh flow without leaking access tokens to browser storage.

### Wave 0 Gaps for Phase 2

- `backend/tests/integration/chat/**`
- `backend/tests/security/test_chat_authorization.py`
- `backend/tests/security/test_chat_idempotency.py`
- `backend/tests/security/test_chat_provider_failure.py`
- `backend/tests/security/test_chat_rendering_contract.py`
- `backend/tests/unit/ai/test_chat_adapter.py`
- `frontend/tests/chat-workspace.test.ts`
- `frontend/tests/chat-markdown.test.ts`
- `frontend/tests/chat-session-routing.test.ts`

## Sources

### Internal
- `D:\ADMIN\Documents\matmahoc\@DO_AN\Simpagent\.planning\ROADMAP.md`
- `D:\ADMIN\Documents\matmahoc\@DO_AN\Simpagent\.planning\REQUIREMENTS.md`
- `D:\ADMIN\Documents\matmahoc\@DO_AN\Simpagent\.planning\STATE.md`
- `D:\ADMIN\Documents\matmahoc\@DO_AN\Simpagent\.planning\phases\02-private-direct-chat\02-CONTEXT.md`
- `D:\ADMIN\Documents\matmahoc\@DO_AN\Simpagent\.planning\phases\02-private-direct-chat\02-AI-SPEC.md`
- `D:\ADMIN\Documents\matmahoc\@DO_AN\Simpagent\AGENTS.md`
- `D:\ADMIN\Documents\matmahoc\@DO_AN\Simpagent\prompt.md`
- Existing code paths under `backend/app/**`, `frontend/lib/**`, and `frontend/components/account-access/**`

### External research already captured in AI-SPEC
- OpenAI Python SDK and Chat Completions docs
- OWASP API1:2023 Broken Object Level Authorization
- OWASP LLM02 Insecure Output Handling
- OWASP Cross-Site Scripting Prevention Cheat Sheet
- NIST AI RMF / Generative AI Profile

## Metadata

**Confidence breakdown:**
- Ownership, authorization, and BOLA controls: HIGH
- Idempotent send/retry state machine: HIGH
- Safe Markdown and link rendering: HIGH
- Frontend workspace evolution from the Phase 1 shell: HIGH
- Live provider behavior with real credentials: MEDIUM

**Research date:** 2026-06-11
**Valid until:** 2026-07-11 for architectural planning, with live provider behavior rechecked before final assembled verification
