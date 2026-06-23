---
phase: 03-policy-controlled-google-search
verified: 2026-06-23T08:26:22Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 4/5
  gaps_closed:
    - "Firecrawl-selected-but-unconfigured legacy /turns path now returns search_unavailable with provider firecrawl and does not fall back to Gemini."
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Run the chat UI, produce a Gemini grounded answer with suggestions, click a suggestion."
    expected: "Suggestions remain separate from Markdown; clicking pre-fills the composer, switches/focuses search intent, and does not auto-submit."
    why_human: "Layout, copy trust cues, and real browser focus behavior are partly visual/interactive."
  - test: "Trigger a missing-grounding fallback."
    expected: "The assistant turn shows `có thể tham khảo`, has no grounded badge/citations/suggestions, and feels tentative rather than like a verified answer."
    why_human: "Tone and ambiguity are subjective despite automated copy checks."
  - test: "Compare a no-scope user search turn with a configured-but-unavailable search turn."
    expected: "The denied state says no search executed; unavailable says the selected provider is not ready and offers retry/switch guidance."
    why_human: "Evaluator-facing clarity and visual distinction need manual confirmation."
---

# Phase 3: Policy-Controlled Google Search Verification Report

**Phase Goal:** Authorized users can request current information and receive verifiable Google-grounded answers through a coordinator that cannot be overruled by model or tool content.
**Verified:** 2026-06-23T08:26:22Z
**Status:** human_needed
**Re-verification:** Yes - after provider metadata gap closure.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Authorized user can request Google Search and receive answer text, claim-linked citations, and required Search Suggestions only when live grounding evidence is present. | VERIFIED | `backend/app/ai/search_worker/agent.py` builds a dedicated ADK agent with `GoogleSearchTool`; `backend/app/ai/search_worker/service.py` normalizes grounding; `frontend/components/chat/GroundedAnswer.tsx` renders badge, citations, sources, and Gemini-only trusted suggestions. Earlier focused frontend search/admin suite passed 22/22. |
| 2 | User can visibly distinguish grounded answers from missing grounding, provider failure, timeout, and unavailable search capability. | VERIFIED | `backend/app/services/chat_turns.py` now preserves route-supplied non-ready provider metadata before returning `search_unavailable`; rebuilt focused test passed and the full Phase 03 search/security gate passed 44/44. Manual UX clarity checks remain below. |
| 3 | Each turn selects only direct chat, Google Search, or Python from an explicit allowlist and permits at most one bounded invocation. | VERIFIED | `backend/app/agent/coordinator.py` routes only direct, `google_search`, or `python`; integration/security tests cover unsupported modes, one search call, timeout, and no retry fanout. |
| 4 | Model output can propose but cannot authorize a tool; execution rechecks scope and uses a short-lived audience-bound capability instead of the user's bearer token. | VERIFIED | `ChatCoordinator._complete_search()` and `ChatTurnsService._handle_search_turn()` recheck `tool:websearch`; `backend/app/security/search_capability.py` mints RS256 audience-bound capability JWTs; `test_search_capability_token.py` rejects user access tokens and tampered tool bindings. |
| 5 | Search and Python remain separate typed credential boundaries, every tool decision has persisted correlated state, and untrusted prompt/search content cannot change policy, expose secrets, fetch internal URLs, or trigger arbitrary actions. | VERIFIED | Google Search worker uses only `GoogleSearchTool`; Python uses separate capability/client path; `ToolExecution` persists tool status/correlation; grounding code filters private/internal URLs and allowed metadata fields; security tests cover prompt injection, secret leakage, retention allowlist, and worker boundary. |

**Score:** 5/5 truths verified

## User Flow Coverage

| Step | Expected | Evidence in Codebase | Status |
|---|---|---|---|
| Authenticated user opens the app | Signed-in users land in the chat workspace, not the auth form. | `frontend/components/account-access/AccountAccessShell.tsx` renders `ChatWorkspace` for authenticated sessions. | VERIFIED |
| User chooses a websearch-capable turn | UI exposes explicit tool mode only when `tool:websearch` is present. | `ChatWorkspace.tsx` tracks `toolMode`, computes `searchEnabled`, and sends `tool_mode` through `frontend/lib/chat-api.ts`. | VERIFIED |
| Backend executes a permitted search | Backend rechecks owner/scope, mints a search capability, calls the search worker once, and persists the tool record. | `backend/app/agent/coordinator.py` and `backend/app/services/chat_turns.py`; tests in `backend/tests/integration/search` and `backend/tests/security/test_search_guardrails.py`. | VERIFIED |
| User sees grounded evidence | Grounded answers render citations, source list, and trusted Gemini Search Suggestions. | `AssistantMessageCard.tsx`, `GroundedAnswer.tsx`, `SearchSourceList.tsx`, `SearchSuggestionList.tsx`; frontend search rendering tests passed. | VERIFIED |
| User sees provider-honest unavailable state | If Firecrawl is selected but unconfigured, UI/backend evidence says Firecrawl unavailable and does not fall back to Gemini. | `test_firecrawl_without_key_returns_search_unavailable_without_gemini_fallback` passed after rebuild: provider remains `firecrawl`, `tool_executed` is false, and the injected Gemini worker receives zero calls. | VERIFIED |

## Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `backend/app/agent/coordinator.py` | Deterministic coordinator for direct/search/Python and policy rechecks | VERIFIED | Routes explicit/heuristic search and Python, records search/Python tool executions, uses capability credentials. Commit `3a0a55d` preserved injected ready search workers in this coordinator. |
| `backend/app/services/chat_turns.py` | Legacy `/turns` search contract and persisted state matrix | VERIFIED | Commit `4f8df9b` preserves route-supplied provider/status for selected but non-ready providers; focused Firecrawl-unconfigured test passed locally. |
| `backend/app/ai/search_worker/agent.py` | Dedicated Google ADK worker | VERIFIED | Builds a single-purpose `google_search_worker` with exactly `GoogleSearchTool()`. |
| `backend/app/ai/search_worker/service.py` | Google/Firecrawl worker services and capability validation | VERIFIED | Validates capability claims before worker execution; uses ADK runner timeout and Firecrawl client boundary. |
| `backend/app/security/search_capability.py` | Short-lived internal search capability credential | VERIFIED | RS256 JWT with `aud`, `iss`, `sub`, `tool`, `conversation_id`, `correlation_id`, `iat`, `nbf`, `exp`, and `jti`; tests reject bearer access tokens. |
| `backend/app/core/provider_status.py` | Provider allowlist and readiness states | VERIFIED | Allows only `gemini`/`firecrawl`; distinguishes unconfigured, invalid provider, unsupported model, and ready. |
| `frontend/components/chat/*` and `frontend/lib/chat-api.ts` | Search UI rendering and live chat API wiring | VERIFIED | Authenticated workspace uses `/api/conversations` and `/messages`; frontend tests prove search rendering and provider-honest Firecrawl UI components. |
| `backend/tests/integration/search/*`, `backend/tests/security/test_search*.py`, `frontend/tests/search-*.ts*` | Search behavior, security, and rendering coverage | VERIFIED | Current rebuilt backend Phase 03 search/security gate passed 44/44; focused Firecrawl provider metadata regression passed. |

## Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| Authenticated frontend | Live chat workspace | `AccountAccessShell` -> `ChatWorkspace` | WIRED | Root app renders auth shell; authenticated branch mounts `ChatWorkspace`. |
| `ChatWorkspace` | Chat API | `createConversationWithMessage()` / `sendMessage()` with `tool_mode` | WIRED | `frontend/lib/chat-api.ts` sends `auto`, `google_search`, or `python` to backend conversation routes. |
| Conversation routes | `ChatCoordinator` | `_chat_coordinator()` executor | WIRED | `backend/app/api/routes/chat.py` injects coordinator with principal scopes, provider state, workers, Python client, and correlation ID. |
| Coordinator | Search worker | `mint_search_capability()` then `search_worker.run()` | WIRED | User bearer token is not forwarded; worker validates search capability. |
| Search result | Persistence/rendering | `metadata["search"]`, `ToolExecution`, `assistantTurnFromMessage()` | WIRED | Messages retain search metadata; frontend reconstructs assistant turns from metadata. |
| Legacy `/turns` route | Provider-honest unavailable state | `ChatTurnsService._refresh_search_runtime()` | WIRED | Non-ready selected providers now return early with the existing provider preserved and no worker execution. |

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|---|---|---|---|---|
| `backend/app/agent/coordinator.py` | `search` metadata and `ToolExecution` | Principal scopes, runtime provider resolver, search worker result, DB session | Yes | FLOWING |
| `backend/app/services/chat_turns.py` | `SearchTurnResult.provider/state` | Route-supplied app state plus `_refresh_search_runtime()` | Yes | FLOWING; Firecrawl-unconfigured remains `firecrawl` and does not call Gemini. |
| `backend/app/ai/search_worker/grounding.py` | sources, citations, suggestions, queries | ADK grounding metadata | Yes | FLOWING; private/internal URLs and sensitive suggestions are filtered. |
| `frontend/components/chat/MessageList.tsx` | assistant search turn | `message.metadata.search` via `assistantTurnFromMessage()` | Yes | FLOWING |
| `frontend/components/chat/GroundedAnswer.tsx` | citations/sources/suggestions | Trusted backend search metadata | Yes | FLOWING; Firecrawl omits Google-only suggestions. |

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Focused provider metadata closure | `docker compose -f compose.test.yaml run --rm --build backend-test pytest -q tests/integration/search/test_search_failure_states.py::test_firecrawl_without_key_returns_search_unavailable_without_gemini_fallback` | 1 passed | PASS |
| Backend Phase 03 search/security gate | `docker compose -f compose.test.yaml run --rm --build backend-test pytest -q tests/integration/search tests/security/test_search_capability_token.py tests/security/test_search_guardrails.py tests/security/test_search_prompt_injection.py tests/security/test_search_secret_leakage.py tests/security/test_search_retention_allowlist.py -x` | 44 passed | PASS |
| Frontend search/admin rendering contracts | `npm --prefix frontend test -- tests/search-session.test.ts tests/search-rendering.test.tsx tests/admin-evidence.test.tsx` | 22 passed in prior Phase 03 verification evidence | PASS |
| Orchestrator regression gates | User-provided backend/frontend/typecheck/schema gates | Backend cross-phase 57 passed; frontend regression 49 passed; frontend typecheck passed; schema drift false; codebase drift skipped/no-structure-md | PASS (external gate evidence) |

