# Phase 1: Secure Platform and Account Access - Context

**Gathered:** 2026-06-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver the runnable local platform and secure account foundation: Compose topology, database migrations, environment configuration, health/readiness behavior, local registration and login, strict access JWTs, rotating refresh sessions, logout, current-user identity, and fail-closed handling of inactive or unknown principals. Chat, Google Search, Python execution, gateway hardening, and administrative evidence surfaces remain in later phases.

</domain>

<decisions>
## Implementation Decisions

### Account Defaults
- **D-01:** Every newly registered `User` receives the complete standard user scope bundle: `chat:read`, `chat:write`, `tool:websearch`, and `tool:python`.
- **D-02:** Normal registration always creates an active `User` with the fixed standard scope bundle. Clients cannot request, select, or modify roles or scopes during registration.
- **D-03:** The first production Admin is created or promoted only through an explicit one-time bootstrap command. Production must not ship or automatically create default administrator credentials.
- **D-04:** Development mode automatically provisions demo User and Admin accounts when the Compose environment starts.
- **D-05:** Automatic demo provisioning must be gated by an explicit development-mode setting and must not run in production mode.

### the agent's Discretion
- Choose access-token and refresh-session lifetimes, multi-device session behavior, logout scope, and the exact replay-response UX while preserving strict rotation, revocation, and replay detection.
- Choose password policy details, validation error structure, and duplicate-account messaging while preventing account enumeration and following the locked Argon2id requirement.
- Choose demo-account credential values, idempotent reseeding behavior, and how credentials are surfaced in development documentation. Do not commit real secrets, reuse demo credentials outside development, or allow the seed path in production.
- Choose whether absent LLM credentials produce startup failure or a documented degraded provider state. Authentication and database readiness must remain diagnosable, and secret-bearing errors are forbidden.
- Choose module layout, schema details, migration structure, configuration library, test fixtures, and bootstrap command syntax using the project stack and security requirements.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and Decisions
- `.planning/ROADMAP.md` - Defines the Phase 1 boundary, dependencies, requirements, and observable success criteria.
- `.planning/REQUIREMENTS.md` - Defines the Phase 1 `PLAT-*`, `AUTH-*`, `AUTHZ-01`, and `AUTHZ-08` requirements and project-wide acceptance criteria.
- `.planning/PROJECT.md` - Defines the core value, fixed technology constraints, local-auth/OIDC boundary, and security decisions.
- `.planning/STATE.md` - Records current project position and decisions carried into Phase 1.

### Original Brief and Local Guidance
- `prompt.md` - Original project brief, API shape, data model, security controls, Compose expectations, and development strategy.
- `AGENTS.md` - Generated project stack and workflow guidance that applies to implementation agents.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- No application code exists yet. Phase 1 creates the initial backend, data, Compose, migration, and test foundations.

### Established Patterns
- Planning uses six dependency-ordered vertical MVP phases.
- FastAPI is the authoritative security boundary even when later gateway checks are added.
- Security-sensitive behavior must fail closed, avoid secret logging, and have negative tests.
- Local credentials must sit behind an identity-provider boundary suitable for later external OIDC integration.

### Integration Points
- Phase 1 establishes the backend application factory, configuration model, database session and migrations, authentication routes, authorization dependencies, Compose services, and health/readiness contracts used by every later phase.
- The user and refresh-token models must support later conversations, tool scopes, audit records, security events, and administrative access without implementing those later capabilities now.

</code_context>

<specifics>
## Specific Ideas

- Development Compose should be immediately demonstrable with automatically provisioned demo User and Admin accounts.
- Production administration should remain deliberate: an operator invokes a one-time command rather than relying on startup environment credentials or a permanent seeded account.
- Tool access is part of the normal User entitlement for this prototype, even though later phases must still recheck the relevant scope immediately before each tool execution.

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope.

</deferred>

---

*Phase: 1-secure-platform-and-account-access*
*Context gathered: 2026-06-08*
