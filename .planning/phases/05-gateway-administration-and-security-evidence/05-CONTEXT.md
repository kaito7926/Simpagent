# Phase 5: Final Product Hardening, OAuth, Gateway, Administration, and Security Evidence - Context

**Gathered:** 2026-06-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver the final coding phase for the prototype: Google and GitHub OAuth login, hardened DB-less Kong ingress, redacted correlated admin/security evidence, all Phase 5 admin surfaces, and a small production deployment profile sized for about 100 users/month. This phase must preserve the existing local email/password flow, protected refresh-token model, FastAPI authorization authority, Search/Python tool boundaries, and Phase 5 UI design contract.

</domain>

<decisions>
## Implementation Decisions

### Scope Promotion
- **D-01:** Google and GitHub OAuth are in Phase 5 scope, not deferred. Phase 5 now includes `IDEN-03`, `IDEN-06`, `IDEN-07`, and `IDEN-08`.
- **D-02:** Small production-readiness for about 100 users/month is in Phase 5 scope, not deferred. Phase 5 now includes `PRODREADY-01` through `PRODREADY-05`.
- **D-03:** Phase 5 remains a maintainable prototype target. The product must not claim high availability, distributed rate limiting, enterprise edge protection, or production-grade sandbox guarantees.

### OAuth Login
- **D-04:** Google and GitHub login use OAuth2/OIDC-safe redirect flows with CSRF state protection and provider secrets stored only in environment configuration.
- **D-05:** OAuth sessions land in the same short-lived access JWT plus protected HttpOnly refresh-token session model as local email/password login.
- **D-06:** OAuth provider identity is stored by `(provider, provider_subject)` so future logins do not depend on mutable provider email values.
- **D-07:** Existing local accounts are auto-linked only when the provider returns a verified email that matches the normalized local account email.
- **D-08:** Missing, unverified, or conflicting provider email identity fails closed. Do not link or provision in ambiguous cases.
- **D-09:** First-time OAuth login with a verified new email auto-provisions a standard `user` account with the same standard scopes as local registration.
- **D-10:** Google/GitHub provider buttons appear only when the corresponding backend provider is configured; missing config hides or disables that provider without breaking local login.

### Gateway Evidence
- **D-11:** Kong enforces gateway behavior, while FastAPI stores redacted correlated evidence.
- **D-12:** DB-less Kong remains the ingress control point for strict CORS, request-size limits, validated or propagated correlation IDs, route exposure, and useful route-specific rate limits.
- **D-13:** FastAPI evidence covers requests that reach the backend: auth failures, admin denials, refresh replay, tool decisions, provider calls, sandbox violations, admin actions, and correlation IDs.
- **D-14:** Gateway-only `429` or request-size denials that never reach FastAPI are represented through Kong configuration and verification/test evidence, not fabricated admin database rows.

### Admin Evidence Surfaces
- **D-15:** Phase 5 wires all six admin surfaces as real product surfaces: metrics, users, security events, tool executions, gateway evidence, and orchestration.
- **D-16:** Properly scoped admins can page through bounded evidence; ordinary users and under-scoped admins are denied with recorded redacted evidence.
- **D-17:** User mutation and orchestration writes remain gated by `admin:write`; read-only evidence is gated by `admin:read`.

### Redaction Detail Policy
- **D-18:** Admin tables show summaries only.
- **D-19:** Evidence detail drawers may show short expandable sanitized snippets after recursive redaction.
- **D-20:** Forbidden in admin evidence: raw prompts, full request bodies, provider payload dumps, bearer tokens, cookies, passwords, API keys, raw Google grounding JSON/HTML, full sandbox output, container IDs, host paths, and unredacted secret-bearing identifiers.
- **D-21:** Tests must include canary-secret and redaction assertions for snippets, not only table summaries.

