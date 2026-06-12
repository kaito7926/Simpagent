---
phase: 02-private-direct-chat
plan: "02"
subsystem: ai
tags: [openai, provider-adapter, fastapi, configuration, pytest]
requires:
  - phase: 02-01
    provides: owner-scoped conversations and message turn-state schema foundation
provides:
  - OpenAI-compatible direct chat adapter boundary
  - Secret-safe provider settings for base URL, API key, model, timeout, and retry ceiling
  - Non-streaming provider payload and safe provider-error mapping tests
affects: [02-03, 02-04, 03-policy-controlled-google-search]
tech-stack:
  added: [openai>=2,<3]
  patterns: [thin provider adapter, app-owned provider error codes, direct-chat prompt boundary]
key-files:
  created:
    - backend/app/ai/__init__.py
    - backend/app/ai/prompts.py
    - backend/app/ai/schemas.py
    - backend/app/ai/chat_adapter.py
    - backend/tests/unit/ai/test_chat_adapter.py
  modified:
    - backend/pyproject.toml
    - backend/app/core/config.py
    - .env.example
    - compose.yaml
key-decisions:
  - "Use the official OpenAI Python SDK package `openai>=2,<3` after human legitimacy approval."
  - "Keep direct chat on Chat Completions with local database ownership as the source of truth; do not use provider-hosted conversation state."
  - "Allow both prefixed `SIMPAGENT_LLM_*` and documented `LLM_*` provider env names for the direct-chat settings."
patterns-established:
  - "Only `backend/app/ai/chat_adapter.py` imports and constructs `AsyncOpenAI`."
  - "Provider exceptions are normalized into `ChatProviderError` with safe code, retryability, and provider request ID only."
requirements-completed: [CHAT-07, CHAT-08, CHAT-11]
duration: 29 min
completed: 2026-06-12
---

# Phase 02 Plan 02: OpenAI-Compatible Provider Adapter Summary

**Configuration-driven non-streaming OpenAI-compatible chat adapter with safe provider error contracts**

## Performance

- **Duration:** 29 min
- **Started:** 2026-06-12T07:24:00Z
- **Completed:** 2026-06-12T07:53:01Z
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments

- Added RED tests first for provider settings, secret-safe configuration, exact non-streaming chat payload shape, and provider failure mapping.
- Approved and added the official `openai>=2,<3` SDK dependency; Docker resolved audited version `openai-2.41.1`.
- Added `OpenAIChatAdapter`, `ChatTurn`, `ChatCompletionResult`, direct SimpAgent prompt, and `ChatProviderError` safe metadata mapping.
- Added `LLM_TIMEOUT_SECONDS` and `LLM_MAX_RETRIES` settings and documented/propagated customizable LLM environment values.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create RED provider adapter and configuration tests** - `3f019ae` (test)
2. **Task 2: Approve OpenAI SDK dependency legitimacy before manifest update** - checkpoint approved by user; no code commit
3. **Task 3: Implement provider settings, prompt, schemas, and adapter** - `84a5bae` (feat)

**Plan metadata:** this docs commit

## Files Created/Modified

- `backend/tests/unit/ai/test_chat_adapter.py` - RED/GREEN provider adapter contract tests.
- `backend/pyproject.toml` - Adds approved `openai>=2,<3` dependency.
- `.env.example` - Documents `LLM_TIMEOUT_SECONDS` and `LLM_MAX_RETRIES` alongside existing LLM provider variables.
- `compose.yaml` - Passes `.env` LLM values into backend `SIMPAGENT_LLM_*` settings.
- `backend/app/core/config.py` - Adds LLM timeout/retry settings and accepts both `SIMPAGENT_LLM_*` and `LLM_*` env aliases for provider settings.
- `backend/app/ai/__init__.py` - Exports adapter and schema symbols.
- `backend/app/ai/prompts.py` - Defines the direct SimpAgent prompt with no search, file, tool, account, tenant, or hidden-data claims.
- `backend/app/ai/schemas.py` - Defines typed adapter turn/result contracts.
- `backend/app/ai/chat_adapter.py` - Constructs `AsyncOpenAI` from settings, sends non-streaming Chat Completions, and maps safe provider errors.

## Decisions Made

- The dependency gate was satisfied by PyPI, OpenAI official docs, GitHub source, and explicit user approval before changing `backend/pyproject.toml`.
- The adapter uses Chat Completions, `stream=False`, `temperature=0.3`, and `max_completion_tokens=800`; no tools, search, files, hosted conversations, MCP, or code-execution parameters are sent.
- `ChatProviderError` exposes only app-owned code, retryability, and provider request ID so provider bodies, prompts, API keys, bearer tokens, cookies, and assistant content are not leaked.

