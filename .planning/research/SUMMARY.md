# Project Research Summary

**Project:** Design a Secure Chatbot Application with Lightweight Agent Capabilities
**Domain:** Secure multi-user chatbot SaaS prototype with bounded agent tools
**Researched:** 2026-06-08
**Confidence:** HIGH overall; MEDIUM for time-sensitive Gemini/ADK behavior and Docker sandbox assurance on Windows hosts

## Executive Summary

This project is a security-focused ChatGPT-like university prototype, not a general autonomous agent. Experts would build it as a modular FastAPI policy and persistence authority, a Next.js browser client, PostgreSQL, and two narrow tool boundaries: a Google ADK search-only service and a separately controlled Python execution service. Kong supplies coarse ingress controls, but FastAPI remains authoritative for identity, token semantics, roles, scopes, object ownership, tool permission, account state, budgets, and audit outcomes. Models and tool outputs are untrusted proposals or data, never authorization authorities.

The recommended v1 proves a narrow set of complete workflows: secure local authentication with rotating refresh-token families, owner-only conversation history, normal OpenAI-compatible chat, policy-gated Google Search grounding, and scope-gated no-network Python execution. Every sensitive control must have a visible result, a negative test, and correlated redacted evidence. Build security contracts, persistence, observability, identity, and ownership before connecting real providers or executing code.

The highest risks are semantically incomplete JWT validation, refresh-token races, BOLA, model-driven tool bypass, Google grounding/retention mistakes, and a sandbox control plane that accidentally has host-level power. Mitigate them with explicit token profiles, transactional rotation, owner-scoped repositories, a deterministic coordinator, a version-pinned grounding contract test, and a sandbox design that never gives user code or the application backend Docker control. Gemini model availability is time-sensitive: configure a Gemini 2 model externally and prove at startup or deployment that it is still available and returns Google Search grounding metadata; do not hardcode a model identifier that may be retired.

## Key Findings

Detailed research: [STACK.md](./STACK.md), [FEATURES.md](./FEATURES.md), [ARCHITECTURE.md](./ARCHITECTURE.md), and [PITFALLS.md](./PITFALLS.md).

### Recommended Stack

Use current stable framework lines, pin compatible minors, commit lockfiles, and pin service images by digest. The compatibility anchor is Google ADK 2.2, which drives the Python, FastAPI, Pydantic, and Google Gen AI SDK ranges. Keep provider adapters thin and local rather than adding a broad agent framework abstraction.

**Core technologies:**
- Next.js `>=16.2,<16.3`, React `>=19.2,<19.3`, TypeScript `>=5.9,<6`, and Tailwind CSS `>=4.3,<4.4`: stable App Router frontend with typed, safe chat rendering.
- Python `>=3.13,<3.14`, FastAPI `>=0.136,<0.137`, and Pydantic `>=2.12,<3`: explicitly compatible backend baseline for ADK 2.2.
- SQLAlchemy `>=2.0.50,<2.1`, Alembic `>=1.18.4,<1.19`, PostgreSQL 18 current patch, and Psycopg 3: explicit models, reviewed migrations, transactions, and durable security state.
- PyJWT with RS256 and `pwdlib[argon2]`: strict access-token validation and modern password hashing.
- Opaque refresh tokens with server-side hashed family records: rotation, replay detection, revocation, and concurrency control.
- OpenAI Python SDK `>=2,<3`: configurable OpenAI-compatible normal-chat adapter with bounded timeout and retry behavior.
- `google-adk >=2.2,<2.3` and `google-genai >=2.8,<2.9`: search-only worker behind a model-neutral grounding envelope.
- Kong OSS DB-less with declarative configuration: route allowlisting, CORS, request-size limits, coarse JWT screening, correlation IDs, and single-node local rate limits.
- Docker Compose v2 and hardened Linux containers: reproducible local topology and bounded Python execution.
- pytest, HTTPX, Ruff, mypy, Semgrep, Bandit, pip-audit, Trivy, and ZAP: layered functional, security, dependency, image, IaC, and black-box verification.

