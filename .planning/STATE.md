---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: Ready to execute
stopped_at: Added Phase 07 sender-constrained session hardening workflow after Phase 06 closeout
last_updated: "2026-06-24T23:24:00.000Z"
progress:
  total_phases: 7
  completed_phases: 6
  total_plans: 46
  completed_plans: 44
  percent: 96
---

# Project State

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-06-08)

**Core value:** Users can safely authenticate and use an AI chatbot with controlled agent tools without crossing tenant, role, scope, network, or host-execution boundaries.
**Current focus:** Phase 07 — sender-constrained-sessions-and-cryptographic-hardening

## Current Position

Phase: 07 (sender-constrained-sessions-and-cryptographic-hardening) — EXECUTING
Plan: 4 of 5
Plan pack: Phase 07 workflow artifacts are being seeded after Phase 06 verification closeout
Known shipped slice: Phase 06 remains the last fully verified delivery slice; Phase 07 is the next hardening continuation
Latest verification: `06-VERIFICATION.md` passed on 2026-06-19 with 5/5 must-haves verified and 4/4 human checks passed

Progress: Phase 06 is fully verified; Phase 07 now captures the next cryptographic hardening slice while the historical Phase 03 planning/verification debt remains explicitly documented

## Performance Metrics

**Velocity:**

- Total completed plans tracked: 37
- Known shipped PRs: PR #1 (Phase 02) and PR #2 (integrated Phase 04 slice)
- Latest verified slice: Phase 06 closed through 5 plans and final verification on 2026-06-19

**By Phase:**

| Phase | Plans | Status | Notes |
|-------|-------|--------|-------|
| 01 Secure Platform and Account Access | 8/8 | Complete | Foundation shipped |
| 02 Private Direct Chat | 7/7 | Shipped | PR #1 |
| 03 Policy-Controlled Google Search | 4/4 | Historical debt visible | `03-VERIFICATION.md` remains stale/gaps-found and is intentionally not rewritten into a clean dependency-order completion story |
| 04 Isolated Python Execution | 5/5 | Shipped | PR #2 integrated slice; `04-VERIFICATION.md` passed |
| 05 Final Product Hardening, OAuth, Gateway, Administration, and Security Evidence | 8/8 | Complete | `05-VERIFICATION.md` passed on 2026-06-17 |
| 06 Adversarial Verification and Vietnamese Delivery | 5/5 | Verified | `06-VERIFICATION.md` passed on 2026-06-19; matrix and attack summaries regenerated |
| 07 Sender-Constrained Sessions and Cryptographic Hardening | 3/5 | In Progress | Replay foundations, OAuth PKCE transactions, and asymmetric one-time tool capabilities shipped |

**Recent Trend:**

- Most recent completed plans: 06-01, 06-02, 06-03, 06-04, 06-05
- Trend: Stable; Phase 06 verification and delivery passed, and Phase 07 has been opened as the next cryptographic hardening slice while the historical Phase 03 artifact debt remains called out

| Phase 03-policy-controlled-google-search P05 | 14 min | 3 tasks | 20 files |
| Phase 03-policy-controlled-google-search P06 | 11 min | 3 tasks | 15 files |
| Phase 03-policy-controlled-google-search P07 | 13 min | 2 tasks | 15 files |
| Phase 07 P01 | 30 min | 3 tasks | 7 files |
| Phase 07 P02 | 35 min | 3 tasks | 8 files |
| Phase 07 P03 | 50 min | 3 tasks | 14 files |

## Accumulated Context

### Decisions

Decisions are logged in `PROJECT.md` and phase `CONTEXT.md` files.
Recent decisions affecting current work:

- Phase 01 keeps Kong as the public origin while FastAPI remains the authorization authority.
- Browser access tokens stay memory-only; refresh remains cookie-backed and CSRF-protected.
- Phase 04 keeps Python natural-language-first with backend-owned reviewed profiles and a 15-minute sliding session window.
- Phase 05 keeps OAuth browser starts backend-owned, does not persist session material in browser storage, and keeps unconfigured providers visible as truthful disabled states.
- Phase 05 keeps the small-production profile environment-only and Cloudflare optional rather than mandatory.
- Phase 06 uses dedicated `security-tests/` attack assets and `docs/` Vietnamese delivery docs instead of treating scanner output or `.planning` alone as the evaluator deliverable.
- Phase 06 verified the shipped search behavior without erasing the historical Phase 03 planning/verification debt.
- Public gateway routing now includes `undo-delete` so adversarial verification hits the real backend authorization path instead of a frontend 404.
- Phase 07 scopes MVP cryptographic hardening to PKCE + sealed OAuth transactions, asymmetric one-time capability tokens, and DPoP-style sender-constrained sessions; WebAuthn step-up remains deferred beyond this phase.
- Phase 07 internal tool capabilities now use one-time asymmetric trust artifacts: search consumes `jti` values through the replay journal, and Python sandbox requests verify backend-issued RS256 JWTs with a public key.
- [Phase ?]: Keep Firecrawl behind existing google_search turn mode — Provider identity is metadata behind tool:websearch, not a new client-visible tool surface.
- [Phase ?]: Use HTTPX directly for Firecrawl Cloud — The plan required no new SDK; existing HTTPX keeps the provider boundary small and auditable.
- [Phase 03-policy-controlled-google-search]: Keep provider override in existing runtime settings — Plan 03-06 reuses agent_runtime_settings as nullable value data instead of introducing a new table.
- [Phase 03-policy-controlled-google-search]: Resolve websearch provider at request time — Admin reads, readiness, and live execution must use the same effective provider contract after overrides and clears.
- [Phase 03-policy-controlled-google-search]: Keep frontend provider labels metadata-driven — Plan 03-07 renders Google-specific badges and suggestions only for Gemini search turns while Firecrawl uses provider-honest or neutral websearch copy.

### Pending Todos

- Reconcile or refresh the stale Phase 03 verification chain when the team wants the roadmap to represent Search history cleanly.
- Keep future README/docs edits truthful about prototype limits, provider dependence, Docker-based sandbox boundaries, and the historical Phase 03 planning gap.

### Blockers/Concerns

- No active Phase 06 blocker remains; final matrix and attack suites passed from a clean Docker state on 2026-06-19.
- Phase 03 still remains a historical documentation/verification debt and is intentionally not presented as a clean dependency-order completion.
- Kong OSS scope, trusted-proxy assumptions, provider dependence, and Docker-based sandbox limits must stay explicit in evaluator-facing docs.
- After editing `sandbox/runtime/` or gateway routes, rebuild/restart the relevant containers before trusting stale local evidence.

### Quick Tasks Completed

See `.planning/quick/` for the completed quick-task history from 2026-06-14 through 2026-06-17. Those artifacts remain the source of truth for quick task execution details.

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260620-klg | Soạn brief nội dung và thiết kế slide thuyết trình phân tích bảo mật dự án SimpAgent | 2026-06-20 | 8fd7d05 | [260620-klg](./quick/260620-klg-so-n-brief-n-i-dung-v-thi-t-k-slide-thuy/) |
| 260620-l8q | Bổ sung giao tiếp mạng Docker an toàn và chống XSS trong Account Takeover | 2026-06-20 | 26a4fe8 | [260620-l8q](./quick/260620-l8q-b-sung-brief-slide-v-giao-ti-p-m-ng-an-t/) |
| 260624-3t5 | Fix Phase 03 Firecrawl websearch UAT UI issue report | 2026-06-24 | pending | [260624-3t5](./quick/260624-3t5-fix-phase-03-firecrawl-websearch-uat-ui-/) |

## Deferred Items

None currently tracked.

## Session Continuity

Last session: 2026-06-23T07:15:00Z
Stopped at: Added Phase 07 sender-constrained session hardening workflow after Phase 06 closeout
Resume file: `.planning/phases/07-sender-constrained-sessions-and-cryptographic-hardening/07-CONTEXT.md`
