# Requirements: Design a Secure Chatbot Application with Lightweight Agent Capabilities

**Defined:** 2026-06-08
**Core Value:** Users can safely authenticate and use an AI chatbot with controlled agent tools without crossing tenant, role, scope, network, or host-execution boundaries.

## v1 Requirements

### Platform Foundation

- [ ] **PLAT-01**: Developer can start the required local system with `docker compose up --build`.
- [ ] **PLAT-02**: The Compose topology starts frontend, backend, PostgreSQL, Kong, and the Python sandbox foundation with health checks.
- [ ] **PLAT-03**: Backend applies reviewed Alembic migrations for users, refresh tokens, conversations, messages, tool executions, audit logs, and security events.
- [ ] **PLAT-04**: Operator can configure all secrets, provider endpoints, model IDs, allowed origins, and security settings through environment variables documented in `.env.example`.
- [ ] **PLAT-05**: Services expose liveness and readiness endpoints that distinguish process health from dependency readiness without exposing secrets.
- [ ] **PLAT-06**: Missing required LLM credentials or an unavailable configured search model produces a documented fail-closed or degraded state without a secret-bearing stack trace.

### Authentication and Sessions

- [ ] **AUTH-01**: User can register with a normalized unique email and password without account-enumerating responses.
- [ ] **AUTH-02**: User can log in with valid local credentials and receives a short-lived access token plus a protected refresh session.
- [ ] **AUTH-03**: Passwords are hashed with Argon2id and are never stored, returned, or logged in plaintext.
- [ ] **AUTH-04**: Access JWTs include `sub`, `role`, `scopes`, `exp`, `iat`, and `jti` and are validated against an explicit algorithm, issuer, audience, type, and time policy.
- [ ] **AUTH-05**: User can refresh a session through an opaque, server-side-hashed refresh-token family with atomic rotation.
- [ ] **AUTH-06**: Reuse of a rotated or revoked refresh token revokes its active family, denies the request, and records a security event.
- [ ] **AUTH-07**: User can log out and invalidate the active refresh session.
- [ ] **AUTH-08**: Authenticated user can retrieve their current identity, role, scopes, and active status without credential material.
- [ ] **AUTH-09**: Browser session handling keeps refresh tokens unavailable to JavaScript and applies CSRF and Origin protections appropriate to the deployment topology.
- [ ] **AUTH-10**: Identity code exposes an OIDC-ready provider boundary without claiming that local password authentication is itself an OpenID Provider.

### Authorization

- [ ] **AUTHZ-01**: Every protected endpoint rejects inactive users and tokens missing the required authenticated principal.
- [ ] **AUTHZ-02**: Admin APIs require the Admin role and the corresponding `admin:read` or `admin:write` scope.
- [x] **AUTHZ-03**: Chat read operations require `chat:read`, and chat mutation operations require `chat:write`.
- [ ] **AUTHZ-04**: Web Search execution requires `tool:websearch`, and Python execution requires `tool:python`.
- [x] **AUTHZ-05**: Conversation and message queries constrain resource ID and authenticated owner in the same data-access operation.
- [x] **AUTHZ-06**: User cannot infer, read, modify, append to, or delete another user's conversations or messages.
- [ ] **AUTHZ-07**: Tool authorization is checked immediately before execution and cannot be granted or overridden by model output.
- [ ] **AUTHZ-08**: Unknown roles, scopes, tools, and policy states fail closed and produce a redacted authorization or security event.

### Conversations and Chat

- [x] **CHAT-01**: User can create a conversation they own.
- [x] **CHAT-02**: User can list their own conversations in stable, paginated order.
- [x] **CHAT-03**: User can retrieve one owned conversation and its ordered message history.
- [x] **CHAT-04**: User can delete an owned conversation according to a documented data and audit-retention policy.
- [x] **CHAT-05**: User can send a message to an owned conversation without duplicate submission creating duplicate provider work.
- [x] **CHAT-06**: Backend persists accepted user messages and successful assistant responses with immutable roles, timestamps, ordering, and safe metadata.
- [x] **CHAT-07**: A provider failure never creates a fabricated successful assistant message and returns a stable error containing a support correlation ID.
- [x] **CHAT-08**: A configurable OpenAI-compatible adapter handles normal chat through `LLM_API_BASE`, `LLM_API_KEY`, `LLM_MODEL`, and bounded timeout/retry settings.
- [ ] **CHAT-09**: Frontend supports registration, login, logout, conversation navigation, message composition, pending states, retryable errors, and history reload.
- [ ] **CHAT-10**: Frontend renders Markdown and code blocks while sanitizing raw HTML, scripts, event handlers, and dangerous URL schemes.
- [x] **CHAT-11**: Chat supports a correct non-streaming JSON response path; streaming is enabled only if disconnect, persistence, and proxy behavior remain correct.
- [ ] **CHAT-12**: User can distinguish direct LLM, Google-grounded Search, and Python-tool responses in the chat interface.

