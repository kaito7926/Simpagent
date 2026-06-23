---
phase: 03-policy-controlled-google-search
verified: 2026-06-23T08:17:07Z
status: gaps_found
score: 4/5 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 0/5
  gaps_closed:
    - "Historical stale verification claimed no chat/search backend, no coordinator, no search worker, no frontend search UI, and no search tests. Current code now has those artifacts and wiring."
  gaps_remaining:
    - "Firecrawl-selected-but-unconfigured legacy /turns path returns search_unavailable with provider gemini instead of firecrawl."
  regressions: []
gaps:
  - truth: "User can visibly distinguish provider-specific search unavailable/failure states without hidden Gemini fallback."
    status: failed
    reason: "Rebuilt Docker search test fails: Firecrawl-unconfigured /api/conversations/{conversation_id}/turns returns state search_unavailable but labels provider as gemini."
    artifacts:
      - path: "backend/app/services/chat_turns.py"
        issue: "_refresh_search_runtime() re-resolves provider from settings/runtime override and can overwrite the route-supplied firecrawl provider with the settings default gemini in the unconfigured legacy turn path."
      - path: "backend/tests/integration/search/test_search_failure_states.py"
        issue: "test_firecrawl_without_key_returns_search_unavailable_without_gemini_fallback fails after --build."
    missing:
      - "Preserve the selected firecrawl provider on the search_unavailable branch for /api/conversations/{conversation_id}/turns when Firecrawl is selected but unconfigured, or route the same effective provider resolution used by the current chat coordinator into ChatTurnsService."
---

# Phase 3: Policy-Controlled Google Search Verification Report

**Phase Goal:** Authorized users can request current information and receive verifiable Google-grounded answers through a coordinator that cannot be overruled by model or tool content.
**Verified:** 2026-06-23T08:17:07Z
**Status:** gaps_found
**Re-verification:** Yes - replacing stale historical gaps-found verification.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Authorized user can request Google Search and receive answer text, claim-linked citations, and required Search Suggestions only when live grounding evidence is present. | VERIFIED | `backend/app/ai/search_worker/agent.py` builds a dedicated ADK agent with `GoogleSearchTool`; `backend/app/ai/search_worker/service.py` normalizes grounding; `frontend/components/chat/GroundedAnswer.tsx` renders badge, citations, sources, and Gemini-only trusted suggestions. Focused frontend search/admin suite passed 22/22. |
| 2 | User can visibly distinguish grounded answers from missing grounding, provider failure, timeout, and unavailable search capability. | FAILED | Most states are implemented and tested, but the rebuilt backend search suite fails `test_firecrawl_without_key_returns_search_unavailable_without_gemini_fallback`: the unavailable response is provider-labeled `gemini` instead of selected `firecrawl`. |
| 3 | Each turn selects only direct chat, Google Search, or Python from an explicit allowlist and permits at most one bounded invocation. | VERIFIED | `backend/app/agent/coordinator.py` routes only direct, `google_search`, or `python`; `test_turn_routing.py`, `test_search_budgets.py`, and `test_search_guardrails.py` cover unsupported modes, one search call, timeout, and no retry fanout. |
| 4 | Model output can propose but cannot authorize a tool; execution rechecks scope and uses a short-lived audience-bound capability instead of the user's bearer token. | VERIFIED | `ChatCoordinator._complete_search()` and `ChatTurnsService._handle_search_turn()` recheck `tool:websearch`; `backend/app/security/search_capability.py` mints RS256 audience-bound capability JWTs; `test_search_capability_token.py` rejects user access tokens and tampered tool bindings. |
| 5 | Search and Python remain separate typed credential boundaries, every tool decision has persisted correlated state, and untrusted prompt/search content cannot change policy, expose secrets, fetch internal URLs, or trigger arbitrary actions. | VERIFIED | Google Search worker uses only `GoogleSearchTool`; Python uses separate capability/client path; `ToolExecution` persists tool status/correlation; grounding code filters private/internal URLs and allowed metadata fields; security tests cover prompt injection, secret leakage, retention allowlist, and worker boundary. |

**Score:** 4/5 truths verified

## User Flow Coverage

