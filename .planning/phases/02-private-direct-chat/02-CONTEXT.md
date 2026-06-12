# Phase 2: Private Direct Chat - Context

**Gathered:** 2026-06-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a secure, durable, owner-only direct LLM chat slice for authenticated users. Phase 2 covers the English chat-first frontend workspace, conversation create/list/retrieve/delete, ordered message persistence, non-streaming direct OpenAI-compatible assistant responses, idempotent send/retry behavior, Markdown/code rendering, and BOLA-safe authorization. Google Search, Python tools, tool response labeling, archive/search, and full manual conversation management remain outside this phase.

</domain>

<decisions>
## Implementation Decisions

### Chat Workspace Shape
- **D-01:** After login, the product becomes a chat-first workspace instead of keeping the Phase 1 account-access panel as the primary UI.
- **D-02:** Conversation navigation uses a left sidebar on desktop and a drawer or menu pattern on mobile.
- **D-03:** The empty authenticated state is composer-first: the user can type immediately, and the first submit creates the conversation.
- **D-04:** The account menu and logout action live at the bottom of the sidebar, making account/security details secondary to the chat flow.
- **D-05:** Website UI copy for Phase 2 must be English. Vietnamese is only the agent-user discussion language for this planning session.
- **D-06:** Use Playwright during UI design or implementation to inspect public `chatgpt.com` interaction patterns as inspiration only. Do not copy OpenAI or ChatGPT branding, logos, assets, content, or pixel-perfect design.

### Conversation Lifecycle
- **D-07:** Conversation titles are generated locally from the first user message, using a short truncation or local summarization. Phase 2 must not call the LLM only to title a conversation.
- **D-08:** Conversation deletion is a soft delete using `deleted_at`, hidden immediately from the list, with a short undo toast in the frontend.
- **D-09:** Conversation history uses cursor pagination with stable newest-first ordering.
- **D-10:** Phase 2 remains focused on create, list, retrieve, message, and delete. Manual rename is desired but deferred because rename, archive, and search belong to v2 `PROD-01`.

### Send, Retry, and Idempotency
- **D-11:** Each submit carries a frontend-generated `client_message_id` or idempotency key. The backend uses it to prevent double-clicks, network retries, refreshes, or browser repeats from creating duplicate provider work.
- **D-12:** A conversation permits only one in-flight assistant turn at a time. While a response is pending, users cannot send another message in that same conversation.
- **D-13:** Retry after provider failure reuses the already-persisted user message and attempts the assistant response again without creating a second user message.
- **D-14:** Provider failures appear inline as a failed assistant placeholder or error row with a retry button and support correlation ID.
- **D-15:** The backend must not persist a fabricated successful assistant message when the provider fails.
- **D-16:** Backend concurrency control must protect `sequence_no` ordering and return a conflict or pending state rather than allowing concurrent turns in the same conversation.

### Assistant Response Rendering and Safety
- **D-17:** Markdown rendering should support GitHub-flavored Markdown features, including tables and task lists, plus fenced code blocks.
- **D-18:** Raw HTML from user or model Markdown is disabled completely. HTML in ordinary text is escaped; HTML inside fenced code blocks displays as code only.
- **D-19:** Code blocks include syntax highlighting and a copy button. Code rendering must never execute code.
- **D-20:** Links are sanitized. Only safe schemes such as `http`, `https`, and `mailto` may become links; unsafe schemes such as `javascript:` or dangerous `data:` URLs render as text.
- **D-21:** External links open in a new tab with `rel="noopener noreferrer"`.
- **D-22:** Sanitizer blocking should be silent: render the safe version without showing noisy technical warnings to the user.

### the agent's Discretion
- Choose exact sidebar breakpoints, drawer implementation, prompt suggestion copy, title truncation length, undo toast duration, cursor token shape, API response field names, and Markdown/syntax-highlighting libraries, provided the locked safety, ownership, and UX decisions above hold.
- Choose the exact conflict status code and error code for an in-flight conversation turn, provided the frontend can show a stable retryable/pending state with a correlation ID when relevant.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and Requirements
- `.planning/ROADMAP.md` - Defines Phase 2 boundary, dependencies, MVP mode, requirement IDs, and success criteria.
- `.planning/REQUIREMENTS.md` - Defines `AUTHZ-03`, `AUTHZ-05`, `AUTHZ-06`, and `CHAT-01` through `CHAT-11`.
- `.planning/PROJECT.md` - Defines project security constraints, stack requirements, external provider assumptions, and out-of-scope boundaries.
- `.planning/STATE.md` - Records Phase 1 completion and decisions carried into Phase 2.
- `AGENTS.md` - Project workflow, stack, and security guidance.
- `prompt.md` - Original project brief and intended secure chatbot behavior.