## Dependency Legitimacy Evidence

- PyPI package `openai` was listed as version `2.41.1`, released 2026-06-10, with description "The official Python library for the openai API", OpenAI owner, and verified GitHub project links.
- OpenAI official SDK documentation instructs Python users to install the SDK with `pip install openai`.
- GitHub source `openai/openai-python` declares `name = "openai"`, Apache-2.0 license, OpenAI author metadata, and repository/homepage links to `https://github.com/openai/openai-python`.
- User approval received after checkpoint: approved package/version evidence `openai` `2.41.1`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Wired Compose LLM variables through `.env`**
- **Found during:** Task 3
- **Issue:** `.env.example` documented unprefixed `LLM_API_BASE` and `LLM_MODEL`, but `compose.yaml` hardcoded backend `SIMPAGENT_LLM_API_BASE` and `SIMPAGENT_LLM_MODEL`, preventing custom provider values from the documented environment file in the local startup path.
- **Fix:** Changed backend Compose environment entries to interpolate `${LLM_API_BASE}`, `${LLM_MODEL}`, `${LLM_API_KEY_FILE}`, `${LLM_TIMEOUT_SECONDS}`, and `${LLM_MAX_RETRIES}` with safe defaults.
- **Files modified:** `compose.yaml`
- **Verification:** `docker compose -f compose.test.yaml run --rm -e SIMPAGENT_LLM_API_BASE=https://custom-provider.example/v1 -e SIMPAGENT_LLM_MODEL=custom-model -e SIMPAGENT_LLM_TIMEOUT_SECONDS=7 -e SIMPAGENT_LLM_MAX_RETRIES=0 backend-test python -c "..."`
- **Committed in:** `84a5bae`

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** The adjacent Compose change was required to satisfy the explicit custom provider configuration requirement. It did not add runtime behavior beyond provider configuration plumbing.

## Issues Encountered

- The first `docker compose run --rm backend pytest ...` RED attempt failed because the existing backend image did not contain the newly added test file. Rebuilding the backend image produced the intended RED failure on missing `app.ai`.
- `docker compose run --rm backend python -` later exposed a stale `migrate` service image against a development database stamped with `0003_chat_turn_state`. Rebuilding the backend-context Compose services resolved the verification environment.
- Docker reported pre-existing orphan containers during Compose test runs. They were unrelated to this plan and were not removed.

## User Setup Required

External provider credentials are required for live provider calls after later send-route plans:

- `LLM_API_KEY` or `LLM_API_KEY_FILE`
- `LLM_API_BASE` for a custom OpenAI-compatible provider
- `LLM_MODEL` for the provider-approved chat-completions model
- `LLM_TIMEOUT_SECONDS`
- `LLM_MAX_RETRIES`

## Known Stubs

None. Stub scan found only typed `None` defaults and test fake empty lists used to exercise provider error handling.

## Verification

- RED: `docker compose run --rm backend pytest -q tests/unit/ai/test_chat_adapter.py; if ($LASTEXITCODE -eq 0) { throw "Expected chat adapter tests to be RED" }` failed with `ModuleNotFoundError: No module named 'app.ai'` after rebuilding the backend image.
- GREEN: `docker compose run --rm backend pytest -q tests/unit/ai/test_chat_adapter.py -x` passed with `9 passed`.
- Test target: `docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/unit/ai/test_chat_adapter.py -x` passed with `9 passed`.
- Env override probe: `SIMPAGENT_LLM_API_BASE`, `SIMPAGENT_LLM_MODEL`, `SIMPAGENT_LLM_TIMEOUT_SECONDS`, and `SIMPAGENT_LLM_MAX_RETRIES` resolved to custom values in `Settings`.
- Import check: `rg -n "AsyncOpenAI" backend/app` shows `AsyncOpenAI` only in `backend/app/ai/chat_adapter.py`.

## Self-Check: PASSED

- Key files exist on disk.
- Task commits `3f019ae` and `84a5bae` exist in git history.
- Focused adapter verification passed through the plan's Docker Compose command.
- Dependency legitimacy evidence and user approval are recorded above.

## Next Phase Readiness

Ready for Plan 02-03 to consume `OpenAIChatAdapter` from the send/retry state machine without adding provider-specific logic to routes or persistence code.

---
*Phase: 02-private-direct-chat*
*Completed: 2026-06-12*