### Agent Coordination

- [ ] **AGNT-01**: A deterministic coordinator can select only direct chat, Google Search, or Python from an explicit allowlist.
- [ ] **AGNT-02**: The model may propose a tool action but cannot authorize it, alter its execution policy, or select arbitrary commands, images, networks, mounts, or external APIs.
- [ ] **AGNT-03**: v1 permits at most one bounded tool invocation per user turn and enforces request, output, retry, wall-time, concurrency, and cost budgets.
- [ ] **AGNT-04**: Search and Python use separate workers and credential boundaries behind typed internal contracts.
- [ ] **AGNT-05**: Internal tool requests use short-lived audience-bound capability credentials rather than forwarding the user's bearer token.
- [ ] **AGNT-06**: Every requested, denied, started, succeeded, failed, or timed-out tool action has a persisted state and correlation ID.
- [ ] **AGNT-07**: System prompts and coordinator policy explicitly treat user input, model output, and tool content as untrusted and never expose secrets to model context.

### Google Search

- [ ] **SRCH-01**: A dedicated Google ADK worker invokes built-in Google Search using a deployment-configured, currently available compatible Gemini 2 model.
- [ ] **SRCH-02**: Search startup or deployment performs a capability check for model availability, Google Search support, and expected grounding metadata.
- [ ] **SRCH-03**: A live grounded response transports answer text and required grounding fields without falsely labeling an ungrounded response as grounded.
- [ ] **SRCH-04**: Frontend renders claim-to-source citations and required Google Search Suggestions safely for the same end user.
- [ ] **SRCH-05**: Grounding persistence and telemetry retain only fields allowed by Google terms effective at implementation time and do not perform source-link click tracking.
- [ ] **SRCH-06**: Search requests apply input limits, timeout, result/output limits, user budgets, and safe failure behavior.
- [ ] **SRCH-07**: Search failures, missing grounding, and model unavailability are visibly distinguished from successful grounded answers.
- [ ] **SRCH-08**: Search content cannot cause internal URL fetching, scope escalation, arbitrary tool execution, or policy changes.

### Python Sandbox

- [ ] **SBOX-01**: Backend never executes user Python with host-process `exec`, `eval`, shell execution, or the backend interpreter.
- [ ] **SBOX-02**: Authorized code runs only through a dedicated fixed-policy sandbox boundary that accepts code and bounded execution parameters.
- [ ] **SBOX-03**: Sandbox execution has no network access by default and cannot reach localhost, private networks, link-local addresses, cloud metadata, or Docker internal services.
- [ ] **SBOX-04**: Sandbox runs non-root with a read-only root filesystem, temporary writable workspace, dropped capabilities, `no-new-privileges`, and an enforced seccomp profile.
- [ ] **SBOX-05**: Sandbox enforces wall-time, CPU, memory, PID, file-size, process, and output limits and reports the limit that ended execution.
- [ ] **SBOX-06**: Sandbox receives no application secrets, host paths, Docker socket, privileged mode, host namespaces, devices, or user-controlled runtime configuration.
- [ ] **SBOX-07**: Sandbox captures bounded stdout, stderr, exit status, duration, and safe error details, then removes temporary execution data.
- [ ] **SBOX-08**: Package installation and arbitrary external commands are denied unless a future reviewed allowlist explicitly permits them.

### Gateway and Edge Security

- [ ] **GATE-01**: Kong OSS runs in DB-less mode with declarative services and routes for approved `/api/*`, `/health`, and readiness traffic.
- [ ] **GATE-02**: Kong applies strict configured CORS origins, methods, and headers without using a wildcard credentialed origin.
- [ ] **GATE-03**: Kong applies stricter limits to login, registration, and tool routes than to ordinary chat routes and returns useful `429` metadata.
- [ ] **GATE-04**: Kong applies request-size limits and propagates or creates a validated correlation ID.
- [ ] **GATE-05**: Kong may reject coarse invalid JWT traffic early, but FastAPI independently remains authoritative for complete token, account, role, scope, ownership, and tool-policy validation.
- [ ] **GATE-06**: Kong Admin API, PostgreSQL, search worker, and sandbox control plane are not exposed as public application ports.
- [ ] **GATE-07**: Documentation defines the optional request path `Client -> Cloudflare -> Kong -> FastAPI -> PostgreSQL/LLM/Tools` and trusted proxy assumptions.
- [ ] **GATE-08**: Cloudflare documentation covers Tunnel, DNS, TLS, Free-plan WAF guidance, Turnstile integration points, Bot Fight Mode, limitations, and source-IP trust.

