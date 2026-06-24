# Phase 7: Sender-Constrained Sessions and Cryptographic Hardening - Context

**Gathered:** 2026-06-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Harden SimpAgent against `web2api`-style abuse by turning the browser session, OAuth callback artifacts, and internal tool capability boundaries into replay-resistant cryptographic trust paths instead of reusable bearer-style credentials. This phase delivers the MVP hardening slice only: PKCE and sealed OAuth transactions, asymmetric one-time internal capabilities, and DPoP-style sender-constrained sessions.

</domain>

<decisions>
## Implementation Decisions

### Scope and sequencing
- **D-01:** Phase 07 is an MVP hardening slice, not a full identity/security redesign. It must stop at PKCE + sealed OAuth transactions, asymmetric one-time capability tokens, and DPoP-style sender-constrained sessions.
- **D-02:** WebAuthn/passkey step-up for admin or sensitive actions is explicitly deferred beyond Phase 07.
- **D-03:** Rollout must be feature-flag friendly and migration-safe so the codebase can introduce new trust artifacts without pretending legacy sessions were already sender-constrained.

### OAuth and browser session hardening
- **D-04:** Google and GitHub OAuth authorization-code flows must add PKCE S256 and a sealed one-time transaction record instead of relying on signed `state` alone.
- **D-05:** The browser session hardening model must use a browser-held client key and DPoP-style request proofs so copied access tokens or refresh cookies are insufficient by themselves.
- **D-06:** Sender-constrained auth must cover the core protected auth and conversation surfaces first; phase work should not claim every future endpoint is already hardened until it really is.

### Internal capability hardening
- **D-07:** Search and Python capability credentials must move from reusable short-lived bearer semantics to asymmetric, audience-bound, one-time consumable artifacts.
- **D-08:** Replay tracking should use a shared journal or equivalent reviewed persistence so DPoP proofs, OAuth transactions, and internal capabilities can all fail closed on reuse with correlated evidence.

### Evidence and documentation
- **D-09:** This phase must extend operational guidance and security evidence truthfully: key-loss re-auth behavior, rollout constraints, and residual prototype limitations must be documented, not implied.

### the agent's Discretion
- Choose the exact signing primitive for asymmetric internal capabilities (for example Ed25519 or ES256) based on the existing Python/JS libraries and interoperability constraints.
- Choose whether replay-journal storage is split by token type or normalized into one table, as long as it stays auditable and bounded.
- Choose the exact DPoP proof helper/module split between backend and frontend, as long as browser-held key material remains non-exportable in normal operation.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project scope and active roadmap
- `.planning/ROADMAP.md` - Defines Phase 07 goal, requirements, success criteria, and dependency on Phase 06.
- `.planning/REQUIREMENTS.md` - Defines `AUTH-11`, `AUTH-12`, `IDEN-09`, `AGNT-08`, `AGNT-09`, `OBS-08`, and `PRODREADY-06`.
- `.planning/STATE.md` - Records that Phase 07 is the next hardening slice while Phase 03 historical debt remains visible.
- `.planning/PROJECT.md` - Defines the project core value, constraints, and post-v1 cryptographic hardening direction.

### Existing auth/session and OAuth implementation
- `backend/app/api/routes/auth.py` - Current login, refresh, logout, cookie, and CSRF entrypoints.
- `backend/app/services/authentication.py` - Current local login/session issuance flow.
- `backend/app/services/sessions.py` - Current refresh rotation, replay handling, and logout behavior.
- `backend/app/security/access_tokens.py` - Current RS256 access-token issuance/validation profile.
- `backend/app/security/refresh_tokens.py` - Current refresh-token generation and hashing.
- `backend/app/security/csrf.py` - Existing Origin/CSRF enforcement that must coexist with DPoP.
- `backend/app/api/routes/auth_oauth.py` - Current OAuth start/callback flow and signed state cookies.
- `backend/app/identity/oauth_service.py` - Current OAuth account-linking and session issuance behavior.
- `backend/tests/integration/auth/test_session_flow.py` - Existing refresh rotation and logout verification.
- `backend/tests/integration/auth/test_oauth_flows.py` - Existing OAuth security tests.
- `backend/tests/unit/test_oauth_state_cookie.py` - Existing state-cookie invariants.
- `backend/tests/security/test_jwt_profile.py` - Current JWT profile and gateway/backend authority expectations.