| Step | Expected | Evidence in Codebase | Status |
|---|---|---|---|
| Authenticated user opens the app | Signed-in users land in the chat workspace, not the auth form. | `frontend/components/account-access/AccountAccessShell.tsx` renders `ChatWorkspace` for authenticated sessions. | VERIFIED |
| User chooses a websearch-capable turn | UI exposes explicit tool mode only when `tool:websearch` is present. | `ChatWorkspace.tsx` tracks `toolMode`, computes `searchEnabled`, and sends `tool_mode` through `frontend/lib/chat-api.ts`. | VERIFIED |
| Backend executes a permitted search | Backend rechecks owner/scope, mints a search capability, calls the search worker once, and persists the tool record. | `backend/app/agent/coordinator.py` and `backend/app/services/chat_turns.py`; tests in `backend/tests/integration/search` and `backend/tests/security/test_search_guardrails.py`. | VERIFIED |
| User sees grounded evidence | Grounded answers render citations, source list, and trusted Gemini Search Suggestions. | `AssistantMessageCard.tsx`, `GroundedAnswer.tsx`, `SearchSourceList.tsx`, `SearchSuggestionList.tsx`; frontend search rendering tests passed. | VERIFIED |
| User sees provider-honest unavailable state | If Firecrawl is selected but unconfigured, UI/backend evidence must say Firecrawl unavailable and must not fall back to Gemini. | Rebuilt test failed: response state is unavailable but provider is `gemini`. | FAILED |

## Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `backend/app/agent/coordinator.py` | Deterministic coordinator for direct/search/Python and policy rechecks | VERIFIED | Routes explicit/heuristic search and Python, records search/Python tool executions, uses capability credentials. Recent commit `3a0a55d` preserved injected ready search workers in this coordinator. |
| `backend/app/services/chat_turns.py` | Legacy `/turns` search contract and persisted state matrix | PARTIAL | Search scope/capability/persistence are substantive, but Firecrawl-unconfigured provider metadata regresses to `gemini` in the failing test. |
| `backend/app/ai/search_worker/agent.py` | Dedicated Google ADK worker | VERIFIED | Builds a single-purpose `google_search_worker` with exactly `GoogleSearchTool()`. |
| `backend/app/ai/search_worker/service.py` | Google/Firecrawl worker services and capability validation | VERIFIED | Validates capability claims before worker execution; uses ADK runner timeout and Firecrawl client boundary. |
| `backend/app/security/search_capability.py` | Short-lived internal search capability credential | VERIFIED | RS256 JWT with `aud`, `iss`, `sub`, `tool`, `conversation_id`, `correlation_id`, `iat`, `nbf`, `exp`, and `jti`; tests reject bearer access tokens. |
| `backend/app/core/provider_status.py` | Provider allowlist and readiness states | VERIFIED | Allows only `gemini`/`firecrawl`; distinguishes unconfigured, invalid provider, unsupported model, and ready. |
| `frontend/components/chat/*` and `frontend/lib/chat-api.ts` | Search UI rendering and live chat API wiring | VERIFIED | Authenticated workspace uses `/api/conversations` and `/messages`; frontend tests prove search rendering and provider-honest Firecrawl UI components. |
| `backend/tests/integration/search/*`, `backend/tests/security/test_search*.py`, `frontend/tests/search-*.ts*` | Search behavior, security, and rendering coverage | VERIFIED | Test files are substantive and mostly pass; one backend search test is currently failing and is the reported gap. |

## Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| Authenticated frontend | Live chat workspace | `AccountAccessShell` -> `ChatWorkspace` | WIRED | Root app renders auth shell; authenticated branch mounts `ChatWorkspace`. |
| `ChatWorkspace` | Chat API | `createConversationWithMessage()` / `sendMessage()` with `tool_mode` | WIRED | `frontend/lib/chat-api.ts` sends `auto`, `google_search`, or `python` to backend conversation routes. |
| Conversation routes | `ChatCoordinator` | `_chat_coordinator()` executor | WIRED | `backend/app/api/routes/chat.py` injects coordinator with principal scopes, provider state, workers, Python client, and correlation ID. |
| Coordinator | Search worker | `mint_search_capability()` then `search_worker.run()` | WIRED | User bearer token is not forwarded; worker validates search capability. |
| Search result | Persistence/rendering | `metadata["search"]`, `ToolExecution`, `assistantTurnFromMessage()` | WIRED | Messages retain search metadata; frontend reconstructs assistant turns from metadata. |
| Legacy `/turns` route | Provider-honest unavailable state | `ChatTurnsService._refresh_search_runtime()` | PARTIAL | The route works for many search states but fails Firecrawl-unconfigured provider preservation. |

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|---|---|---|---|---|
| `backend/app/agent/coordinator.py` | `search` metadata and `ToolExecution` | Principal scopes, runtime provider resolver, search worker result, DB session | Yes | FLOWING |
| `backend/app/services/chat_turns.py` | `SearchTurnResult.provider/state` | Route-supplied app state plus `_refresh_search_runtime()` | Partial | HOLLOW_EDGE for Firecrawl-unconfigured legacy route; provider becomes `gemini`. |
| `backend/app/ai/search_worker/grounding.py` | sources, citations, suggestions, queries | ADK grounding metadata | Yes | FLOWING; private/internal URLs and sensitive suggestions are filtered. |
| `frontend/components/chat/MessageList.tsx` | assistant search turn | `message.metadata.search` via `assistantTurnFromMessage()` | Yes | FLOWING |
| `frontend/components/chat/GroundedAnswer.tsx` | citations/sources/suggestions | Trusted backend search metadata | Yes | FLOWING; Firecrawl omits Google-only suggestions. |

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Frontend search/admin rendering contracts | `npm --prefix frontend test -- tests/search-session.test.ts tests/search-rendering.test.tsx tests/admin-evidence.test.tsx` | 22 passed | PASS |
| Backend search/security suite | `docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/integration/search/... tests/security/test_search... -x` | 26 passed, then failed on Firecrawl-unconfigured provider mismatch | FAIL |
| Focused rebuild of failing backend case | `docker compose -f compose.test.yaml run --rm --build backend-test pytest -q tests/integration/search/test_search_failure_states.py::test_firecrawl_without_key_returns_search_unavailable_without_gemini_fallback -q` | Failed: expected `firecrawl`, got `gemini` | FAIL |
| Local non-Docker backend pytest | `python -m pytest backend/tests/security/test_search_retention_allowlist.py backend/tests/security/test_search_prompt_injection.py backend/tests/security/test_search_secret_leakage.py -q` | Failed before tests: local environment lacks `fastapi` | SKIP |
| Orchestrator regression gates | User-provided Docker/frontend/typecheck gates | Backend regression 57 passed; frontend 49 passed; typecheck passed | PASS (external gate evidence) |

## Probe Execution