## Probe Execution

| Probe | Command | Result | Status |
|---|---|---|---|
| Conventional probes | `Get-ChildItem -Recurse scripts -Filter probe-*.sh` | No `scripts` directory in prior scan; no phase probe declared in 03-08 evidence | SKIPPED |
| Phase-declared probes | Phase 03 markdown scan | No runnable `probe-*.sh` declared for this closeout | SKIPPED |

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
| SRCH-01 | 03-02 | Dedicated Google ADK worker invokes built-in Google Search. | SATISFIED IN CODE | `build_google_search_agent()` uses a single `GoogleSearchTool`; `.planning/REQUIREMENTS.md` still has a stale unchecked box. |
| SRCH-02 | 03-02, 03-05 | Capability checks distinguish configured/unsupported/unavailable/ready. | SATISFIED | `provider_status.py` and capability-check tests cover model family, invalid provider, Firecrawl key requirement, and no Gemini fallback intent. |
| SRCH-03 | 03-01, 03-07 | Grounded response transports required grounding fields without false grounded label. | SATISFIED | Grounding normalizer downgrades unsafe/missing evidence; tests cover missing-grounding. |
| SRCH-04 | 03-03, 03-07, 03-08 | Frontend safely renders citations and Google Search Suggestions. | SATISFIED | `GroundedAnswer`, source/suggestion components, and frontend search rendering tests. |
| SRCH-05 | 03-04, 03-05, 03-08 | Grounding persistence and telemetry retain only allowed fields and no click tracking. | SATISFIED | Metadata allowlists in `domain.py`/`chat_turns.py`; retention tests cover Firecrawl click tracking/raw payload rejection. |
| SRCH-06 | 03-02, 03-05, 03-08 | Search requests apply limits, timeouts, budgets, and safe failure behavior. | SATISFIED | Full search/security gate passed; Firecrawl-unconfigured provider metadata now remains provider-honest without hidden Gemini fallback. |
| SRCH-07 | 03-01, 03-03, 03-07, 03-08 | Search failures, missing grounding, and model unavailability are visibly distinct. | SATISFIED AUTOMATED / HUMAN UX PENDING | Automated state/provider checks pass; remaining visual distinction is listed under human verification. |
| SRCH-08 | 03-04, 03-05 | Search content cannot fetch internal URLs, escalate scope, execute arbitrary tools, or change policy. | SATISFIED | Prompt-injection tests and grounding URL filters cover internal URL rejection and policy override text. |

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---:|---|---|---|
| `backend/app/services/chat_turns.py` | 41 | `DIRECT_CHAT_PLACEHOLDER` remains in legacy `/turns` direct-chat path | WARNING | Pre-existing warning outside the Phase 03 search closeout; authenticated production workspace uses the newer `/api/conversations` and `/messages` coordinator path for direct chat. |

No unreferenced `TBD`, `FIXME`, or `XXX` debt markers were found in the Phase 03 implementation files scanned.

## Human Verification Required

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

No automated Phase 03 gap remains. The previous provider metadata blocker is closed by `4f8df9b` and verified with a rebuilt focused Docker test plus the full 44-test Phase 03 search/security gate.

Status is `human_needed`, not `passed`, because the remaining criteria are visual/manual UX checks for search suggestions, missing-grounding tone, and denied-versus-unavailable clarity.

---

_Verified: 2026-06-23T08:26:22Z_
_Verifier: the agent (gsd-verifier)_