**Critical version decisions:**
- Prefer Python 3.13 because ADK 2.2 explicitly covers it; do not assume Python 3.14 compatibility.
- Keep TypeScript 5.9 until project tooling proves TypeScript 6 compatibility.
- Treat Kong OSS 3.9.1 as a constrained prototype dependency with time-limited support, not a long-term production gateway choice.
- Configure the Gemini 2 model ID through deployment settings. On each environment and before the demonstration, run a capability smoke test for model availability, Google Search support, and expected grounding metadata.

### Expected Features

**Must have (table stakes):**
- Registration, login, logout, `/me`, Argon2id password handling, non-enumerating errors, and authentication abuse controls.
- Short-lived access JWTs with exact algorithm, issuer, audience, type, time, subject, and token-ID validation.
- HttpOnly refresh cookie, memory-only access token, CSRF/Origin protection, atomic refresh-family rotation, replay-family revocation, and logout invalidation.
- Roles, scopes, active-account checks, exact tool permissions, and owner-constrained conversation/message queries.
- Durable conversation and message history, stable ordering, idempotent sends, safe Markdown/code rendering, clear loading/error states, and non-streaming fallback.
- Configurable OpenAI-compatible normal chat with bounded provider behavior and stable application errors.
- Deterministic coordinator for direct chat, search, or Python, with one bounded tool invocation per turn in v1.
- Search-only Google ADK service that preserves the live grounding contract and renders required Search Suggestions under current terms.
- Dedicated Python execution boundary with no network, non-root execution, read-only root, temporary workspace, dropped capabilities, seccomp, and hard CPU, memory, PID, time, file, and output limits.
- Endpoint-specific Kong policy plus full FastAPI defense in depth.
- Structured redacted logs, request/trace correlation, audit records, security events, tool execution states, and minimal admin evidence APIs.
- One-command Compose startup, health/readiness checks, automated adversarial tests, and Vietnamese setup, architecture, security, testing, and incident documentation.

**Should have (competitive):**
- Security evidence center linking controls to current passing tests and redacted events.
- Tool authorization receipts showing required scope, decision, reason, execution ID, and correlation ID.
- Refresh-replay incident evidence and visible search/sandbox separation in traces.
- Citation-integrity rendering with UTF-8-safe support offsets and no false "grounded" label.
- Sandbox isolation proof mode showing effective runtime controls.
- Per-request and per-user cost/tool budgets.
- Vietnamese security evidence report suitable for project evaluation.

**Defer to v1.x:**
- Conversation search/archive, session/device management, password reset/email verification, refined streaming cancellation, usage dashboard, exportable evidence, OpenTelemetry stack, and optional Cloudflare Turnstile profile.

**Defer to v2+:**
- External OIDC/SSO, MFA/WebAuthn, organizations, sharing, files/RAG/connectors, long-term memory, additional write-capable tools, billing, and stronger multi-tenant sandbox runtimes.

### Architecture Approach

Use a modular monolith for application policy and persistence, with separate services only where credentials or execution risk justify them. FastAPI owns all security decisions and calls provider/tool adapters through typed contracts. The search service has only Google credentials and Google Search capability. The sandbox control plane accepts only a named fixed policy profile and never arbitrary images, commands, mounts, devices, capabilities, environment variables, or networking options. PostgreSQL is private to the backend, and all services communicate over explicit least-reach Compose networks.

**Major components:**
1. **Next.js frontend** -- auth and conversation UX, memory-only access token, safe Markdown/code, grounded citation UI, and isolated Search Suggestions rendering.
2. **Kong Gateway** -- public route inventory, request-size limits, strict CORS, coarse endpoint rate limits, correlation metadata, and optional signature/`exp`/`nbf` screening.
3. **FastAPI backend** -- identity, token lifecycle, authorization, owner-scoped data access, chat coordination, provider adapters, audit, and application budgets.
4. **PostgreSQL** -- users, refresh families, conversations, messages, tool states, permitted grounding records, audit logs, and security events.
5. **OpenAI-compatible adapter** -- normal chat only, with fixed operator configuration and bounded retries/timeouts.
6. **Google ADK search service** -- search-only credential boundary and model-neutral extraction of grounded answer data.
7. **Sandbox control plane and runtime** -- trusted fixed-profile controller plus isolated no-network Python execution that receives no application secrets.
8. **Security test and evidence layer** -- stateful multi-user attacks, runtime sandbox checks, SAST/DAST, and correlated proof.

