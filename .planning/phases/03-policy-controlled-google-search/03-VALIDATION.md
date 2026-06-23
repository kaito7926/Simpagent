---
phase: 03
slug: policy-controlled-google-search
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-11
updated: 2026-06-23
---

# Phase 03 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Backend framework** | pytest `>=9,<10`, pytest-asyncio `>=1.4,<2`, HTTPX `>=0.28,<1` |
| **Frontend framework** | `node:test` via `tsx --test` |
| **Backend config file** | `backend/pyproject.toml` |
| **Frontend config file** | `frontend/package.json` |
| **Backend quick run command** | `docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/integration/search/test_search_capability_check.py tests/integration/search/test_search_persistence.py tests/security/test_search_retention_allowlist.py -x` |
| **Backend security quick command** | `docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/security/test_search_guardrails.py -x` |
| **Frontend quick run command** | `cd frontend && npm test -- tests/search-session.test.ts tests/search-rendering.test.tsx` |
| **Full suite command** | `docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/integration/search/test_search_capability_check.py tests/integration/search/test_search_persistence.py tests/security/test_search_retention_allowlist.py tests/integration/admin/test_admin_write.py tests/smoke/test_google_search_flow.py tests/smoke/test_admin_flow.py -x && cd frontend && npm test -- tests/search-session.test.ts tests/search-rendering.test.tsx tests/admin-evidence.test.tsx && npm run typecheck` |
| **Compose smoke command** | `docker compose up --build --wait && docker compose run --rm -e SIMPAGENT_RUN_SMOKE=true backend python -m pytest -q tests/smoke/test_google_search_flow.py tests/smoke/test_admin_flow.py -x` |
| **Estimated quick runtime** | Under 45 seconds after search-specific fixtures and tests exist |

Search-specific backend tests should continue to run against PostgreSQL 18 and real application-created sessions. Frontend tests should prefer controller/state tests and pure rendering assertions before introducing heavier browser tooling. The closeout provider matrix covers Gemini default search, Firecrawl admin override search, Firecrawl-selected-but-unconfigured `search_unavailable`, and admin override clear-to-default behavior. Firecrawl success smoke requires `FIRECRAWL_API_KEY` or `SIMPAGENT_FIRECRAWL_API_KEY_FILE`; without it, the assembled smoke must prove the D-11 fail-closed unconfigured branch.

---

## Sampling Rate

- **After every task commit:** Run the narrowest relevant backend or frontend search test, targeting under 45 seconds.
- **After every plan wave:** Run the backend search integration suite plus the frontend search-session/rendering suite.
- **After worker, policy, or grounding changes:** Also run prompt-injection, missing-grounding, unavailable, timeout, and no-bearer-forwarding tests.
- **Before `$gsd-verify-work`:** Start a fresh Compose topology, run the full backend search/security suite, the frontend search/admin suite, the SRCH-05 retention allowlist suite, and the end-to-end Gemini/Firecrawl grounded/degraded smoke matrix.
- **Max feedback latency:** 45 seconds for task-level checks; full topology checks run at wave and phase gates.

---

## Per-Task Verification Map

Task IDs and plan assignments are finalized by the planner. Every requirement below must appear in at least one plan task with the listed automated command or a stricter equivalent.

| Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| AUTHZ-04 | T-03 | Search requests without `tool:websearch` are denied before any provider call | security/integration | `docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/integration/search/test_search_authz.py` | Yes | COVERED |
| AUTHZ-07 | T-03 | Model/tool output cannot grant or override search authorization | security | `docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/security/test_search_guardrails.py -k authz` | Yes | COVERED |
| AGNT-01 | T-01 | Turn routing accepts only the explicit allowlist and records the chosen mode/state | integration | `docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/integration/search/test_turn_routing.py` | Yes | COVERED |
| AGNT-02 | T-03 | Search worker cannot trigger arbitrary tools or commands | security | `docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/security/test_search_guardrails.py -k worker_boundary` | Yes | COVERED |
| AGNT-03 | T-04 | At most one bounded tool invocation occurs per user turn | integration/security | `docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/integration/search/test_search_budgets.py` | Yes | COVERED |
| AGNT-04 | T-03 | Search and Python remain separate workers and credential boundaries | source/security | `docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/security/test_search_guardrails.py -k separate_worker` | Yes | COVERED |
| AGNT-05 | T-02 | Internal worker calls use a short-lived capability credential, not the user's bearer token | security | `docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/security/test_search_capability_token.py` | Yes | COVERED |
| AGNT-06 | T-05 | Requested, denied, started, succeeded, failed, and timed-out actions persist correlated state | integration | `docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/integration/search/test_search_persistence.py` | Yes | COVERED |
| AGNT-07 | T-02 / T-03 | Prompts, outputs, and tool content are treated as untrusted and never leak secrets | security | `docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/security/test_search_prompt_injection.py tests/security/test_search_secret_leakage.py` | Yes | COVERED |
| SRCH-01 | T-01 | Dedicated ADK worker invokes Google Search through a configured compatible Gemini 2 model | contract/integration | `docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/integration/search/test_search_worker_contract.py` | Yes | COVERED |
| SRCH-02 | T-01 | Startup/provider checks distinguish configured, unsupported, unavailable, and ready search capability | integration | `docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/integration/search/test_search_capability_check.py` | Yes | COVERED |
| SRCH-03 | T-05 | Grounded responses include normalized evidence and ungrounded responses are not mislabeled | integration | `docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/integration/search/test_grounding_contract.py` | Yes | COVERED |
| SRCH-04 | T-06 | Frontend safely renders citations and Search Suggestions for the same end user | frontend | `cd frontend && npm test -- tests/search-rendering.test.tsx tests/search-session.test.ts` | Yes | COVERED |
| SRCH-05 | T-02 | Persistence and telemetry retain only the allowed field set and perform no click tracking | source/security | `docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/security/test_search_retention_allowlist.py` | Yes | COVERED |
| SRCH-06 | T-04 | Search input, timeout, output, and retry budgets fail safely and visibly | integration | `docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/integration/search/test_search_failure_states.py` | Yes | COVERED |
| SRCH-07 | T-05 | Grounded, missing-grounding, unavailable, timeout, and denied states stay visually distinct | frontend/integration | `cd frontend && npm test -- tests/search-rendering.test.tsx && docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/integration/search/test_search_failure_states.py` | Yes | COVERED |
| SRCH-08 | T-03 | Search content cannot cause internal URL fetching, scope escalation, arbitrary tool execution, or policy changes | security | `docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/security/test_search_prompt_injection.py` | Yes | COVERED |

---

## Critical Security Scenarios

1. **No-search-on-deny:** a request lacking `tool:websearch` returns the denied state and produces no provider call.
2. **Missing-grounding honesty:** the worker returns answer text without grounding metadata and the system downgrades it to ordinary assistant styling with no badge/citations/suggestions.
3. **Prompt-injection containment:** retrieved content attempts to override policy, fetch internal URLs, or request another tool and is ignored.
4. **Capability-token boundary:** the worker receives only a short-lived audience-bound internal credential and never sees the user's bearer token.
5. **Provider unavailability matrix:** configured-but-unavailable model, worker timeout, and provider failure all persist distinct states and copy.
6. **Suggestion safety:** Search Suggestions prefill the composer and never auto-submit.
7. **One-tool-per-turn:** a single user turn cannot trigger both direct chat and search or more than one search attempt.
8. **Retention allowlist:** persisted message/tool metadata excludes disallowed raw provider or click-tracking fields.
9. **Dual-provider closeout:** assembled smoke proves Gemini default behavior, Firecrawl override behavior, Firecrawl-unconfigured fail-closed behavior, and override clear-to-default behavior through public search/admin entry points.

---

## Wave 0 Requirements

Wave 0 is complete. Every path below now exists in the repository and is linked to the plan that introduced it.

| Wave 0 path | Owner | Created before behavior |
|-------------|-------|-------------------------|
| `backend/tests/integration/search/test_search_authz.py` | 03-01 | Search authorization routing |
| `backend/tests/integration/search/test_turn_routing.py` | 03-01 | Explicit mode / one-tool-per-turn routing |
| `backend/tests/integration/search/test_search_worker_contract.py` | 03-01 | ADK worker implementation |
| `backend/tests/integration/search/test_search_capability_check.py` | 03-01 | Provider/model capability probing |
| `backend/tests/integration/search/test_grounding_contract.py` | 03-01 | Grounding normalization and honest state mapping |
| `backend/tests/integration/search/test_search_persistence.py` | 03-02 | Message/tool persistence semantics |
| `backend/tests/integration/search/test_search_failure_states.py` | 03-02 | Timeout/unavailable/provider-failed state matrix |
| `backend/tests/integration/search/test_search_budgets.py` | 03-02 | Input/output/retry/time budgets |
| `backend/tests/security/test_search_guardrails.py` | 03-01 | Boundary, authz, and worker/tool guardrails |
| `backend/tests/security/test_search_capability_token.py` | 03-02 | Internal capability credential boundary |
| `backend/tests/security/test_search_prompt_injection.py` | 03-04 | Prompt-injection and SSRF denial |
| `backend/tests/security/test_search_secret_leakage.py` | 03-04 | Secret redaction on search paths |
| `backend/tests/security/test_search_retention_allowlist.py` | 03-04 | Allowed-field persistence only |
| `frontend/tests/search-session.test.ts` | 03-03 | Client mode switch, retry, and suggestion-prefill controller behavior |
| `frontend/tests/search-rendering.test.tsx` | 03-03 | Grounded/degraded rendering contract |
| `backend/tests/smoke/test_google_search_flow.py` | 03-04 | End-to-end grounded/degraded search flow through Compose topology |
| `backend/tests/smoke/test_admin_flow.py` | 05-04 / 03-08 | End-to-end admin evidence, provider override set, denied, clear, and runtime search evidence through Compose topology |