### Logging and Administration

- [ ] **OBS-01**: Every request receives a validated correlation ID propagated through Kong, FastAPI, provider calls, tool calls, audit records, and the response.
- [ ] **OBS-02**: Application logs are structured JSON with allowlisted fields and recursive redaction of credentials, tokens, cookies, API keys, secrets, and sensitive raw content.
- [ ] **OBS-03**: Auth failures, forbidden access, refresh replay, rate-limit events, tool decisions, sandbox violations, and admin actions create typed redacted evidence.
- [ ] **OBS-04**: Tool execution records contain actor, conversation, tool, safe input/output summaries, status, duration, and correlation ID.
- [ ] **OBS-05**: Properly authorized admin can list users and paginated recent audit logs, security events, tool executions, failed logins, and available rate-limit evidence.
- [ ] **OBS-06**: Ordinary users and under-scoped admins cannot access administrative evidence endpoints.
- [ ] **OBS-07**: Admin metrics expose bounded aggregate operational/security counts without leaking user content or credentials.

### Verification and Documentation

- [ ] **TEST-01**: Automated tests cover registration, login, refresh rotation, invalid and expired tokens, logout, and refresh-token replay.
- [ ] **TEST-02**: Automated two-user tests prove BOLA protection for every conversation and message read/write/delete route.
- [ ] **TEST-03**: Automated tests prove users cannot call admin APIs or tools without the required role and scopes.
- [ ] **TEST-04**: Automated chat tests cover conversation creation, message sending, history ordering, idempotency, and provider failure behavior.
- [ ] **TEST-05**: Automated search tests cover scope enforcement, grounding contract handling, timeout, missing grounding, and prompt-injection attempts.
- [ ] **TEST-06**: Automated sandbox tests cover timeout, network denial, memory/CPU/PID limits, host-file denial, output limits, cleanup, and escape attempts.
- [ ] **TEST-07**: Attack scripts under `security-tests/` demonstrate BOLA denial, brute-force limiting, token replay response, SSRF denial, prompt/tool abuse control, and sandbox escape denial against the Compose topology.
- [ ] **TEST-08**: Repository includes practical Semgrep, Snyk-compatible dependency, Burp Suite, AWVS, and DAST guidance plus a security finding report template.
- [ ] **TEST-09**: Security tests assert database, network, process, and provider side effects rather than relying only on response wording or model refusals.
- [ ] **TEST-10**: Canary-secret tests verify that success and failure logs, audit records, and API responses do not leak protected values.
- [ ] **DOCS-01**: Vietnamese `README.md` explains project purpose, prerequisites, environment, startup, testing, demo setup, API docs, security features, and known limitations.
- [ ] **DOCS-02**: Vietnamese architecture documentation includes Mermaid component, trust-boundary, request-flow, and network-flow diagrams.
- [ ] **DOCS-03**: Vietnamese security documentation explains local auth versus OIDC readiness, JWT lifecycle, refresh replay, RBAC/scopes, BOLA controls, tool policy, grounding, sandbox isolation, logging, and audit.
- [ ] **DOCS-04**: Vietnamese testing documentation explains unit/integration tests, attack simulations, SAST, dependency scanning, container scanning, Burp, AWVS, and DAST.
- [ ] **DOCS-05**: Vietnamese runbook covers brute force, token replay, BOLA, prompt injection, sandbox abuse, SSRF, provider outages, and secret exposure response.
- [ ] **DOCS-06**: Documentation states prototype limitations, external provider data flows, Google grounding retention constraints, Windows/Docker sandbox limitations, and features not implemented.

## User Stories

- As a user, I can authenticate and continue a protected session without exposing a long-lived token to browser JavaScript.
- As a user, I can create and revisit private conversations that no other user can access.
- As an authorized user, I can ask for current web information and see verifiable Google-grounded citations.
- As an authorized user, I can run bounded Python code without granting it access to the host, application network, or secrets.
- As an administrator, I can inspect redacted security and tool evidence without reading credentials or unrestricted private content.
- As an evaluator, I can start the system, run adversarial tests, and trace each claimed control to implementation evidence and Vietnamese documentation.

