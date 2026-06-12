---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: ready_for_phase_03
stopped_at: Completed 02-07-PLAN.md
last_updated: "2026-06-12T12:52:00.000Z"
last_activity: 2026-06-12 -- Phase 02 Plan 07 completed
progress:
  total_phases: 6
  completed_phases: 2
  total_plans: 15
  completed_plans: 15
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-08)

**Core value:** Users can safely authenticate and use an AI chatbot with controlled agent tools without crossing tenant, role, scope, network, or host-execution boundaries.
**Current focus:** Phase 03 — policy-controlled-google-search

## Current Position

Phase: 02 (private-direct-chat) — COMPLETE
Plan: 7 of 7
Status: Ready for Phase 03 planning
Last activity: 2026-06-12 -- Phase 02 Plan 07 completed

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**

- Total plans completed: 15
- Average duration: Phase 02 averaged about 30 min/plan across tracked plans
- Total execution time: Phase 02 tracked execution 207 min plus combined multi-session Phase 01 completion

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 Secure Platform and Account Access | 8 | Complete | Combined execution |
| 02 Private Direct Chat | 7 | 207 min | 30 min |

**Recent Trend:**

- Last 5 plans: 02-03, 02-04, 02-05, 02-06, 02-07 completed through the Phase 2 private direct-chat pass
- Trend: Stable

*Updated after each plan completion*
| Phase 02 P01 | 16 min | 2 tasks | 10 files |
| Phase 02 P02 | 29 min | 3 tasks | 9 files |
| Phase 02 P03 | 14 min | 2 tasks | 7 files |
| Phase 02 P04 | 17 min | 2 tasks | 30 files |
| Phase 02 P05 | 11 min | 2 tasks | 17 files |
| Phase 02 P06 | 104 min | 3 tasks | 10 files |
| Phase 02 P07 | 16 min | 2 tasks | 4 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Phase 01 uses Kong as the single public origin while FastAPI remains the authorization authority.
- Browser access tokens stay memory-only; refresh remains cookie-backed and CSRF-protected.
- Development demo seeding and secret initialization run as explicit Compose jobs; production admin creation stays deliberate and one-time.
- Provider-only readiness failures degrade the platform without blocking core account access.
- [Phase 02]: Cross-user conversation access returns a generic not-found envelope to avoid existence signals. — Missing and unauthorized conversation IDs should not be distinguishable.
- [Phase 02]: Conversation ownership is enforced in repository SQL predicates using both conversation ID and user ID. — Prevents BOLA by avoiding fetch-by-id then Python owner checks.
- [Phase 02]: Use the official OpenAI Python SDK package openai>=2,<3 after human legitimacy approval. — The package matched PyPI/OpenAI/GitHub evidence and was explicitly approved before manifest changes.
- [Phase 02]: Allow both SIMPAGENT_LLM_* and documented LLM_* provider env names for direct-chat settings. — This keeps Pydantic settings, .env.example, and Compose provider configuration aligned for custom LLM_API_BASE and LLM_MODEL.
- [Phase 02]: Provider calls happen after durable turn commit — Accepted user messages and pending assistant rows are committed before adapter.complete runs, avoiding long DB transactions and preserving retryable failed-turn state.
- [Phase 02]: Send retry uses provider settings boundary — Routes obtain OpenAIChatAdapter through Settings from Plan 02-02 so custom LLM_API_BASE and LLM_MODEL remain configurable.
- [Phase 02]: Provider failures persist failed assistant rows — Provider errors return provider_failed and store safe retry metadata plus correlation IDs without fabricated assistant content.
- [Phase 02]: Chat API helpers use AuthSessionController.authorizedJson exclusively. — This preserves memory-only access tokens and the existing refresh-on-401 session boundary.
- [Phase 02]: Non-streaming chat shows an optimistic pending row and reloads persisted state after provider failure. — Durable backend message state remains authoritative for retry and correlation display.
- [Phase 02]: Authenticated sessions replace the account card with ChatWorkspace on the root route. — Login, registration, recovery, and session expiry remain in the existing shell.
- [Phase 02]: Undo-delete is implemented as a write-scoped owner-constrained SQL update with a 6-second deleted_at window. — Keeps recovery short-lived, database-backed, and tenant-safe.
- [Phase 02]: Conversation list state labels expose only UI-safe values: Pending reply, Retry available, or null. — The sidebar does not leak provider internals or message counts from other owners.
- [Phase 02]: Delete remains the only row management action, with undo handled through the existing authorized session request path. — Phase 2 avoids rename, archive, share, export, model, and tool controls.
- [Phase 02]: Assistant Markdown is rendered only through a safe client component with no rehype-raw or dangerouslySetInnerHTML. — Raw HTML tags are escaped before Markdown parsing, unsafe hrefs render inertly, and links are scheme-allowlisted.
- [Phase 02]: Code blocks are inert text with clipboard-only behavior. — Syntax highlighting and copy state never execute displayed code.
- [Phase 02]: Next was patched to 16.2.9 with a narrow nested PostCSS override. — npm audit high/moderate findings are resolved while staying inside the selected >=16.2,<16.3 line.
- [Phase 02]: The final assembled smoke uses a deterministic app-level chat adapter injection. — This proves provider-boundary behavior without requiring live external LLM credentials.
- [Phase 02]: Phase 2 completed through the default Compose topology. — Backend, frontend, Kong, sandbox, and Postgres reached healthy after `docker compose up --build --wait`.

### Pending Todos

None.

### Blockers/Concerns

- Phase 3: Reconfirm current Gemini 2 availability, ADK grounding behavior, and Google retention terms before implementation.
- Phase 4: Verify effective Docker Desktop/WSL2 resource, seccomp, and network controls before claiming isolation.
- Phase 5: Validate Kong OSS support status and trusted proxy behavior for the chosen deployment profile.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Human verification | Demo credential clarity and readiness operator usefulness still need manual review | Open | 2026-06-10 |

## Session Continuity

Last session: 2026-06-12T12:52:00.000Z
Stopped at: Completed 02-07-PLAN.md
Resume file: None
