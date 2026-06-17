---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: Phase complete — ready for verification
stopped_at: Completed 05-08-PLAN.md
last_updated: "2026-06-16T10:19:42.810Z"
progress:
  total_phases: 6
  completed_phases: 5
  total_plans: 32
  completed_plans: 32
  percent: 83
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-08)

**Core value:** Users can safely authenticate and use an AI chatbot with controlled agent tools without crossing tenant, role, scope, network, or host-execution boundaries.
**Current focus:** Phase 05 — gateway-administration-and-security-evidence

## Current Position

Phase: 05 (gateway-administration-and-security-evidence) — EXECUTING
Plan: 8 of 8
Roadmap order complete: Phases 01-02
Integrated shipped slice: Phase 04 (isolated-python-execution) - PR #2
Latest verification: `04-VERIFICATION.md` passed on 2026-06-13 with 5/5 end-to-end truths verified

Progress: 20/20 shipped plans tracked, Phase 05 Planned

## Performance Metrics

**Velocity:**

- Total shipped plans: 20
- Total shipped PRs: PR #1 (Phase 02) and PR #2 (integrated Phase 04 slice)
- Latest shipped slice: Phase 04 closed through 5 plans and final verification on 2026-06-13

**By Phase:**

| Phase | Plans | Status | Notes |
|-------|-------|--------|-------|
| 01 Secure Platform and Account Access | 8/8 | Complete | Foundation shipped |
| 02 Private Direct Chat | 7/7 | Shipped | PR #1 |
| 03 Policy-Controlled Google Search | 0/TBD | Artifact closeout pending | `03-VERIFICATION.md` is stale and no plan/summaries are present |
| 04 Isolated Python Execution | 5/5 | Shipped | PR #2 integrated slice; `04-VERIFICATION.md` passed |
| 05 Gateway, Administration, and Security Evidence | 8/8 | Planned | Ready for execution |

**Recent Trend:**

- Most recent shipped plans: 04-01, 04-02, 04-03, 04-04, 04-05
- Trend: Stable; backend, frontend, smoke, and Compose gates were all green in the closing verification pass