| Probe | Command | Result | Status |
|---|---|---|---|
| Conventional probes | `Get-ChildItem -Recurse scripts -Filter probe-*.sh` | No `scripts` directory | SKIPPED |
| Phase-declared probes | scanned Phase 03 markdown for `probe-*.sh` | No runnable phase probe declared; matches only research/stale verification wording | SKIPPED |

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| AUTHZ-04 | 03-01, 03-08 | Web Search requires `tool:websearch`; Python requires `tool:python`. | SATISFIED | Scope rechecks in coordinator/service; denied search test skips worker and records denied tool execution. |
| AUTHZ-07 | 03-01, 03-05 | Tool authorization checked immediately before execution and cannot be granted by model output. | SATISFIED | `_search_scope_allowed()` and `_handle_search_turn()` recheck scopes before worker calls; guardrail/security tests cover no-bearer and no worker on deny. |
| AGNT-01 | 03-01, 03-05 | Coordinator selects only direct chat, Google Search, or Python. | SATISFIED | `RequestedTool = Literal["google_search", "python"]`; direct path is separate; unknown frontend/backend modes are rejected. |
| AGNT-02 | 03-02, 03-05 | Model cannot authorize tools or alter policy. | SATISFIED | Worker instructions reject policy override/internal fetches; coordinator owns execution authorization. |
| AGNT-03 | 03-01, 03-05 | At most one bounded tool invocation per turn. | SATISFIED | Search guardrail and budget tests cover single worker call, timeout, and provider error without retry fanout. |
| AGNT-04 | 03-02, 03-05 | Search and Python use separate workers and credential boundaries. | SATISFIED | Google ADK worker service and Python sandbox client/capability paths are separate typed contracts. |
| AGNT-05 | 03-02, 03-05 | Internal tool requests use short-lived audience-bound capability credentials. | SATISFIED | Search capability JWT and Python capability code exist; tests reject user bearer token as worker capability. |
| AGNT-06 | 03-01, 03-03, 03-08 | Tool actions have persisted state and correlation ID. | SATISFIED | `ToolExecution` model; coordinator/service add executions; persistence tests cover lifecycle and retries. |
| AGNT-07 | 03-04, 03-05 | Prompts, outputs, and tool content are untrusted and do not expose secrets. | SATISFIED | Prompt-injection and secret-leakage tests; grounding filters sensitive queries/suggestions. |
| SRCH-01 | 03-02 | Dedicated Google ADK worker invokes built-in Google Search. | SATISFIED IN CODE | `build_google_search_agent()` uses a single `GoogleSearchTool`; note `.planning/REQUIREMENTS.md` checkbox still says pending and should be updated after the blocker is fixed. |
| SRCH-02 | 03-02, 03-05 | Capability checks distinguish configured/unsupported/unavailable/ready. | SATISFIED | `provider_status.py` and capability-check tests cover model family, invalid provider, Firecrawl key requirement, and no Gemini fallback intent. |
| SRCH-03 | 03-01, 03-07 | Grounded response transports required grounding fields without false grounded label. | SATISFIED | Grounding normalizer downgrades unsafe/missing evidence; tests cover missing-grounding. |
| SRCH-04 | 03-03, 03-07, 03-08 | Frontend safely renders citations and Google Search Suggestions. | SATISFIED | `GroundedAnswer`, source/suggestion components, and frontend search rendering tests. |
| SRCH-05 | 03-04, 03-05, 03-08 | Grounding persistence and telemetry retain only allowed fields and no click tracking. | SATISFIED | Metadata allowlists in `domain.py`/`chat_turns.py`; retention tests cover Firecrawl click tracking/raw payload rejection. |
| SRCH-06 | 03-02, 03-05, 03-08 | Search requests apply limits, timeouts, budgets, and safe failure behavior. | BLOCKED | Limits and timeout behavior are covered, but Firecrawl-unconfigured provider metadata fails the safe no-hidden-fallback failure branch. |
| SRCH-07 | 03-01, 03-03, 03-07, 03-08 | Search failures, missing grounding, and model unavailability are visibly distinct. | BLOCKED | UI states are distinct, but the failed backend response mislabels the selected provider, weakening visible provider-specific distinction. |
| SRCH-08 | 03-04, 03-05 | Search content cannot fetch internal URLs, escalate scope, execute arbitrary tools, or change policy. | SATISFIED | Prompt-injection tests and grounding URL filters cover internal URL rejection and policy override text. |

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---:|---|---|---|
| `backend/app/services/chat_turns.py` | 41 | `DIRECT_CHAT_PLACEHOLDER` remains in legacy `/turns` direct-chat path | WARNING | The authenticated production workspace uses the newer `/api/conversations` and `/messages` coordinator path for direct chat, but this legacy route can still mislead future tests/users if called directly. |
| `backend/app/services/chat_turns.py` | 540 | Runtime provider refresh can override route-supplied selected provider | BLOCKER | Causes Firecrawl-selected unconfigured search to be reported as Gemini unavailable in the failing test. |

No unreferenced `TBD`, `FIXME`, or `XXX` debt markers were found in the Phase 03 implementation files scanned.

## Human Verification Required After Gap Closure

These do not decide the current status because the automated blocker above takes precedence.

### 1. Search Suggestions UX

**Test:** Run the chat UI, produce a Gemini grounded answer with suggestions, click a suggestion.
**Expected:** Suggestions remain separate from Markdown; clicking pre-fills the composer, switches/focuses search intent, and does not auto-submit.
**Why human:** Layout, copy trust cues, and real browser focus behavior are partly visual/interactive.

### 2. Missing-Grounding Tone

**Test:** Trigger a missing-grounding fallback.
**Expected:** The assistant turn shows `có thể tham khảo`, has no grounded badge/citations/suggestions, and feels tentative rather than like a verified answer.
**Why human:** Tone and ambiguity are subjective despite automated copy checks.

### 3. Denied vs Unavailable Distinction

**Test:** Compare a no-scope user search turn with a configured-but-unavailable search turn.
**Expected:** The denied state says no search executed; unavailable says the selected provider is not ready and offers retry/switch guidance.
**Why human:** Evaluator-facing clarity and visual distinction need manual confirmation.

## Gaps Summary

Phase 03 is mostly implemented and substantially wired, but the current code does not pass the phase-owned backend search matrix. The blocking gap is provider honesty in the Firecrawl-unconfigured legacy `/turns` path: the state is correctly unavailable, but the provider metadata says `gemini`, contradicting the D-11/D-13 no-hidden-fallback contract and blocking SRCH-06/SRCH-07 closeout.

The stale historical verification debt is closed in code for backend routes, coordinator, search worker, frontend components, and tests. It should not be used as evidence for current status.

---

_Verified: 2026-06-23T08:17:07Z_
_Verifier: the agent (gsd-verifier)_