**Required patterns:**
- Policy-before-model: model output can propose a typed action but cannot authorize it.
- Narrow internal capability tokens: one short-lived, audience-bound token per tool invocation; never forward end-user bearer tokens.
- Transactional state around external calls: persist accepted state, call providers outside a DB transaction, then finalize in a short transaction.
- Owner-scoped repositories: retrieve tenant-owned objects by object ID and authenticated owner in the same query.
- Grounding as a typed end-to-end contract: preserve exact response text and offset mappings before Markdown transformation.
- Defense in depth: Kong rejects coarse invalid traffic; FastAPI independently performs complete token and application authorization.
- Explicit network zones: edge, app, data, search, sandbox, and provider-specific egress; do not use one default Compose network.

### Resolved Conflicts

1. **Named Gemini model versus deprecation risk:** `STACK.md` recommends a specific Gemini 2 model, while `ARCHITECTURE.md` notes that model is already in its documented earliest-shutdown month. Resolution: do not name a default model in application contracts or this roadmap. Require a configured Gemini 2 model and a deployment-time capability test. If no qualifying Gemini 2 model remains available, stop search startup and surface the project-constraint conflict rather than silently using an ungrounded or different-generation model.
2. **Persist all grounding metadata versus terms-limited retention:** architecture favors durable structured grounding, while feature research warns that current Google terms restrict caching, storage, and link-level tracking. Resolution: the live response contract carries all required fields to the same end user, but persistence uses a separately reviewed allowlist. Persist exact answer text and only metadata explicitly allowed by the terms effective at implementation time; never add source-link click tracking. Historical UI must not reconstruct citations or label content grounded when retained evidence is insufficient.
3. **ADK tool-composition necessity versus newer workarounds:** newer SDKs may support more combinations, but separate search and Python services remain the v1 decision for least privilege, credential isolation, stable metadata handling, and independent failure limits. A version change cannot collapse these boundaries without a new threat review and contract tests.
4. **Ephemeral per-job containers versus Docker-socket risk:** architecture prefers one disposable container per execution, while pitfalls correctly reject exposing Docker control to the backend or user-code worker. Resolution: Docker control belongs only to a minimal trusted control-plane component on an isolated boundary, with fixed job specifications and no public reachability; it is never mounted into FastAPI or the untrusted runtime. If the local prototype cannot provide that boundary safely, use a pre-created fixed worker/pool and document the reduced isolation instead of mounting the socket broadly.
5. **Grounding persistence versus citations after reload:** user expectations favor durable citations, but legal/provider terms take precedence. Resolution: make retention behavior explicit in the schema and UI. Preserve durable citation behavior only when current terms allow the required fields; otherwise retain the answer while marking historical source details unavailable.
6. **Kong JWT verification versus backend authority:** Kong is an early rejection layer only. Preserve standard issuer semantics and keep exact issuer, audience, type, scope, role, account, ownership, and revocation checks in FastAPI.

### Critical Pitfalls