| Phase 05 P02 | 18 min | 3 tasks | 17 files |
| Phase 05-gateway-administration-and-security-evidence P04 | 16 min | 3 tasks | 11 files |
| Phase 05-gateway-administration-and-security-evidence P05 | 15 min | 3 tasks | 8 files |
| Phase 05-gateway-administration-and-security-evidence P03 | 13 min | 2 tasks | 14 files |
| Phase 05-gateway-administration-and-security-evidence P06 | 12 min | 3 tasks | 8 files |
| Phase 05-gateway-administration-and-security-evidence P07 | 18 min | 3 tasks | 8 files |
| Phase 05-gateway-administration-and-security-evidence P09 | 7 min | 2 tasks | 5 files |
| Phase 05-gateway-administration-and-security-evidence P08 | 13 min | 3 tasks | 9 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Phase 01 uses Kong as the single public origin while FastAPI remains the authorization authority.
- Browser access tokens stay memory-only; refresh remains cookie-backed and CSRF-protected.
- Development demo seeding and secret initialization run as explicit Compose jobs; production admin creation stays deliberate and one-time.
- Provider-only readiness failures degrade the platform without blocking core account access.
- [Phase 02]: Conversation ownership is enforced in repository SQL predicates using both conversation ID and user ID.
- [Phase 02]: Assistant Markdown is rendered only through a safe client component with no `rehype-raw` or `dangerouslySetInnerHTML`.
- [Phase 04]: Chat stays natural-language-first; the backend coordinator decides when Python is implied instead of exposing a mode toggle.
- [Phase 04]: Python profile choice stays backend-owned: default `python-basic-v1`, narrow elevation to `python-data-v1`.
- [Phase 04]: Python session state uses a 15-minute sliding window reset on accepted execution and cleaned up lazily on access.
- [Phase 04]: Worker-start failures retry once only; callers cannot choose runtime mounts, namespaces, commands, or secrets.
- [Phase 04]: Runtime results are returned through a supervisor log marker because the worker workspace is tmpfs.
- [Phase 05]: Authlib approved and pinned for Google OAuth — The package-legitimacy checkpoint was explicitly approved before adding Authlib>=1.7,<2, satisfying the Phase 5 supply-chain gate.
- [Phase 05]: Admin Overview uses backend-owned bounded aggregate counters, and Orchestration write confirmations remain UI-side guardrails with FastAPI `admin:write` enforcement as the authority.
- [Phase 05]: Kong JWT screening was not enabled on live app routes because Compose development JWT keys are generated at runtime while DB-less Kong config is static; FastAPI remains the authorization authority.
- [Phase 05]: Gateway config assertions that need repo-root files are skipped in backend-only containers and backed by direct host-side Kong config parsing.
- [Phase 05-gateway-administration-and-security-evidence]: GitHub OAuth reuses the existing backend OAuth service and first-party refresh-cookie session model. — This preserves local/Google session semantics and avoids a second browser session path.
- [Phase 05-gateway-administration-and-security-evidence]: GitHub identity is resolved by stable provider subject before any verified-email linking attempt. — This satisfies D-06/D-08 and prevents mutable provider email from becoming the login key.
- [Phase 05-gateway-administration-and-security-evidence]: Admin evidence redaction runs in the backend service layer before schema serialization. — This ensures secrets and raw operational payloads are removed before admin contracts leave FastAPI.
- [Phase 05-gateway-administration-and-security-evidence]: Gateway-only 429/413 evidence is exposed from Kong-backed service contracts instead of fabricated FastAPI security_events rows. — This preserves D-14 truthfulness for requests blocked before the backend.
- [Phase 05-gateway-administration-and-security-evidence]: Plan 05-06 keeps HTTP route exposure out of scope; Plan 05-07 can consume the service contract. — This preserves the planned slice boundary while giving the next plan a typed backend contract.
- [Phase 05-gateway-administration-and-security-evidence]: Gateway evidence is exposed through the existing AdminEvidenceService admin:read gate. — Preserves FastAPI as the admin authorization authority while adding the final gateway evidence route.
- [Phase 05-gateway-administration-and-security-evidence]: Admin evidence detail drawers render only row fields and backend-sanitized snippets. — Keeps D-19/D-20 redaction boundaries visible in the shared shell and avoids raw payload viewers.
- [Phase 05-gateway-administration-and-security-evidence]: OAuth provider buttons are derived from backend readiness components instead of hardcoded frontend assumptions. — Keeps the auth shell truthful when Google or GitHub credentials are missing.
- [Phase 05-gateway-administration-and-security-evidence]: OAuth starts by browser navigation to backend-owned start routes and does not persist session material in browser storage. — Preserves the existing first-party refresh-cookie session boundary and avoids localStorage/sessionStorage token handling.
- [Phase 05-gateway-administration-and-security-evidence]: Unconfigured Google or GitHub providers remain visible as factual disabled states while local credentials stay available. — Satisfies provider-readiness truthfulness without blocking local account access.
- [Phase ?]: [Phase 05-gateway-administration-and-security-evidence]: The small-production profile stays environment-only and optional; local Compose remains the primary demo path.
- [Phase ?]: [Phase 05-gateway-administration-and-security-evidence]: Cloudflare is documented as an optional edge in front of Kong with explicit trusted-proxy/source-IP assumptions, not as mandatory enterprise protection.
- [Phase ?]: [Phase 05-gateway-administration-and-security-evidence]: Backend profile tests read root-level deployment artifacts through read-only Compose mounts instead of copying production docs into the backend package.

### Pending Todos

- Reconcile or recreate Phase 03 planning artifacts so the roadmap can represent Search status accurately.
- Decide whether Phase 05 planning starts immediately or only after the Phase 03 metadata debt is repaired.