### Cloudflare and Small Production Profile
- **D-22:** Cloudflare is an optional documented edge path; the local app remains primary and must still run through `docker compose up --build`.
- **D-23:** Implement the trusted proxy/origin configuration hooks needed by app and Kong.
- **D-24:** Document Cloudflare Tunnel, WAF, Turnstile integration points, Bot Fight Mode, TLS, source-IP trust, and Free-plan limitations without requiring Cloudflare for local demo.
- **D-25:** Production-readiness includes environment hardening, secure cookies/origins, OAuth redirect URL guidance, migrations, admin bootstrap, backup/restore, smoke checks, and explicit limits for about 100 users/month.

### UI Contract
- **D-26:** `05-UI-SPEC.md` remains the canonical frontend visual and interaction contract for Phase 5.
- **D-27:** The auth UI supports configured Google and GitHub provider buttons above a local-credentials divider while preserving local login/register.
- **D-28:** Unsupported social providers, dark mode, fake forgot-password links, fake app-launcher controls, raw logs, raw provider payloads, and secret-bearing debug chrome remain forbidden.

### the agent's Discretion
- Choose the exact OAuth callback route names, service/module names, database model split, and provider adapter boundaries, as long as the locked security and account-linking behavior holds.
- Choose the exact standard OAuth-created user scope set by reusing the existing standard local user scope defaults.
- Choose the exact gateway evidence UI copy for Kong-only events, as long as it does not imply FastAPI stored rows for requests it never received.
- Choose the exact snippet length limits, metadata allowlist, and drawer layout, as long as recursive redaction and canary-secret tests cover them.
- Choose the exact smoke-test packaging for the 100 users/month profile, as long as local credentials, Google login, GitHub login, gateway routing, admin evidence, chat, Search, and Python paths are covered.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and Requirements
- `.planning/ROADMAP.md` - Defines the expanded Phase 5 title, goal, requirements, and success criteria.
- `.planning/REQUIREMENTS.md` - Defines `AUTHZ-02`, `IDEN-03`, `IDEN-06` through `IDEN-08`, `GATE-01` through `GATE-08`, `OBS-01` through `OBS-07`, and `PRODREADY-01` through `PRODREADY-05`.
- `.planning/PROJECT.md` - Defines the security value, local Compose target, FastAPI authority, no-secret logging rule, and prototype-over-production-scale constraint.
- `.planning/STATE.md` - Records shipped prior slices, current concerns, and the Phase 5 scope expansion session.
- `.planning/phases/05-gateway-administration-and-security-evidence/05-UI-SPEC.md` - Canonical Phase 5 UI contract, including OAuth auth buttons, admin surfaces, evidence drawers, and redaction-sensitive UI constraints.

### Prior Phase Decisions
- `.planning/phases/01-secure-platform-and-account-access/01-CONTEXT.md` - Carries forward local auth, strict sessions, standard scope defaults, and FastAPI as the application authorization authority.
- `.planning/phases/02-private-direct-chat/02-CONTEXT.md` - Carries forward chat workspace, sidebar, safe Markdown/code rendering, and owner-only chat behavior.
- `.planning/phases/03-policy-controlled-google-search/03-CONTEXT.md` - Carries forward distinct Google Search states, citations, suggestions, and search policy boundaries.
- `.planning/phases/04-isolated-python-execution/04-CONTEXT.md` - Carries forward no Python mode toggle, one tool invocation per turn, Python result states, sandbox denial handling, and trusted-supervisor behavior.

### Existing Backend and Gateway Code
- `kong/kong.yml` - Current DB-less Kong configuration; Phase 5 must harden routes, methods, headers, CORS, rate limits, size limits, and correlation behavior here or in adjacent gateway config.
- `backend/app/api/routes/admin.py` - Existing admin route surface for users, security events, tool executions, metrics, orchestration, and user access updates.
- `backend/app/services/admin_evidence.py` - Existing admin evidence service and admin read/write enforcement pattern.
- `backend/app/schemas/admin.py` - Existing bounded admin response shapes.
- `backend/app/db/repositories/admin.py` - Existing admin evidence query layer.
- `backend/app/db/repositories/agent_settings.py` - Existing orchestration settings persistence.
- `backend/tests/integration/admin/test_admin_evidence.py` - Existing admin evidence negative and allow-path test coverage.
- `backend/tests/integration/admin/test_admin_write.py` - Existing admin write and orchestration settings tests.
- `backend/tests/smoke/test_admin_flow.py` - Existing assembled-stack admin smoke coverage.