### Prior Phase Context
- `.planning/phases/01-secure-platform-and-account-access/01-CONTEXT.md` - Locks standard user scope defaults, token/session behavior, and Phase 1 integration expectations.
- `.planning/phases/01-secure-platform-and-account-access/01-VERIFICATION.md` - Evidence that Phase 1 account and platform foundation closed successfully.

### Existing Backend Integration Points
- `backend/app/models/domain.py` - Existing `Conversation`, `Message`, and `ToolExecution` ORM models.
- `backend/alembic/versions/0002_platform_foundations.py` - Existing conversation/message/tool schema migration.
- `backend/app/authorization/principal.py` - Current authenticated principal resolution and fail-closed account state checks.
- `backend/app/authorization/policy.py` - Current role/scope enum and required-scope evaluator.
- `backend/app/api/routes/auth.py` - Existing FastAPI route style, dependency injection, cookie/CSRF handling, and error patterns.
- `backend/app/core/errors.py` - Error envelope and correlation ID format.
- `backend/app/main.py` - Router registration, CORS, and correlation middleware.

### Existing Frontend Integration Points
- `frontend/lib/auth-session.ts` - Existing memory-token session controller, refresh flow, `authorizedJson`, and session error handling.
- `frontend/lib/api.ts` - Existing API error parsing and correlation ID propagation.
- `frontend/components/account-access/AccountAccessShell.tsx` - Current authenticated account UI, English/Vietnamese copy patterns to replace or reuse carefully.
- `frontend/app/page.tsx` - Current root page wiring.
- `frontend/package.json` - Current frontend dependencies; Markdown/code rendering dependencies are not installed yet.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AuthSessionController.authorizedJson` can be reused for chat API calls with memory-only access tokens and refresh-on-401 behavior.
- `ApiError` and `toApiError` already surface backend error codes and correlation IDs for frontend display.
- `resolve_principal` already validates bearer tokens, active users, known roles/scopes, and stale account state.
- `evaluate_required_scopes` provides the existing scope-check pattern for `chat:read` and `chat:write`.
- Existing `Conversation` and `Message` models provide `title`, `deleted_at`, `sequence_no`, role checks, and JSON metadata.

### Established Patterns
- FastAPI route modules live under `backend/app/api/routes` and are registered from `backend/app/api/__init__.py` plus `backend/app/main.py`.
- Frontend user-facing copy from Phase 2 should be English, even though Phase 1 contains Vietnamese account UI copy.
- Backend errors use an `error.code`, `error.message`, and optional `error.correlation_id` envelope.
- Browser refresh tokens remain cookie-backed and inaccessible to JavaScript; chat calls should continue using bearer access tokens through the existing frontend controller.
- Security-sensitive behavior must fail closed and include negative tests for missing scopes, cross-user ownership access, stale tokens, provider failure, and duplicate submit behavior.

### Integration Points
- Backend needs chat routes for conversation list/create/retrieve/delete and send/retry that combine authenticated `user_id` ownership constraints with required chat scopes in the same data path.
- Backend needs an OpenAI-compatible direct chat adapter using `LLM_API_BASE`, `LLM_API_KEY`, `LLM_MODEL`, timeout, and retry settings without logging secrets.
- Frontend root authenticated view should evolve from account-access shell into the chat-first workspace while preserving login/register/session recovery.
- Markdown rendering requires new frontend dependencies and tests because `frontend/package.json` currently has no Markdown/syntax-highlight/sanitizer libraries.

</code_context>

<specifics>
## Specific Ideas

- The desired interaction model is ChatGPT-style: sidebar history, active thread, composer-first empty state, pending assistant row, retryable inline failure, and code blocks with copy affordance.
- Playwright should be used during UI work to inspect `chatgpt.com` public layout and interaction patterns for inspiration. The implementation must remain SimpAgent-branded and legally distinct.
- Manual rename is desired by the user, but it must be deferred unless the roadmap is explicitly updated because v2 `PROD-01` owns rename/archive/search.

</specifics>

<deferred>
## Deferred Ideas

- Manual conversation rename - desired by the user, but belongs to v2 `PROD-01` with archive/search/retention management.
- Conversation archive and search - remain in v2 `PROD-01`.
- Google Search response labeling and citations - Phase 3.
- Python tool responses and tool mode distinction - Phase 4.
- Streaming response behavior - only allowed later if disconnect, persistence, and proxy behavior remain correct.
- Safe HTML subset rendering - deferred unless a future phase adds a dedicated threat model and negative XSS tests.

</deferred>

---

*Phase: 2-private-direct-chat*
*Context gathered: 2026-06-11*
