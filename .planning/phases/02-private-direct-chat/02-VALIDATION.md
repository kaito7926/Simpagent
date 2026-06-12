---
phase: 02
slug: private-direct-chat
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-11
---

# Phase 02 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Existing pytest `>=9,<10`, pytest-asyncio `>=1.4,<2`, HTTPX `>=0.28,<1`, and frontend `tsx --test` |
| **Backend config file** | `backend/pyproject.toml` |
| **Frontend config file** | `frontend/package.json` scripts + TypeScript config |
| **Backend quick run command** | `docker compose run --rm backend pytest -q tests/integration/chat -x` |
| **Backend security quick command** | `docker compose run --rm backend pytest -q tests/security/test_chat_authorization.py tests/security/test_chat_idempotency.py tests/security/test_chat_provider_failure.py -x` |
| **Frontend quick run command** | `docker compose run --rm frontend npm run test -- tests/chat-workspace.test.ts tests/chat-markdown.test.ts` |
| **Frontend typecheck** | `docker compose run --rm frontend npm run typecheck` |
| **Full backend suite** | `docker compose run --rm backend pytest -q` |
| **Frontend build check** | `docker compose run --rm frontend npm run build` |
| **Assembled smoke** | `docker compose up --build --wait && docker compose run --rm backend pytest -q tests/smoke/test_private_direct_chat.py` |
| **Estimated quick runtime** | Under 45 seconds once Phase 2 test modules exist |

All conversation, message, and authorization integration tests must continue to use the real PostgreSQL-backed Compose topology. Do not replace owner, locking, or sequence guarantees with SQLite or mocked repository behavior for release-gate tests.

---

## Sampling Rate

- **After every task commit:** Run the narrowest relevant backend or frontend test module, targeting under 45 seconds.
- **After every wave:** Run `docker compose run --rm backend pytest -q tests/integration tests/security` and the relevant frontend test modules.
- **After send/retry or provider-adapter changes:** Always run the idempotency, provider-failure, and two-user authorization suites.
- **After frontend workspace or rendering changes:** Always run chat workspace tests, Markdown rendering tests, typecheck, and at least one authenticated session-controller test.
- **Before verification:** Run the full backend suite, frontend typecheck, frontend build, and the assembled private-direct-chat smoke test.
- **Max feedback latency:** 45 seconds for task-level checks; topology-level smoke remains a wave or phase gate.

---

## Per-Task Verification Map

| Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| AUTHZ-03 | T-02 | Chat routes deny missing `chat:read` or `chat:write` before DB content or provider work | security/integration | `docker compose run --rm backend pytest -q tests/security/test_chat_authorization.py` | No - Wave 0 | pending |
| AUTHZ-05 | T-01 | Conversation and message lookups constrain owner and resource ID in the same DB path | security/integration | `docker compose run --rm backend pytest -q tests/security/test_chat_authorization.py` | No - Wave 0 | pending |
| AUTHZ-06 | T-01 | A second user cannot infer, read, append to, retry, or delete another user's conversation | security/integration | `docker compose run --rm backend pytest -q tests/security/test_chat_authorization.py tests/integration/chat/test_conversation_crud.py` | No - Wave 0 | pending |
| CHAT-01 | T-03 | First message or explicit create path creates one owned conversation | integration | `docker compose run --rm backend pytest -q tests/integration/chat/test_conversation_crud.py -k create` | No - Wave 0 | pending |
| CHAT-02 | T-03 | Sidebar list returns only owner conversations in stable newest-first cursor order | integration | `docker compose run --rm backend pytest -q tests/integration/chat/test_conversation_crud.py -k list` | No - Wave 0 | pending |
| CHAT-03 | T-03 | One owned conversation returns ordered history by `sequence_no` | integration | `docker compose run --rm backend pytest -q tests/integration/chat/test_conversation_crud.py -k retrieve` | No - Wave 0 | pending |
| CHAT-04 | T-03 | Delete sets `deleted_at`, hides the conversation, and preserves retention semantics | integration | `docker compose run --rm backend pytest -q tests/integration/chat/test_conversation_crud.py -k delete` | No - Wave 0 | pending |
| CHAT-05 | T-04 | Duplicate submits and retries with the same `client_message_id` never create duplicate provider work | security/integration | `docker compose run --rm backend pytest -q tests/security/test_chat_idempotency.py` | No - Wave 0 | pending |
| CHAT-06 | T-04 | Accepted user turns and successful assistant turns persist once with monotonic order and safe metadata | integration | `docker compose run --rm backend pytest -q tests/integration/chat/test_message_send.py` | No - Wave 0 | pending |
| CHAT-07 | T-05 | Provider failure persists a retryable failed assistant turn or equivalent safe artifact with a correlation ID and no fabricated success | security/integration | `docker compose run --rm backend pytest -q tests/security/test_chat_provider_failure.py` | No - Wave 0 | pending |
| CHAT-08 | T-05 | OpenAI-compatible adapter honors configured base URL, key, model, timeout, and retry ceilings | unit/integration | `docker compose run --rm backend pytest -q tests/unit/ai/test_chat_adapter.py` | No - Wave 0 | pending |
| CHAT-09 | T-06 | Authenticated user can navigate conversations, compose, reload history, and recover from pending/retryable failures | frontend/integration | `docker compose run --rm frontend npm run test -- tests/chat-workspace.test.ts tests/chat-session-routing.test.ts` | No - Wave 0 | pending |
| CHAT-10 | T-06 | Markdown, tables, task lists, code blocks, and links render safely without raw HTML or dangerous schemes | frontend/security | `docker compose run --rm frontend npm run test -- tests/chat-markdown.test.ts` | No - Wave 0 | pending |
| CHAT-11 | T-05 | Non-streaming JSON direct-chat path returns correct conversation and turn state | integration/smoke | `docker compose run --rm backend pytest -q tests/integration/chat/test_message_send.py tests/smoke/test_private_direct_chat.py` | No - Wave 0 | pending |