1. **JWT signature accepted without token meaning** -- define mutually exclusive token profiles and test wrong issuer, audience, type, algorithm, times, subject, and token ID against FastAPI and the gateway path.
2. **Refresh rotation that is replayable or racy** -- store only indexed token hashes, preserve family lineage, rotate under a row lock or conditional transaction, revoke the family on reuse, and test concurrent refresh.
3. **BOLA hidden behind UUIDs or nested routes** -- make ownership part of every repository query and run a real two-user matrix across read, list, append, update, and delete paths.
4. **Scope or tool policy bypass through model/internal calls** -- use one deny-by-default policy service immediately before every execution and assert that denied calls create no provider request, job, or side effect.
5. **Prompt guardrails treated as authorization** -- regard prompts, model output, and search content as untrusted; verify zero forbidden side effects rather than checking refusal wording.
6. **Grounding evidence dropped, falsified, or retained unlawfully** -- keep a typed live contract, only mark responses grounded when metadata exists, render required suggestions safely, and apply a terms-reviewed persistence allowlist.
7. **Sandbox receives Docker or host authority** -- no privileged mode, host namespaces, host mounts, application secrets, broad daemon access, or user-controlled runtime options; verify effective controls from outside the sandbox.
8. **Rate limiting mistaken for resource control** -- combine route/IP limits with backend subject, concurrency, token, search, tool, output, and wall-time budgets; document that Kong local counters are single-node only.
9. **Logs become a secret/content database** -- allowlist fields, recursively redact, keep raw prompts/code/output out of ordinary logs, and scan canary secrets across success and failure paths.
10. **Security tests prove scripts rather than properties** -- test the real Compose topology, use positive controls, assert database/network/process side effects, and fail with a nonzero status.

## Implications for Roadmap

Based on combined dependencies and risk, use seven phases.

### Phase 1: Security Contracts and Platform Skeleton
**Rationale:** Token, authorization, state, provider, redaction, and trust-boundary contracts must exist before APIs and tools invent incompatible semantics.
**Delivers:** Threat model; principal/role/scope/tool matrix; access-token profile; refresh-family state machine; message/tool states; grounding retention policy; internal capability-token contract; redaction schema; Compose network skeleton; health checks; database migrations and indexes; request/trace context and audit writer.
**Addresses:** Reproducible startup, structured evidence foundation, durable data model.
**Avoids:** Token-purpose confusion, one default network, late audit retrofits, ambiguous grounding retention.

### Phase 2: Identity, Sessions, and Owner-Scoped APIs
**Rationale:** Identity, session revocation, and BOLA-resistant data access are prerequisites for all chat and tool work.
**Delivers:** Registration/login/logout/me; Argon2id; strict access JWTs; HttpOnly refresh flow; CSRF/Origin checks; atomic rotation and replay response; active-account checks; RBAC/scopes; owner-scoped conversation/message CRUD; minimal admin authorization boundaries.
**Addresses:** Authentication, secure browser session contract, conversation lifecycle, durable history, object-level authorization.
**Avoids:** JWT semantic gaps, refresh races, OIDC/token confusion, BOLA, route-only authorization.

### Phase 3: Normal Chat and Browser Experience
**Rationale:** Prove the core product and persistence protocol before adding higher-risk tools.
**Delivers:** OpenAI-compatible adapter; idempotent non-streaming message flow; bounded context, timeout, retry, and error mapping; Next.js auth and chat UI; memory-only access token; safe Markdown/code; clear pending/error/retry behavior. Add SSE only if final persistence and cancellation remain correct.
**Addresses:** Chat table stakes and provider configurability.
**Avoids:** External calls inside DB transactions, duplicate provider purchases, unsafe HTML, silent message loss.

### Phase 4: Coordinator and Google Search Vertical Slice
**Rationale:** This is the most time-sensitive integration and should be validated end to end before broad implementation.
**Delivers:** Deterministic one-tool coordinator; mock tool clients; search-only ADK service; configured-model capability gate; final-event extraction; live grounding envelope; compliant persistence allowlist; citation-integrity renderer; isolated Search Suggestions; grounded/ungrounded UX; search budgets and audit receipts.
**Addresses:** Google Search grounding, policy-before-model, provider-boundary transparency.
**Avoids:** Retired model hardcoding, unsupported ADK composition, false citations, indirect prompt escalation, prohibited retention/tracking.

### Phase 5: Python Sandbox Boundary
**Rationale:** Code execution is the highest-risk capability and should arrive only after identity, policy, audit, tool states, and internal capability authentication are proven.
**Delivers:** Fixed-profile sandbox API; narrow capability verification; dedicated runtime; no network; non-root/read-only/tmpfs execution; dropped capabilities; seccomp; CPU/memory/PID/time/file/output limits; cleanup; bounded result schema; isolation proof tests.
**Addresses:** Scope-gated Python execution and visible tool lifecycle.
**Avoids:** Backend `exec`, model-selected runtime options, Docker-socket exposure to application/user code, host/network access, unbounded output and denial of wallet.