### Existing Frontend Code
- `frontend/lib/admin-api.ts` - Existing admin API wrapper, currently focused on orchestration settings.
- `frontend/components/chat/ChatWorkspace.tsx` - Current shared chat/admin workspace and placeholder admin surfaces to wire with real data.
- `frontend/components/chat/ChatSidebar.tsx` - Current admin navigation entries and access gating.
- `frontend/components/settings/SettingsPage.tsx` - Existing settings/admin status surface.
- `frontend/components/account-access/AccountAccessShell.tsx` - Current auth shell to extend with configured Google and GitHub login.

### Original Brief and Local Guidance
- `AGENTS.md` - Project stack, GSD workflow, security, and documentation constraints.
- `prompt.md` - Original project brief and secure chatbot requirements, if present in the workspace.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/api/routes/admin.py` already exposes users, security events, tool executions, metrics, orchestration reads, orchestration writes, and user access updates.
- `backend/app/services/admin_evidence.py` already centralizes admin read/write checks, bounded paging, security-event recording on denial, and orchestration setting changes.
- `backend/app/schemas/admin.py` already has typed page, user, security event, tool execution, metrics, and orchestration response schemas.
- `frontend/lib/admin-api.ts` already uses `AuthSessionController.authorizedJson` for admin calls and can expand to users/events/tools/metrics/gateway endpoints.
- `frontend/components/chat/ChatWorkspace.tsx` already has admin navigation and placeholder screens for overview, users, security events, tool executions, gateway evidence, and orchestration.
- `kong/kong.yml` already runs DB-less routes for backend API, health/readiness, and frontend app with CORS configured.

### Established Patterns
- Backend route handlers are thin and delegate to service/repository layers.
- FastAPI repeats authoritative role/scope checks even when gateway screening exists.
- Admin denials are security events with correlation IDs.
- Frontend protected calls go through memory access tokens and refresh-on-401 behavior in the auth session controller.
- Admin UI is already access-gated by role/scopes and uses bounded placeholder surfaces rather than fake data.

### Integration Points
- OAuth should extend the existing identity/session boundary instead of creating a separate browser session type.
- OAuth provider identities need persistence adjacent to users/sessions, with migrations and negative tests for takeover cases.
- Gateway evidence should connect Kong config/test evidence to admin UI without pretending Kong-only denied requests were stored by FastAPI.
- Redaction should be applied before admin schemas return evidence snippets, not only in frontend rendering.
- Production-readiness should update environment templates, deployment docs, readiness/smoke checks, and operational runbook content without changing the local Compose startup contract.

</code_context>

<specifics>
## Specific Ideas

- Gateway evidence decision: Kong enforces, FastAPI stores evidence for requests that reach it, and Kong-only denials are represented through config and verification evidence.
- OAuth decision: auto-link only verified matching emails; first-time verified OAuth emails auto-provision standard users.
- Admin evidence decision: all six admin surfaces are Phase 5 scope.
- Redaction decision: summaries in tables, expandable sanitized snippets in drawers.
- Cloudflare decision: optional documented edge with implementation hooks for trusted proxy/origin config; local app remains primary.
- Production target: about 100 users/month, with explicit limitations rather than enterprise production claims.

</specifics>

<deferred>
## Deferred Ideas

None — user explicitly promoted OAuth and small production-readiness into Phase 5 scope.

</deferred>

---

*Phase: 5-Final Product Hardening, OAuth, Gateway, Administration, and Security Evidence*
*Context gathered: 2026-06-15*
