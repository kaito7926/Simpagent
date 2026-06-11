# Phase 03: Policy-Controlled Google Search - Pattern Map

**Mapped:** 2026-06-11
**Repository state:** Phase 1 foundation present; chat/search product code absent
**Expected file/symbol groups classified:** 16
**Reusable application analogs found:** 10 / 16

## Repository Reality

The repository now contains real Phase 1 backend and account-access frontend code, so Phase 3 is no longer greenfield. However, it still lacks the Phase 2 chat shell, conversation routes, message-send API, and chat-facing frontend components.

- Existing reusable backend analogs: auth routes, service layering, settings/readiness seams, JWT/security helpers, `Conversation`/`Message`/`ToolExecution` models.
- Existing reusable frontend analogs: `ActionButton`, `InlineAlert`, `StatusBadge`, `AuthModeSwitch`, `auth-session.ts`, and `readiness.ts`.
- Missing analogs: chat-shell components, conversation/message route group, search worker module, grounded-rendering components, and search-specific tests.

Therefore Phase 3 should extend current service/component patterns where they exist and create the missing chat/search surfaces explicitly where they do not.

## Canonical Source Order

When sources overlap, use this order:

1. `03-CONTEXT.md` for locked user decisions and scope fences.
2. `03-AI-SPEC.md` for worker/coordinator architecture, evaluation, and guardrails.
3. `03-UI-SPEC.md` for visual, copy, accessibility, and state distinctions.
4. `03-VALIDATION.md` for required evidence, test paths, and safety scenarios.
5. `03-RESEARCH.md` for implementation order, normalized persistence, and anti-patterns.
6. `AGENTS.md`, `REQUIREMENTS.md`, `ROADMAP.md`, and current product code for project-wide constraints and existing seams.

## File Classification

| # | Expected File or Symbol Group | Role | Data Flow | Closest Analog | Canonical Contract |
|---:|---|---|---|---|---|
| 1 | `backend/app/api/routes/search.py` or Phase 2 chat route extension | controller/route | request-response | `backend/app/api/routes/auth.py` | Context + Research Pattern 1 |
| 2 | `backend/app/schemas/search.py` | schema | validation/transform | `backend/app/schemas/auth.py`, `backend/app/schemas/health.py` | UI-SPEC + Research Patterns 1 and 4 |
| 3 | `backend/app/services/search_coordinator.py` | service | request-response/orchestration | `backend/app/services/authentication.py`, `registration.py` | AI-SPEC + Research Patterns 1 through 4 |
| 4 | `backend/app/ai/search_worker/{agent,schemas,grounding,service}.py` | worker/integration | provider/tool boundary | none in repo | AI-SPEC + Research Pattern 2 |
| 5 | `backend/app/core/config.py` search additions | config | environment-to-domain transform | existing file | Research Pattern 6 |
| 6 | `backend/app/core/provider_status.py` search capability extensions | service/helper | transform/readiness | existing file | Research Pattern 6 |
| 7 | `backend/app/security/search_capability.py` or equivalent | security utility | transform/validation | `backend/app/security/access_tokens.py`, `refresh_tokens.py` | Research Pattern 3 |
| 8 | `backend/app/models/domain.py` metadata extensions | model | CRUD/state persistence | existing file | Research Pattern 4 |
| 9 | `backend/app/db/repositories/{conversations,tool_executions}.py` additions | repository | CRUD/transaction | existing repository pattern implied by auth services | Research Pattern 4 |
| 10 | `backend/tests/integration/search/**` | test | request-response/CRUD | `backend/tests/integration/auth/**` | 03-VALIDATION.md |
| 11 | `backend/tests/security/test_search_*.py` | negative/security test | adversarial request-response | `backend/tests/security/test_principal_fail_closed.py`, `test_unknown_policy_state.py`, `test_secret_leakage.py` | 03-VALIDATION.md |
| 12 | `frontend/lib/search-session.ts` or chat-session extension | client/service/store | request-response/state machine | `frontend/lib/auth-session.ts` | UI-SPEC + Research Pattern 5 |
| 13 | `frontend/lib/search-readiness.ts` or readiness extension | client/helper | polling/transform | `frontend/lib/readiness.ts` | UI-SPEC + Research Pattern 6 |
| 14 | `frontend/components/chat/**` | component | event-driven/render | `frontend/components/account-access/**` | UI-SPEC component strategy |
| 15 | `frontend/tests/search-session.test.ts` | test | state machine | `frontend/tests/auth-session.test.ts` | 03-VALIDATION.md |
| 16 | `frontend/tests/search-rendering.test.tsx` | test | render/contract | `frontend/tests/readiness.test.ts` as style-of-assertion analog | 03-VALIDATION.md |