### Phase 6: Gateway, Deployment Hardening, and Evidence APIs
**Rationale:** Gateway rules must be applied to stable routes and tested without replacing backend controls.
**Delivers:** Kong DB-less routes; strict CORS; request-size and endpoint rate limits; correlation plugin; optional issuer-level JWT screening; explicit trusted proxy handling; private service ports/networks; image/runtime scanning; minimal admin audit/security/tool views; optional Cloudflare deployment profile.
**Addresses:** Endpoint-specific abuse controls, defense in depth, operator visibility.
**Avoids:** Overloaded issuer claims, Consumer-per-user design, spoofed forwarding headers, exposed Admin API, claims of distributed limits with local counters.

### Phase 7: Adversarial Verification and Vietnamese Delivery
**Rationale:** Security is complete only when the assembled runtime demonstrates the claimed properties and limitations.
**Delivers:** Compose-based functional and attack suite; JWT corpus; concurrent refresh replay; two-user BOLA matrix; role/scope/tool policy matrix; brute force/rate-limit tests; direct and indirect prompt injection with zero side effects; SSRF/egress checks; sandbox resource/escape attempts; canary-secret log scans; SAST/DAST/image/IaC reports; Vietnamese setup, architecture, security, testing, limitations, and incident runbooks.
**Addresses:** Security evidence center, evaluator usability, final acceptance.
**Avoids:** Mock-only assurance, scanner-only claims, model-refusal screenshots as proof, silently skipped platform controls.

### Phase Ordering Rationale

- Freeze token, ownership, tool, grounding, and redaction contracts before implementation because retrofits affect every layer.
- Establish observability early so denial, replay, and tool behavior produce evidence throughout development.
- Build normal chat before tools to validate identity, persistence, idempotency, and UI contracts with lower risk.
- Spike Google Search before the sandbox because model availability, ADK events, grounding metadata, rendering, and terms are externally time-sensitive.
- Add Python only after the same policy and audit path can prove authorization immediately before execution.
- Apply Kong after route shapes stabilize, while continuously requiring direct-backend tests so gateway configuration never becomes the authorization boundary.
- Run attack tests throughout each phase, then execute the full assembled-topology evidence pass in Phase 7.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** Freeze the exact access-token profile, refresh-family transition rules, future external-identity `(issuer, subject)` model, grounding retention allowlist, and internal capability token.
- **Phase 4:** Re-check current Gemini model availability, ADK/Gen AI SDK compatibility, returned event schema, Google Search Suggestions rendering, CSP behavior, and current Google terms immediately before implementation.
- **Phase 5:** Spike the Docker Desktop/WSL2 host behavior, effective cgroup/seccomp controls, and the trusted control-plane design before promising per-job isolation.
- **Phase 6:** Validate Kong OSS version/support status, JWT credential mapping, trusted proxy chain, and whether the target topology remains single-node.

Phases with standard patterns that generally do not need a separate research phase:
- **Phase 2:** Password hashing, strict JWT validation, opaque refresh-family rotation, CSRF protection, and owner-scoped CRUD are well documented, but require careful design review and negative tests.
- **Phase 3:** OpenAI-compatible adapter, non-streaming chat persistence, safe Markdown, and idempotent request patterns are established.
- **Phase 7:** Test design is well sourced; planning should focus on traceability and executable evidence rather than additional technology research.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Current official framework/package sources and explicit compatibility ranges; Gemini model and Kong support status remain time-sensitive. |
| Features | HIGH | Requirements align with current OAuth/JWT, OWASP API/LLM, Docker, Google, and gateway guidance. |
| Architecture | HIGH | Trust boundaries and modular-monolith approach are strongly supported; sandbox control-plane implementation is MEDIUM-HIGH. |
| Pitfalls | HIGH | Based on standards, OWASP guidance, vendor constraints, and concrete negative-test properties. |