## Acceptance Criteria

- All v1 requirements map to exactly one roadmap phase and have executable or inspectable verification.
- `docker compose up --build` starts the documented local topology.
- Real OpenAI-compatible chat and Google ADK Search work when valid external credentials and a compatible Gemini 2 model are configured.
- Negative authorization and sandbox tests prove denied actions create no forbidden data disclosure, provider call, network access, host access, or privileged side effect.
- Logs and evidence correlate sensitive operations without retaining secrets.
- Documentation describes actual implemented behavior and does not overclaim OIDC, distributed rate limiting, Cloudflare protection, or production-grade sandbox isolation.

## Definition of Done

- Required services build and reach their documented healthy or intentionally degraded states.
- Automated functional, authorization, tool, sandbox, and attack tests pass against the assembled topology.
- Security-sensitive behavior has both allow-path and deny-path evidence.
- Database migrations, environment template, Kong configuration, security scripts, and Vietnamese documentation are present and consistent.
- No unresolved critical or high-severity finding remains without an explicit accepted-risk note.

## v2 Requirements

### Identity Enhancements

- **IDEN-01**: User can verify an email address through a bounded single-use token.
- **IDEN-02**: User can reset a forgotten password through a bounded single-use token without account enumeration.
- **IDEN-03**: User can authenticate through a real external OAuth2/OIDC provider using Authorization Code with PKCE.
- **IDEN-04**: User can view and revoke individual device/session families.
- **IDEN-05**: Admin can use MFA or WebAuthn step-up authentication for sensitive actions.

### Product Enhancements

- **PROD-01**: User can rename, archive, search, and explicitly manage retention for conversations.
- **PROD-02**: User can cancel and resume streaming responses with correct persistence semantics.
- **PROD-03**: User can view personal message, search, and sandbox usage budgets.
- **PROD-04**: Evaluator can export a machine-generated Vietnamese security evidence report.

### Operations

- **OPER-01**: Operator can enable an optional Loki, Grafana, and OpenTelemetry observability profile.
- **OPER-02**: Operator can rotate JWT signing keys with overlapping verification windows.
- **OPER-03**: Operator can deploy shared/distributed rate limiting for a multi-instance topology.
- **OPER-04**: Operator can replace the Docker sandbox with gVisor, Kata Containers, or microVM isolation after a separate threat review.

## Out of Scope

| Feature | Reason |
|---------|--------|
| LLM training or fine-tuning | External APIs provide model capability; training is unrelated to the security prototype |
| RAG, knowledge base, file ingestion, or long-term memory | Introduces separate data-ingestion, privacy, malware, and indirect-injection scope |
| Kubernetes or production multi-cloud deployment | Docker Compose is the required local delivery target |
| Organizations and shared multi-tenant workspaces | Requires a separate relationship-authorization and cross-tenant model |
| Billing and subscriptions | Not needed to demonstrate secure chatbot and tool boundaries |
| Email, payments, external deletion, arbitrary HTTP, or other write-capable tools | Violates the deliberately low-impact allowlisted agent scope |
| SearXNG or another search provider | Google ADK built-in Google Search is the selected search path |
| Gateway-only authorization | Kong cannot replace backend token, account, scope, ownership, and tool-policy checks |
| Browser `localStorage` refresh tokens | Persistent JavaScript-readable bearer tokens expand XSS impact |
| Host-process Python execution | User code must execute only behind the isolated sandbox boundary |
| Docker socket in FastAPI or the untrusted runtime | Docker daemon control is effectively host authority |
| Advanced ML anomaly detection | Deterministic controls and typed security events are sufficient for v1 |
| Real penetration testing of third-party systems | Testing is restricted to the owned local application |

## Traceability