## Pattern Assignments

### Backend Route Pattern

**Applies to:** `backend/app/api/routes/search.py` or equivalent Phase 2 chat route extension.

**Analog:** `backend/app/api/routes/auth.py`

**Required shape:**

- inject `Settings`, `AsyncSession`, current time, and correlation ID from request state;
- validate transport input with Pydantic before service calls;
- map typed service outcomes to stable HTTP envelopes;
- set no provider-specific policy inside the route itself;
- never read search capability directly from unchecked browser claims.

### Backend Service Pattern

**Applies to:** `backend/app/services/search_coordinator.py`

**Analogs:** `backend/app/services/authentication.py`, `backend/app/services/registration.py`

**Required shape:**

- one service entry point per user turn;
- coordinator-owned policy check before worker call;
- database transaction for durable message/tool state changes;
- no raw HTTP/JSON branching scattered into routes;
- return a typed outcome object that already encodes the user-visible state enum.

### Settings and Readiness Pattern

**Applies to:** `backend/app/core/config.py`, `backend/app/core/provider_status.py`

**Analogs:** existing files

**Required shape:**

- extend existing `Settings` rather than creating a separate search-settings module;
- keep search-model and Google-key values under the same immutable settings object;
- extend readiness from `unconfigured|ready` to a richer search capability matrix without breaking existing callers;
- preserve safe error and redaction behavior from the current config layer.

### Security Helper Pattern

**Applies to:** `backend/app/security/search_capability.py` or equivalent

**Analogs:** `backend/app/security/access_tokens.py`, `backend/app/security/refresh_tokens.py`

**Required shape:**

- small pure functions for mint/validate/expire behavior;
- explicit audience/type/tool binding;
- no dependency on browser cookie state;
- no reuse of user refresh/access tokens as worker credentials.

### Persistence Pattern

**Applies to:** `backend/app/models/domain.py` and any repository extensions

**Analog:** existing `Conversation`, `Message`, and `ToolExecution` models

**Required shape:**

- extend `Message.message_metadata` instead of creating search-only duplicate message tables;
- persist correlated search state in `ToolExecution`;
- preserve immutable message ordering and assistant/user/tool role semantics;
- keep raw provider payloads behind an allowlist and separate from user-visible markdown content.

### Frontend State Pattern

**Applies to:** `frontend/lib/search-session.ts` or equivalent

**Analog:** `frontend/lib/auth-session.ts`

**Required shape:**

- explicit state-machine transitions captured in plain TypeScript;
- fetch abstraction injected for tests;
- no hidden auto-submit path after suggestion click;
- retry and degraded-state copy modeled in deterministic state transitions.

### Frontend Rendering Pattern

**Applies to:** `frontend/components/chat/**`

**Analogs:** `ActionButton.tsx`, `InlineAlert.tsx`, `StatusBadge.tsx`, `AuthModeSwitch.tsx`

**Required shape:**

- compact pills/alerts/buttons consistent with current account-access language;
- grounded evidence rendered inside the assistant message card, not as a global banner;
- separate source list and suggestion block components;
- no shadcn dependency or third-party registry blocks.

### Test Pattern

**Applies to:** backend and frontend search tests

**Analogs:** `backend/tests/integration/auth/**`, `backend/tests/security/*.py`, `frontend/tests/auth-session.test.ts`, `frontend/tests/readiness.test.ts`

**Required shape:**

- backend integration tests prove durable state and provider-call boundaries;
- backend security tests assert side effects, not just response wording;
- frontend tests stay deterministic by testing controller/state/render helpers with mocked fetch or serialized render assertions;
- use RED-first Wave 0 ownership for all missing search-specific test paths.

## Resolved Source Conflict

The roadmap says Phase 3 depends on Phase 2, but the current repository does not yet contain Phase 2 chat code. The approved UI contract resolves the execution-time ambiguity:

- if the Phase 2 shell exists in the implementation branch, extend it;
- if it does not exist, implement the minimum shell defined in `03-UI-SPEC.md` and keep the scope tightly limited to search-specific chat behavior.

The plan must therefore name concrete target files but allow "extend existing or create minimum equivalent" where the repository currently lacks the expected Phase 2 surface.

## Pattern Notes for the Planner

- Prefer `search.py`, `search_coordinator.py`, and `search-session.ts` style names over overly generic `tools.py` or `agent.py` top-level files.
- Keep Google worker code under `backend/app/ai/search_worker/` so the Python sandbox can later live under a sibling boundary rather than the same module.
- Reuse `frontend/tests/auth-session.test.ts` style controller testing before adding heavier client/browser tools.
- Reuse the current account-access component language; do not plan a visual rewrite as part of search.