**Overall confidence:** HIGH for roadmap direction; MEDIUM for exact Gemini/ADK and host-level sandbox implementation choices.

### Gaps to Address

- **Gemini 2 availability:** Select through configuration and prove availability plus grounding capability on the implementation and demonstration dates. Do not silently fall back.
- **Google retention semantics:** Review the current terms before schema finalization; separate live transport fields from durable storage fields.
- **Sandbox control plane:** Decide between an isolated fixed-profile daemon controller and a pre-created worker/pool without exposing Docker authority to FastAPI or user code.
- **Windows-host assurance:** Record Docker Desktop/WSL2 runtime details and verify effective limits; fail or clearly mark unsupported tests rather than skipping them.
- **Browser session architecture:** Confirm same-site versus cross-site deployment, cookie path/domain, CSRF token flow, and refresh serialization before frontend implementation.
- **Deletion/retention policy:** Define what conversation deletion removes and which redacted security/audit records remain.
- **Streaming scope:** Default to correct non-streaming persistence; add SSE only when proxy buffering, disconnect cancellation, and final-message atomicity are proven.
- **PostgreSQL RLS:** Decide whether it is included as defense in depth after application-level owner-scoped queries; do not use it as a substitute for repository authorization.
- **Kong scaling claim:** Local counters are acceptable only for the one-node prototype; Redis/shared limiting is required before multi-node claims.
- **Cloudflare source-IP trust:** If enabled, specify the exact trusted proxy path and reject spoofed forwarding headers from direct clients.

## Sources

### Primary (HIGH confidence)
- [RFC 9700](https://www.rfc-editor.org/rfc/rfc9700) and [RFC 8725](https://www.rfc-editor.org/rfc/rfc8725) -- refresh-token replay protection and JWT best practices.
- [RFC 9068](https://www.rfc-editor.org/rfc/rfc9068) and [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0-18.html) -- access-token typing and ID-token/provider separation.
- [OWASP API Security](https://owasp.org/API-Security/) and [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/) -- BOLA, function authorization, resource consumption, SSRF, and verification.
- [OWASP GenAI Security](https://genai.owasp.org/) -- prompt injection, excessive agency, unbounded consumption, and agentic risks.
- [Google ADK tool limitations](https://google.github.io/adk-docs/tools/limitations/) and [Google Search tool](https://google.github.io/adk-docs/tools/gemini-api/google-search/) -- ADK composition and search requirements.
- [Gemini Google Search grounding](https://ai.google.dev/gemini-api/docs/google-search), [model availability](https://ai.google.dev/models/gemini), [deprecation schedule](https://ai.google.dev/gemini-api/docs/deprecations), and [additional terms](https://ai.google.dev/gemini-api/terms) -- metadata, availability, rendering, and retention constraints.
- [Docker security](https://docs.docker.com/engine/security/), [resource constraints](https://docs.docker.com/engine/containers/resource_constraints/), and [Compose networking](https://docs.docker.com/compose/how-tos/networking/) -- runtime and network controls.
- [Kong DB-less mode](https://developer.konghq.com/gateway/db-less-mode/), [JWT](https://developer.konghq.com/plugins/jwt/), and [rate limiting](https://developer.konghq.com/plugins/rate-limiting/) -- gateway capabilities and limitations.
- Official Next.js, React, TypeScript, Tailwind, FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL, Google Gen AI SDK, and Google ADK release/package documentation summarized in [STACK.md](./STACK.md).

### Secondary (MEDIUM confidence)
- IETF browser-based applications guidance pending final RFC publication at research time -- supports BFF/token-mediation direction but should be replaced with the final RFC if published before Phase 2.
- Docker Desktop/WSL2 behavior -- official controls are clear, but effective enforcement depends on the evaluator's host/runtime configuration and must be measured.

### Tertiary (LOW confidence)
- None used for roadmap-critical conclusions.

---
*Research completed: 2026-06-08*
*Ready for roadmap: yes*