### Existing internal capability boundaries
- `backend/app/security/search_capability.py` - Current search capability JWT shape and validation.
- `backend/app/security/tool_capabilities.py` - Current Python capability token issuance.
- `backend/app/ai/search_worker/service.py` - Current capability validation at the search worker boundary.
- `backend/app/tools/python_client.py` - Current typed Python supervisor invocation contract.
- `sandbox/server.py` - Current Python supervisor trust boundary and capability verification.

### Frontend/browser session behavior
- `frontend/lib/auth-session.ts` - Current browser memory-only access token logic and refresh behavior.
- `frontend/components/account-access/AccountAccessShell.tsx` - Current auth-shell bootstrap and logout/session UX.
- `frontend/tests/auth-session.test.ts` - Existing frontend auth-session regression coverage.

### Security and architecture truthfulness
- `docs/security.vi.md` - Current truthful statement of session, OAuth, RBAC, search, and sandbox boundaries.
- `docs/architecture.vi.md` - Current trust-boundary and topology documentation.
- `.claude/plan.md` - The hardening strategy analysis that this phase is translating into GSD artifacts.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/security/access_tokens.py` already enforces strict JWT issuer, audience, type, `kid`, and temporal validation, so Phase 07 can extend claims rather than invent a new token stack.
- `backend/app/services/sessions.py` and `backend/app/models/session.py` already implement refresh-family rotation, replay revocation, and security-event recording, which makes them the natural place to extend sender-constrained bindings and replay journals.
- `backend/app/api/routes/auth_oauth.py` already owns backend-started OAuth flows and signed state cookies, so PKCE and sealed transactions should layer onto that route surface instead of introducing a client-owned OAuth start path.
- `backend/app/security/search_capability.py` already uses asymmetric JWT signing for search capabilities, which can act as the pattern source for the broader asymmetric anti-replay boundary.
- `frontend/lib/auth-session.ts` already keeps access tokens in memory only and centralizes refresh retries, making it the correct integration point for DPoP-style proof headers.

### Established Patterns
- SimpAgent prefers fail-closed auth and truthful degraded states; missing or invalid security artifacts should deny access rather than silently falling back.
- Security evidence is first-class: replay or policy violations should create correlated security events, not just HTTP errors.
- The project separates browser session logic, backend authorization, and worker boundaries cleanly; new cryptographic bindings should reinforce those boundaries rather than blur them.
- The repo documents prototype limits honestly. Phase 07 must not overclaim that every endpoint, device migration case, or future admin flow is magically solved.

### Integration Points
- DPoP/session hardening connects backend auth routes, principal resolution, refresh-family persistence, and frontend request helpers.
- PKCE and sealed transactions connect OAuth route handlers, provider exchange flows, and replay-journal persistence.
- Asymmetric one-time capabilities connect search worker validation, Python supervisor validation, and any shared replay-journal persistence added in backend models/repositories.
- Documentation and evidence updates connect `docs/security.vi.md`, runbook/limitations guidance, and security-event logging paths.

</code_context>

<specifics>
## Specific Ideas

- Use a browser-held key pair to bind DPoP-style proofs to core protected requests so copied cookies/tokens alone do not authenticate.
- Add PKCE S256 to both Google and GitHub OAuth flows and seal the backend transaction state so callback artifacts become one-time and provider-bound.
- Convert Python capability verification away from shared-secret issuance toward an asymmetric trust model where the sandbox verifies with a public key only.
- Reuse a single replay-journal concept across OAuth transaction use, DPoP proof replay, and internal capability replay whenever that keeps the codebase simpler and more auditable.

</specifics>

<deferred>
## Deferred Ideas

- WebAuthn/passkey step-up for admin and highly sensitive actions belongs to a later phase, not Phase 07.
- Broader admin-surface cryptographic step-up, device/session self-management UX, and other identity v2 enhancements remain future work.
- Historical Phase 03 planning/verification debt remains visible and should not be “fixed” as part of this hardening phase.

</deferred>

---

*Phase: 7-Sender-Constrained Sessions and Cryptographic Hardening*
*Context gathered: 2026-06-23*