### Blockers/Concerns

- Phase 03 still lacks dedicated plan/summaries and refreshed verification artifacts, so dependency-order completion is not fully represented in `.planning`.
- Phase 05 still needs Kong OSS support and trusted-proxy assumptions revalidated for the chosen deployment profile.
- After editing `sandbox/runtime/`, rebuild the runtime image or restart the stack before trusting stale local worker containers.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260614-m6i | Thêm ngày hiện tại vào system prompt để websearch chính xác hơn | 2026-06-14 | uncommitted | [260614-m6i-th-m-ng-y-hi-n-t-i-v-o-system-prompt-web](./quick/260614-m6i-th-m-ng-y-hi-n-t-i-v-o-system-prompt-web/) |
| 260614-mmh | Gọi thêm LLM để summarize kết quả của WebSearchAgent và Python Agent | 2026-06-14 | uncommitted | [260614-mmh-g-i-th-m-llm-summarize-k-t-qu-c-a-websea](./quick/260614-mmh-g-i-th-m-llm-summarize-k-t-qu-c-a-websea/) |
| 260614-s42 | Xây dựng API để người dùng chủ động gọi Agent Web Search và Agent Python Sandbox, kèm ghi chú UI cho hai nút tích chọn | 2026-06-14 | uncommitted | [260614-s42-x-y-d-ng-api-ng-i-d-ng-ch-ng-g-i-agent-w](./quick/260614-s42-x-y-d-ng-api-ng-i-d-ng-ch-ng-g-i-agent-w/) |
| 260615-pzk | Fix frontend codeblock rendering, replace SimpAgent logos with provided AuroraGuard mark, and center signed-out message on sign-in | 2026-06-15 | uncommitted | [260615-pzk-fix-frontend-codeblock-rendering-replace](./quick/260615-pzk-fix-frontend-codeblock-rendering-replace/) |
| 260615-qbg | Change logo circle background to white | 2026-06-15 | uncommitted | [260615-qbg-change-logo-circle-background-to-white](./quick/260615-qbg-change-logo-circle-background-to-white/) |
| 260615-qgv | Clip logo overflow inside white circular container | 2026-06-15 | uncommitted | [260615-qgv-clip-logo-overflow-inside-white-circular](./quick/260615-qgv-clip-logo-overflow-inside-white-circular/) |
| 260617-deh | Improve Administration and Settings UI layout/text containment, add Google/GitHub OAuth icons, and switch to a Vietnamese-friendly font | 2026-06-17 | uncommitted | [260617-deh-improve-administration-and-settings-ui-l](./quick/260617-deh-improve-administration-and-settings-ui-l/) |
| 260617-ese | Enlarge Administration users and gateway evidence tables and highlight important columns | 2026-06-17 | uncommitted | [260617-ese-enlarge-administration-users-and-gateway](./quick/260617-ese-enlarge-administration-users-and-gateway/) |
| 260617-gsv | Fix Administration evidence table horizontal clipping by using available workspace width | 2026-06-17 | uncommitted | [260617-gsv-fix-administration-evidence-table-horizo](./quick/260617-gsv-fix-administration-evidence-table-horizo/) |
| 260617-ic5 | Add visible horizontal scrollbar for Administration evidence tables | 2026-06-17 | uncommitted | [260617-ic5-add-visible-horizontal-scrollbar-for-adm](./quick/260617-ic5-add-visible-horizontal-scrollbar-for-adm/) |
| 260617-ij4 | Make Administration evidence table horizontal mouse wheel scrolling work in Chrome | 2026-06-17 | uncommitted | [260617-ij4-make-administration-evidence-table-horiz](./quick/260617-ij4-make-administration-evidence-table-horiz/) |

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Human verification | Demo credential clarity and readiness operator usefulness still need manual review | Open | 2026-06-10 |

## Session Continuity

Last session: 2026-06-16T10:19:42.803Z
Stopped at: Completed 05-08-PLAN.md
Resume file: None