---

## Provider Matrix Closeout 2026-06-23

Final Phase 03 enhancement validation must keep these commands synchronized:

1. **Backend provider matrix and SRCH-05 quick proof**
   - `docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/integration/search/test_search_capability_check.py tests/integration/search/test_search_persistence.py tests/security/test_search_retention_allowlist.py -x`
2. **Full enhancement regression**
   - `docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/integration/search/test_search_capability_check.py tests/integration/search/test_search_persistence.py tests/security/test_search_retention_allowlist.py tests/integration/admin/test_admin_write.py tests/smoke/test_google_search_flow.py tests/smoke/test_admin_flow.py -x && cd frontend && npm test -- tests/search-session.test.ts tests/search-rendering.test.tsx tests/admin-evidence.test.tsx && npm run typecheck`
3. **Assembled topology smoke**
   - `docker compose up --build --wait && docker compose run --rm -e SIMPAGENT_RUN_SMOKE=true backend python -m pytest -q tests/smoke/test_google_search_flow.py tests/smoke/test_admin_flow.py -x`

The smoke files and validation commands intentionally point at the same matrix: Gemini default search, Firecrawl override search, Firecrawl-selected-but-unconfigured `search_unavailable`, admin provider override set, denied, clear, and correlated evidence. `backend/tests/security/test_search_retention_allowlist.py` remains mandatory in quick and full commands so SRCH-05 retention/no-click-tracking coverage cannot disappear from closeout evidence.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Search Suggestions satisfy the approved Vietnamese UX while staying separate from markdown | SRCH-04, SRCH-07 | Copy, layout, and trust cues are partly human-facing | Run the chat UI, produce a grounded answer with suggestions, click a suggestion, confirm the composer prefills and does not auto-submit |
| Missing-grounding note feels clearly tentative but not like a hard failure | SRCH-03, SRCH-07 | Tone and ambiguity handling need human review | Trigger a no-grounding fallback and confirm the assistant turn shows `có thể tham khảo` without badge/citations/suggestions |
| Distinction between denied and unavailable is obvious to an evaluator | AUTHZ-04, SRCH-07 | Security semantics and UX semantics must align | Compare a no-scope user search turn with a configured-but-unavailable search turn in the UI |

---

## Validation Sign-Off

- [x] All plan tasks have an automated verification command or an explicit Wave 0 dependency.
- [x] No three consecutive implementation tasks lack automated verification.
- [x] Wave 0 owners above create every missing search-specific test path before its implementation task.
- [x] No watch-mode flags appear in verification commands.
- [x] Backend search feedback latency remains below 45 seconds where practical.
- [x] Frontend search controller/rendering tests run without browser-only tooling by default.
- [x] Grounding, denied, unavailable, timeout, prompt-injection, and retention-allowlist suites are green.
- [x] `nyquist_compliant` and `wave_0_complete` are now true because the planned Wave 0 test inventory exists and is passing.

**Approval:** validated on 2026-06-12; assembled Compose smoke execution and post-fix full rerun completed on 2026-06-13.

## Validation Audit 2026-06-12

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

- Verified backend search integration and security suites locally with PostgreSQL test data: `30 passed`.
- Verified frontend search session/rendering contract and static typing: `9 passed`, `typecheck passed`.
- Verified smoke-test presence for the public search flow: `tests/smoke/test_google_search_flow.py` exists but is skipped in this shell because the assembled Compose topology is not running and `docker` is unavailable on `PATH`.

## Validation Audit 2026-06-13

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 2 |
| Remaining smoke gaps | 0 |

- Fixed a Compose startup defect where Kong could not open `/var/log/simpagent/kong/error.log` from the shared `kong-logs` volume.
- Fixed Phase 03 backend test-clock drift by normalizing `test_now`, quoting `SIMPAGENT_TEST_NOW` in `compose.test.yaml`, and validating search capability JWT timing against the provided backend clock rather than PyJWT's wall clock.
- Reverified the full backend test topology with `docker compose -f compose.test.yaml run --rm backend-test pytest -q --tb=short`: `79 passed, 5 skipped in 5.59s`.
- Reverified the Phase 03 frontend suite with `docker compose run --rm frontend npm run test -- tests/search-session.test.ts tests/search-rendering.test.tsx`: `9 passed`.
- Reverified frontend static typing with `docker compose run --rm frontend npm run typecheck`: `passed`.
- Verified the assembled topology with `docker compose up --build --wait`.
- Verified live smoke execution with `docker compose run --rm -e SIMPAGENT_RUN_SMOKE=true backend python -m pytest -q tests/smoke --tb=short`: `5 passed in 11.61s`.
- Phase 03 now has executed public-stack smoke coverage for topology, account access, search, admin, and logging flows.
