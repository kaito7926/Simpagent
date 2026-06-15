# Phase 5: Final Product Hardening, OAuth, Gateway, Administration, and Security Evidence - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-15
**Phase:** 5-Final Product Hardening, OAuth, Gateway, Administration, and Security Evidence
**Areas discussed:** Scope expansion, Gateway evidence source, OAuth account behavior, Admin evidence depth, Redaction detail policy, Cloudflare and trusted proxy story

---

## Scope Expansion

| Option | Description | Selected |
|--------|-------------|----------|
| Defer OAuth and production-readiness | Keep Phase 5 to original gateway/admin/evidence scope and record Google/GitHub OAuth plus production-readiness as deferred ideas. | |
| Promote OAuth and production-readiness into Phase 5 | Update roadmap and requirements so this is the final coding phase with Google/GitHub OAuth and 100 users/month production-readiness in scope. | yes |

**User's choice:** Promote OAuth and production-readiness into Phase 5.
**Notes:** User explicitly said this should be the final coding phase and requested no deferral. Roadmap, requirements, state continuity, and UI spec were updated accordingly.

---

## Gateway Evidence Source

| Option | Description | Selected |
|--------|-------------|----------|
| Kong enforces, FastAPI stores evidence | Kong handles CORS/rate-limit/request-size/correlation controls; FastAPI stores redacted evidence for requests that reach it. Kong-only 429 evidence comes from config/tests. | yes |
| Kong log plugin feeds evidence | Use Kong logging plugin and ingest gateway logs into backend evidence. | |
| Minimal demonstrable evidence only | Keep gateway evidence mostly config and test-script based. | |

**User's choice:** Kong enforces, FastAPI stores evidence.
**Notes:** This avoids fake admin rows for gateway-only denials while still making the gateway behavior demonstrable.

---

## OAuth Account Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-link only verified matching email | Link provider identity to an existing account only when provider email is verified and matches normalized local email. | yes |
| Always create separate OAuth account | Avoid takeover by never linking, but creates duplicate identities. | |
| Require logged-in user to link provider first | Safest linking UX, but first-time OAuth login is not smooth. | |

**User's choice:** Auto-link only verified matching email.
**Notes:** User first chose separate OAuth accounts, then changed the decision to auto-link verified matching email. Final locked decision is auto-link only on verified matching email.

---

## OAuth First-Time User

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-provision standard user | Create a standard `user` with standard scopes when verified OAuth email is new. | yes |
| Deny until admin invites/creates user | Stronger internal control but less useful social login. | |
| Allow only configured email domain | Auto-provision only for configured domains. | |

**User's choice:** Auto-provision standard user.
**Notes:** Provider identity must still be persisted by `(provider, provider_subject)` for repeat logins.

---

## Admin Evidence Depth

| Option | Description | Selected |
|--------|-------------|----------|
| All six admin surfaces | Wire metrics, users, security events, tool executions, gateway evidence, and orchestration. | yes |
| Security-critical only | Wire users, security events, tool executions, and orchestration only. | |
| Read-only evidence first | Wire metrics, security events, tool executions, and gateway evidence, deferring writes. | |

**User's choice:** All six admin surfaces.
**Notes:** Existing backend already covers many of these surfaces; frontend currently has placeholders for most of them.

---

## Redaction Detail Policy

| Option | Description | Selected |
|--------|-------------|----------|
| Summaries only | Tables and drawers show only safe summaries and metadata. | |
| Summaries plus expandable sanitized snippets | Tables show summaries; drawers can show short redacted snippets. | yes |
| Role-tiered detail | Different admin scopes get different detail levels. | |

**User's choice:** Summaries plus expandable sanitized snippets.
**Notes:** Snippets require recursive redaction and canary-secret tests. Raw prompts, request bodies, provider payloads, tokens, cookies, secrets, raw Google HTML/JSON, full sandbox output, container IDs, and host paths remain forbidden.

---

## Cloudflare and Trusted Proxy Story

| Option | Description | Selected |
|--------|-------------|----------|
| Documented optional edge, local app remains primary | Implement trusted proxy/origin hooks and document Cloudflare Tunnel/WAF/Turnstile/Bot Fight/TLS/source-IP assumptions and Free-plan limits. | yes |
| Cloudflare profile runnable when env is set | Add optional runnable tunnel-style setup. | |
| No implementation, docs only | Write assumptions only. | |

**User's choice:** Documented optional edge, local app remains primary.
**Notes:** Cloudflare must not be required for the local demo.

---

## the agent's Discretion

- Exact OAuth route names, module structure, model names, and provider adapter boundaries.
- Exact snippet length limits, metadata allowlists, and admin drawer layout.
- Exact test packaging for production-readiness smoke checks.
- Exact gateway evidence copy for Kong-only denials, as long as it is truthful.

## Deferred Ideas

None. The user explicitly promoted OAuth and small production-readiness into Phase 5 scope.