Roadmap generation maps every v1 requirement to exactly one phase.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PLAT-01 | Phase 1 | Pending |
| PLAT-02 | Phase 1 | Pending |
| PLAT-03 | Phase 1 | Pending |
| PLAT-04 | Phase 1 | Pending |
| PLAT-05 | Phase 1 | Pending |
| PLAT-06 | Phase 1 | Pending |
| AUTH-01 | Phase 1 | Pending |
| AUTH-02 | Phase 1 | Pending |
| AUTH-03 | Phase 1 | Pending |
| AUTH-04 | Phase 1 | Pending |
| AUTH-05 | Phase 1 | Pending |
| AUTH-06 | Phase 1 | Pending |
| AUTH-07 | Phase 1 | Pending |
| AUTH-08 | Phase 1 | Pending |
| AUTH-09 | Phase 1 | Pending |
| AUTH-10 | Phase 1 | Pending |
| AUTHZ-01 | Phase 1 | Pending |
| AUTHZ-08 | Phase 1 | Pending |
| AUTHZ-03 | Phase 2 | Complete |
| AUTHZ-05 | Phase 2 | Complete |
| AUTHZ-06 | Phase 2 | Complete |
| CHAT-01 | Phase 2 | Complete |
| CHAT-02 | Phase 2 | Complete |
| CHAT-03 | Phase 2 | Complete |
| CHAT-04 | Phase 2 | Complete |
| CHAT-05 | Phase 2 | Complete |
| CHAT-06 | Phase 2 | Complete |
| CHAT-07 | Phase 2 | Complete |
| CHAT-08 | Phase 2 | Complete |
| CHAT-09 | Phase 2 | Pending |
| CHAT-10 | Phase 2 | Pending |
| CHAT-11 | Phase 2 | Complete |
| AUTHZ-04 | Phase 3 | Pending |
| AUTHZ-07 | Phase 3 | Pending |
| AGNT-01 | Phase 3 | Pending |
| AGNT-02 | Phase 3 | Pending |
| AGNT-03 | Phase 3 | Pending |
| AGNT-04 | Phase 3 | Pending |
| AGNT-05 | Phase 3 | Pending |
| AGNT-06 | Phase 3 | Pending |
| AGNT-07 | Phase 3 | Pending |
| SRCH-01 | Phase 3 | Pending |
| SRCH-02 | Phase 3 | Pending |
| SRCH-03 | Phase 3 | Pending |
| SRCH-04 | Phase 3 | Pending |
| SRCH-05 | Phase 3 | Pending |
| SRCH-06 | Phase 3 | Pending |
| SRCH-07 | Phase 3 | Pending |
| SRCH-08 | Phase 3 | Pending |
| CHAT-12 | Phase 4 | Pending |
| SBOX-01 | Phase 4 | Pending |
| SBOX-02 | Phase 4 | Pending |
| SBOX-03 | Phase 4 | Pending |
| SBOX-04 | Phase 4 | Pending |
| SBOX-05 | Phase 4 | Pending |
| SBOX-06 | Phase 4 | Pending |
| SBOX-07 | Phase 4 | Pending |
| SBOX-08 | Phase 4 | Pending |
| AUTHZ-02 | Phase 5 | Pending |
| GATE-01 | Phase 5 | Pending |
| GATE-02 | Phase 5 | Pending |
| GATE-03 | Phase 5 | Pending |
| GATE-04 | Phase 5 | Pending |
| GATE-05 | Phase 5 | Pending |
| GATE-06 | Phase 5 | Pending |
| GATE-07 | Phase 5 | Pending |
| GATE-08 | Phase 5 | Pending |
| OBS-01 | Phase 5 | Pending |
| OBS-02 | Phase 5 | Pending |
| OBS-03 | Phase 5 | Pending |
| OBS-04 | Phase 5 | Pending |
| OBS-05 | Phase 5 | Pending |
| OBS-06 | Phase 5 | Pending |
| OBS-07 | Phase 5 | Pending |
| TEST-01 | Phase 6 | Pending |
| TEST-02 | Phase 6 | Pending |
| TEST-03 | Phase 6 | Pending |
| TEST-04 | Phase 6 | Pending |
| TEST-05 | Phase 6 | Pending |
| TEST-06 | Phase 6 | Pending |
| TEST-07 | Phase 6 | Pending |
| TEST-08 | Phase 6 | Pending |
| TEST-09 | Phase 6 | Pending |
| TEST-10 | Phase 6 | Pending |
| DOCS-01 | Phase 6 | Pending |
| DOCS-02 | Phase 6 | Pending |
| DOCS-03 | Phase 6 | Pending |
| DOCS-04 | Phase 6 | Pending |
| DOCS-05 | Phase 6 | Pending |
| DOCS-06 | Phase 6 | Pending |

**Coverage:**

- v1 requirements: 90 total
- Mapped to phases: 90
- Unmapped: 0

**Phase allocation:**

- Phase 1: 18 requirements
- Phase 2: 14 requirements
- Phase 3: 17 requirements
- Phase 4: 9 requirements
- Phase 5: 16 requirements
- Phase 6: 16 requirements

---
*Requirements defined: 2026-06-08*
*Last updated: 2026-06-08 after roadmap generation*