---

## Critical Security Scenarios

1. **Two-user BOLA matrix:** user B attempts list, retrieve, delete, send, retry, and history reload against user A's conversation IDs and message IDs; all attempts deny with no content leak and no provider call.
2. **Duplicate submit matrix:** same `client_message_id` from double-click, network retry, and refresh replay creates one user message and at most one successful assistant completion.
3. **Pending-turn conflict:** one conversation with an in-flight assistant turn refuses a second send until the first resolves.
4. **Provider failure persistence:** timeout, auth/config error, rate limit, empty response, and 5xx all end in retryable failed state with correlation ID and no fabricated successful assistant content.
5. **Retry correctness:** retry reuses the existing user message and assistant placeholder, not a new user row.
6. **Safe Markdown corpus:** raw HTML tags, event handlers, `javascript:` links, dangerous `data:` URLs, and code blocks remain inert on reload and fresh render.
7. **Pagination stability:** newest-first list remains stable as additional conversations update `updated_at`.
8. **Session continuity:** authenticated chat requests still use the existing single-flight refresh path and fail closed on invalid session state.

---

## Wave 0 Requirements

| Wave 0 path | Owner | Created before behavior |
|-------------|-------|-------------------------|
| `backend/tests/integration/chat/test_conversation_crud.py` | Phase 02 plan wave 1 | conversation list/create/retrieve/delete implementation |
| `backend/tests/integration/chat/test_message_send.py` | Phase 02 plan wave 1 | send / non-streaming response implementation |
| `backend/tests/security/test_chat_authorization.py` | Phase 02 plan wave 1 | owner/scoped authorization implementation |
| `backend/tests/security/test_chat_idempotency.py` | Phase 02 plan wave 2 | idempotent send / retry implementation |
| `backend/tests/security/test_chat_provider_failure.py` | Phase 02 plan wave 2 | provider failure mapping and retry implementation |
| `backend/tests/security/test_chat_rendering_contract.py` | Phase 02 plan wave 3 | persisted rendering-safety contract enforcement |
| `backend/tests/unit/ai/test_chat_adapter.py` | Phase 02 plan wave 1 | OpenAI-compatible adapter implementation |
| `frontend/tests/chat-workspace.test.ts` | Phase 02 plan wave 3 | chat-first authenticated workspace implementation |
| `frontend/tests/chat-markdown.test.ts` | Phase 02 plan wave 4 | Markdown / code rendering implementation |
| `frontend/tests/chat-session-routing.test.ts` | Phase 02 plan wave 3 | authenticated workspace session-expiry and retry UX |
| `backend/tests/smoke/test_private_direct_chat.py` | Phase 02 final wave | assembled full-stack private-direct-chat verification |

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Chat-first workspace feels distinct from the Phase 1 account-access shell while remaining legally and visually distinct from ChatGPT | CHAT-09 + D-01 through D-06 | Layout and design-distinctness judgment remain partly human | Inspect desktop and mobile chat workspace after login; confirm sidebar, composer-first state, and distinct SimpAgent branding |
| Delete undo timing and inline retry/failure messaging are understandable to an evaluator | CHAT-04, CHAT-07, CHAT-09 | Perceived clarity and UX timing need human review | Delete a conversation, observe hide + undo affordance, trigger provider failure, and assess retry messaging/correlation display |
| Safe Markdown presentation remains readable after sanitization | CHAT-10 | The rendered safe version may be technically correct but visually poor | Render adversarial Markdown payloads and confirm the safe output remains understandable without noisy sanitizer warnings |

---

## Validation Sign-Off

- [x] Every planned requirement has an automated command path or explicit manual-only exception.
- [x] Task-level checks remain narrow enough for fast sampling.
- [x] Security-sensitive send/retry/provider/rendering paths each have dedicated negative tests.
- [x] Frontend workspace and Markdown safety are independently testable.
- [ ] Wave 0 test files are created before behavior implementation.
- [ ] Full backend suite, frontend typecheck/build, and assembled smoke are green.
- [ ] Any UI design contract produced for Phase 2 is reflected in the workspace and rendering tests.

**Approval:** draft - pending Phase 2 planning and implementation
