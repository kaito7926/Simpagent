# Feature Research

**Domain:** Secure AI chatbot SaaS prototype with lightweight agent tools
**Researched:** 2026-06-08
**Confidence:** HIGH overall; MEDIUM for rapidly changing Google ADK tool-composition details

## Research Position

For this project, security is part of the product surface. A control is not complete merely because configuration exists: it must have a user-visible or operator-visible outcome, a negative test, and correlated evidence. The recommended v1 is therefore a narrow ChatGPT-like experience with strong identity, authorization, grounding, sandbox, gateway, and audit behavior rather than a broad assistant with many tools.

Current ecosystem signals as of June 2026:

- OAuth Security BCP RFC 9700 requires replay protection for public-client refresh tokens through sender-constraining or rotation. For this prototype, use refresh-token-family rotation and reuse detection.
- The latest browser-based OAuth guidance has been approved by the IESG but was still an Internet-Draft awaiting RFC publication when researched. Its preferred pattern keeps refresh tokens in a backend/BFF-style session rather than persistent JavaScript-accessible storage.
- OWASP API Security continues to rank Broken Object Level Authorization first. RBAC and scopes do not replace per-object ownership checks.
- OWASP's 2025 LLM risks explicitly treat prompt injection, excessive agency, and unbounded consumption as application design problems. Model instructions alone are not authorization controls.
- Google ADK's current `GoogleSearchTool` documentation says it is Gemini 2-compatible, requires Search Suggestions to be rendered, and documents a single-built-in-tool-per-agent limitation. The newer raw Gemini API documentation, updated May 18, 2026, supports additional models and tool combinations. Google's terms effective March 23, 2026 also restrict caching and link-level tracking of grounded results, suggestions, and links. Because this project specifically requires Gemini 2 through ADK, v1 should retain a dedicated search agent behind a deterministic coordinator, transport grounding metadata only as needed for compliant rendering, and pin/test the ADK version.

## Feature Landscape

### Table Stakes (Users Expect These)

Missing these features makes either the chatbot incomplete or the security claim indefensible.

| Feature | Why Expected | Complexity | Depends On | Testable Expected Behavior |
|---------|--------------|------------|------------|----------------------------|
| Registration, login, logout, and current-user profile | Baseline SaaS account lifecycle | MEDIUM | User model, password hashing, email normalization | A new user can register and authenticate; duplicate email and invalid credentials return non-enumerating errors; logout invalidates the active refresh session; `/me` returns only the authenticated subject |
| Modern password handling | Password compromise invalidates every higher-level control | MEDIUM | Argon2id library, password policy, secret configuration | Passwords are never stored or logged; weak/known-compromised values are rejected; long passwords and Unicode are accepted; hashes include per-password salt and tunable work parameters |
| Short-lived, strictly validated access JWTs | APIs need portable, bounded authorization state | MEDIUM | Signing key management, issuer/audience design, clock policy | API rejects expired, malformed, wrong-issuer, wrong-audience, wrong-type, disallowed-algorithm, and invalid-signature tokens; accepted tokens contain `sub`, `role`, `scopes`, `exp`, `iat`, and `jti` |
| Refresh-token family rotation and replay response | Persistent sessions must survive access-token expiry without accepting stolen refresh tokens indefinitely | HIGH | RefreshToken persistence, hashing, transactions, session cookie strategy | Every successful refresh invalidates the presented token and returns a new token; reuse of any rotated token revokes the active family, emits a security event, and forces reauthentication; concurrent refresh has deterministic one-winner behavior |
| Secure browser token handling | Persistent browser-readable bearer tokens make XSS impact much larger | MEDIUM | Same-site deployment or BFF/session endpoint, CSRF defense | Refresh token is not available to JavaScript and is delivered only by `Secure`, `HttpOnly`, appropriately `SameSite` cookie in deployed HTTPS mode; access token is memory-only or requests are proxied by the backend; CSRF tests fail closed |
| Authentication abuse controls | Login and registration are predictable bot and credential-stuffing targets | MEDIUM | Kong routes, app counters/security events, trusted client-IP handling | Login/register have stricter limits than chat; repeated failures produce `429` or progressive delay without revealing account existence; successful and failed attempts are correlated and secrets are absent from logs |
| Role, scope, active-account, and tool-permission checks | Admin/user roles alone are too coarse for agent tools | HIGH | Token claims, authorization dependency, policy mapping | Every protected request validates active user status, required role, required scopes, and tool permission; a user token cannot call admin APIs; missing `tool:websearch` or `tool:python` returns `403` before provider or worker invocation |
| Object-level authorization for conversations and messages | Conversation IDs are attacker-controlled inputs and BOLA is a primary API risk | HIGH | Ownership-aware repository queries, authenticated subject | Every read, write, list, and delete query is constrained by owner; replacing a conversation ID with another user's ID never exposes existence or data; automated two-user negative tests cover all object routes |
| Conversation lifecycle | Chat products require durable sessions users can resume and remove | MEDIUM | PostgreSQL models, ownership checks | User can create, list, open, rename/title, and delete only their own conversations; ordering is stable and paginated; deletion removes the conversation from subsequent list/read operations according to documented retention behavior |
| Durable message history | Users expect context continuity and reload-safe chats | MEDIUM | Conversation model, message ordering, LLM adapter | User and assistant messages are stored with immutable role/order/timestamps; refresh returns the same ordered transcript; a failed provider call does not fabricate a successful assistant message |
| Responsive chat composer and response state | A ChatGPT-like prototype must communicate progress and failure clearly | MEDIUM | Chat endpoint, request IDs, frontend state | Submit disables duplicate send, shows pending/streaming state, supports retry after provider error, preserves unsent input on failure, and displays a correlation ID or support reference for unexpected errors |
| Streaming with graceful fallback | Incremental output is now normal chatbot UX, but reliability matters more than streaming | HIGH | SSE or fetch streaming, proxy timeout configuration, persistence protocol | When enabled, chunks render in order and final persisted text equals displayed text; disconnect/cancel ends provider work where possible; when streaming is unavailable, normal JSON response still completes the same conversation contract |
| Safe Markdown and code rendering | AI answers routinely include lists, links, tables, and code | MEDIUM | Markdown parser, syntax highlighter, sanitization policy | Markdown and fenced code render correctly; raw HTML/script/event handlers and dangerous URL schemes do not execute; long code blocks scroll and can be copied without mutating content |
| Configurable normal-chat provider | The brief requires real OpenAI-compatible operation without provider lock-in | MEDIUM | Environment validation, HTTP client, model adapter | Startup reports missing required provider configuration without exposing secrets; normal chat uses configured base URL/model/key; provider timeout, rate limit, and malformed response map to stable application errors |
| Deterministic agent coordinator | Tool authorization cannot be delegated to stochastic model output | HIGH | Tool registry, policy engine, ADK search agent, sandbox client | Coordinator may route to direct chat, search, or Python only from an allowlist; policy checks occur immediately before execution; unknown tool names and model attempts to override policy are rejected and logged |
| Explicit tool state in chat | Users need to know when data leaves the normal chat path or code is executed | MEDIUM | Tool execution records, frontend event model | UI shows requested/running/succeeded/failed/denied states, tool name, duration, and a safe input/output summary; denied tools do not appear as successful assistant work |
| Google Search grounding contract | Search answers without preserved grounding metadata lose provenance and may violate Google's display requirements | HIGH | Gemini 2 credentials, ADK search-only agent, response schema, frontend renderer, retention policy | For the live response, backend transports response text plus `webSearchQueries`, `searchEntryPoint.renderedContent`, `groundingChunks`, and `groundingSupports` without semantic rewriting; frontend renders clickable inline citations and required associated Search Suggestions; persistence and telemetry store only what current Google terms permit |
| Search failure and freshness UX | Search is external, billable, and fallible | MEDIUM | Search timeout, result schema, provider status | Search timeout or provider failure is labeled as such and never presented as grounded; ungrounded fallback is clearly distinguished or disabled; source links open safely; result count and duration are logged |
| Scope-gated Python sandbox execution | Code execution is valuable but is the highest-risk product capability | HIGH | Dedicated worker, isolated container image, tool policy | Only users with `tool:python` can submit bounded code; backend never calls `exec`, `eval`, or host Python for user code; response contains exit status, bounded stdout/stderr, duration, and timeout/resource-limit reason |
| Sandbox network, filesystem, process, and resource controls | A container without explicit limits is not a sandbox claim | HIGH | Docker runtime, worker lifecycle, hardened image | Execution runs non-root with no network, read-only root filesystem, temporary writable workdir, dropped capabilities, `no-new-privileges`, seccomp, PID/CPU/memory/output/time limits, no Docker socket, and cleanup after each run |
| Endpoint-specific gateway policy | Auth, chat, search, and Python have different cost and abuse profiles | MEDIUM | Kong DB-less route inventory, trusted proxy configuration | Kong applies strict CORS allowlist, request-size limits, correlation ID, and distinct rate limits; exceeded limits return `429` with retry metadata; browser preflight works on path/method-matched routes |
| Defense in depth between Kong and FastAPI | Gateway checks cannot replace application authorization or token lifecycle checks | MEDIUM | Kong JWT feasibility, backend JWT verifier | Requests bypassing Kong in test still fail backend authentication/authorization; Kong may reject invalid/expired JWTs early, but FastAPI remains authoritative for issuer/audience, active user, scopes, ownership, revocation-sensitive flows, and tool policy |
| Structured logs and cross-service correlation | Operators need to reconstruct a request through gateway, API, provider, and worker | HIGH | Correlation middleware/plugin, JSON schema, propagation rules | One correlation ID is propagated through Kong, FastAPI, LLM/tool calls, sandbox, audit, and response; malformed client-supplied IDs are replaced; logs are valid JSON and searchable by correlation ID |
| Audit logs and security events | Admin actions and denied operations require durable evidence distinct from debug logs | HIGH | AuditLog/SecurityEvent models, redaction, admin scopes | Auth failures, forbidden access, refresh reuse, rate limits, tool decisions/execution, admin actions, and sandbox violations create typed records with actor/resource/result/reason/time/correlation; passwords, tokens, API keys, raw cookies, and full secrets never appear |
| Minimal security administration views/APIs | The evaluator must be able to inspect evidence without database access | MEDIUM | Admin RBAC/scopes, pagination, redacted schemas | Properly scoped admin can list users, recent audit logs, tool executions, failed logins, and security events; ordinary users receive `403`; list endpoints paginate and do not disclose credential material |
| Health, readiness, and degraded-provider reporting | Multi-service local demos need diagnosable startup behavior | LOW | Dependency probes, Compose health checks | `/health` reports process liveness; `/ready` fails until required database/migrations are usable; optional external provider status is reported without leaking configuration |
| Reproducible local startup | One-command execution is an explicit acceptance criterion | HIGH | Dockerfiles, Compose networks/volumes, migrations, environment template | `docker compose up --build` starts frontend, backend, PostgreSQL, Kong, and sandbox foundation; health checks converge; missing model credentials produce documented degraded behavior rather than secret-bearing stack traces |
| Automated functional and adversarial tests | Security assertions without executable proof are weak project evidence | HIGH | Test fixtures, two-user identities, controllable sandbox/provider test doubles | CI/local commands prove auth lifecycle, BOLA denial, admin denial, missing tool scopes, refresh replay response, rate limiting, SSRF controls, prompt/tool abuse handling, and sandbox timeout/network/memory/escape defenses |
| Vietnamese setup, architecture, security, testing, and runbook documentation | Vietnamese documentation is a stated deliverable and part of evaluator usability | MEDIUM | Stable commands/configuration, diagrams, evidence outputs | A Vietnamese reader can start, configure, use, test, and troubleshoot the system from docs; JWT lifecycle, trust boundaries, scopes, BOLA, grounding, sandbox, Kong/Cloudflare assumptions, SAST/DAST, and incident runbooks match implemented behavior |
| Clear limitations and data handling statements | Users must know this is a prototype using external model/search providers | LOW | Provider inventory, retention choices | UI/docs state that prompts may be sent to configured providers, search is separately invoked, Python is isolated but not a production multi-tenant sandbox, and the system is not a compliance-certified service |

### Differentiators (Competitive Advantage)

These features align with the project's core value: demonstrating controlled agent capabilities without crossing identity, object, network, or execution boundaries.

| Feature | Value Proposition | Complexity | Depends On | Testable Expected Behavior |
|---------|-------------------|------------|------------|----------------------------|
| Security evidence center | Turns security from a configuration claim into evaluator-visible proof | HIGH | Audit/security events, attack tests, admin APIs | Each named control links to its implementation status, latest passing test/evidence, and relevant redacted events; stale or failed evidence is visible rather than silently green |
| Tool authorization receipt | Makes least-privilege decisions understandable to users and evaluators | MEDIUM | Policy engine, tool event schema | Every tool attempt records requested tool, required scope, decision, policy reason, execution ID, and correlation ID; denial receipt contains no hidden system prompt or secret |
| Refresh-token family incident evidence | Demonstrates replay detection rather than only nominal logout | MEDIUM | Rotation/reuse detection, security events | Replaying an old refresh token revokes its family, blocks the newest token, records both token-family and correlation identifiers in redacted form, and appears in the admin security view |
| Citation-integrity renderer | Preserves claim-to-source relationships instead of appending an unverified source list | HIGH | Grounding response transport, UTF-8-safe segment mapping, terms-compliant retention | Inline citation links in the live grounded response correspond to Google `groundingSupports`/`groundingChunks`; multibyte Vietnamese text does not shift citation placement; missing metadata cannot be labeled grounded; historical display does not reconstruct or retain restricted links |
| Search/sandbox separation visible in traces | Demonstrates correct handling of ADK constraints and different trust boundaries | MEDIUM | Dedicated ADK search worker, custom sandbox worker, coordinator | Trace/evidence shows search and Python are separate executions with independent scope checks and timeouts; no agent instance is configured with unsupported combined tools in the pinned v1 path |
| Sandbox isolation proof mode | Makes invisible container controls demonstrable | HIGH | Worker telemetry, controlled attack fixtures | A report records effective UID, network absence, mount mode, resource limits, timeout result, blocked process/capability attempts, and cleanup without exposing host internals |
| Policy-before-model architecture | Limits prompt-injection impact by keeping authorization deterministic | HIGH | Coordinator and service boundaries | Prompt injection asking to grant scopes, call unknown APIs, read secrets, or bypass sandbox is ignored by code-level policy; tests prove no provider/tool call occurs after denial |
| Cost-aware tool budgets | Protects a university demo from denial-of-wallet and runaway loops | MEDIUM | Per-user quotas, request/token/tool counters | A request has maximum model calls, tool calls, search calls, output size, and wall time; exceeding any budget stops cleanly, emits a reason, and does not continue in background |
| Vietnamese security evidence pack | Makes the project unusually usable for local evaluation and defense presentation | MEDIUM | Vietnamese docs, generated test artifacts | One documented command produces a Vietnamese summary of passed/failed security scenarios with timestamps, versions, and correlation IDs suitable for inclusion in the project report |
| Provider-boundary transparency | Helps users distinguish normal LLM, Google-grounded search, and local sandbox processing | LOW | Tool states, provider metadata | Each assistant response identifies the processing path and whether sources/tools were used, without exposing API keys or internal chain-of-thought |
| Optional Cloudflare abuse-control profile | Demonstrates realistic edge hardening while preserving a fully local core | MEDIUM | Cloudflare deployment docs, Turnstile server validation | When enabled, login/register require a valid single-use Turnstile token verified server-side; local mode has an explicit development bypass that cannot be enabled accidentally in production mode |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Refresh/access tokens persisted in `localStorage` | Simple SPA implementation and survives reloads | Any same-origin script running after XSS can read persistent bearer tokens; refresh-token theft creates a long-lived session risk | Use a BFF-like backend session or `HttpOnly` refresh cookie with CSRF defense; keep access token memory-only if the browser must hold one |
| Calling local password login “full OIDC” | Sounds standards-compliant in a project demo | Local credentials plus custom JWT endpoints are not an OpenID Provider and should not make false interoperability claims | Implement an OIDC-ready identity adapter and document local auth honestly; add a real external OIDC provider only after core validation |
| Gateway-only authentication/authorization | Centralized policy looks simpler | Kong's basic JWT plugin validates limited registered claims and cannot enforce database ownership, active-account state, refresh-family incidents, or tool policy | Use Kong for early rejection and traffic control; keep FastAPI authoritative for complete authorization |
| RBAC-only access control | Admin/User roles are easy to explain | Roles do not prove ownership and do not prevent BOLA between two ordinary users | Combine role, scope, relationship/ownership, account state, and explicit tool permissions on every request |
| Trusting client-supplied `user_id`, `role`, scopes, or conversation owner | Reduces backend lookup code | Lets callers select the authorization context they want | Derive identity from validated token/session and ownership from database relationships only |
| Letting the LLM approve its own tool use | Feels more agentic | Prompt injection and hallucination can become privilege escalation | Model may propose an allowlisted action; deterministic coordinator validates user scope, arguments, budgets, and policy immediately before execution |
| General URL fetch/browser tool | Broadens research capability | Creates SSRF, internal network discovery, credential forwarding, malicious-content, and arbitrary exfiltration paths | Use Google Search grounding only; do not expose fetch-by-URL in v1 |
| Arbitrary third-party API/function calling | Makes the assistant appear extensible | Expands excessive agency, secret distribution, data handling, and authorization complexity beyond the prototype's evidence capacity | Keep exactly two low-impact tools: grounded search and isolated Python |
| Host subprocess or in-process Python execution | Easy to build and fast | User code can inherit backend credentials, filesystem, network, and process privileges | Use a separate worker that launches hardened disposable containers; backend never evaluates user code |
| Mounting the Docker socket into the sandbox worker without a containment plan | Simplifies dynamic container creation | Docker socket access is effectively host-control authority if the worker is compromised | Prefer a tightly scoped runner service/runtime boundary; if Docker socket is unavoidable for the prototype, isolate and document it as a trusted control-plane component never reachable from user code |
| Network-enabled Python or runtime package installation | Users expect notebooks to install packages | Enables exfiltration, malware retrieval, dependency attacks, and non-reproducible execution | Ship a small allowlisted standard-library/scientific image; no network and no package manager in v1 |
| Privileged containers, disabled seccomp, added broad capabilities | Fixes compatibility issues quickly | Removes central container defenses and weakens sandbox-escape claims | Run non-root, drop capabilities, retain/tighten seccomp, set `no-new-privileges`, and fail startup if controls cannot be applied |
| Combining ADK Google Search and custom Python in one agent without a pinned integration test | Reduces orchestration code | ADK-specific documentation still describes single-tool limitations and workaround caveats, despite newer raw Gemini API combinations | Keep separate search and sandbox workers behind a coordinator for v1; revisit only with version-pinned contract tests |
| Discarding Google grounding metadata and generating a source list from model text | Simplifies the message schema | Loses claim-to-source mapping, can create fake citations, and may omit required Search Suggestions | Transport and render the structured grounding contract for the live response; retain only data allowed by current terms |
| Persisting or click-tracking Google grounded links/Suggestions as ordinary analytics | Makes history and source analytics easy | Current Gemini API terms restrict caching, storing, and link-level monitoring except for narrow stated allowances | Transport metadata transiently for the submitting user's grounded response; retain only terms-permitted grounded text/history data and no source-link click telemetry |
| Rendering `searchEntryPoint.renderedContent` or LLM Markdown without a security boundary | Vendor/model HTML seems ready to display | Generic unsanitized HTML can create XSS; Google's required widget also has policy-specific rendering requirements | Render vendor-provided Search Suggestions only in the documented location/path; sanitize all ordinary model Markdown and disallow arbitrary raw HTML |
| One global rate limit | Easy Kong configuration | Login, chat, search, and Python have radically different abuse and cost profiles | Use endpoint-specific limits plus per-user/tool budgets; trust forwarded IP headers only from configured proxies |
| Cloudflare as a required local dependency | Adds recognizable edge security | Makes the acceptance path depend on an external account and can hide whether Kong/FastAPI controls work | Keep Cloudflare optional and documented; local Compose must remain complete behind Kong |
| Relying on Bot Fight Mode for API correctness | It is free and automatic | Cloudflare documents that free Bot Fight Mode applies domain-wide, is not granular, and may challenge API/mobile traffic | Use Turnstile specifically on human auth forms and Kong/app rate limits for APIs; document Bot Fight Mode caveats |
| Detailed login errors and user-existence checks | Improves immediate form feedback | Enables account enumeration | Return generic authentication/registration recovery responses while logging specific internal reason securely |
| Logging full prompts, model responses, code, tokens, cookies, or headers by default | Maximizes debugging data | Creates a high-value secret and personal-data store; may expose prompt injection payloads or credentials | Log redacted summaries, hashes/identifiers, sizes, decisions, and correlation IDs; make any content capture explicit, bounded, and off by default |
| “Prompt injection blocked” as a binary product claim | Sounds like a strong security result | OWASP states foolproof prevention is unclear; filters can be bypassed | Claim impact containment: no secret context, no model-granted authority, allowlisted tools, complete mediation, output handling, budgets, and adversarial tests |
| Autonomous loops with no action/cost ceiling | Appears more capable | Enables denial-of-wallet, runaway tools, and difficult incident reconstruction | Maximum one tool path per v1 request or a small explicit call budget with wall-clock and token ceilings |
| Sensitive actions such as email, payment, destructive admin, or external deletion | Creates impressive demos | Requires consent, step-up auth, idempotency, rollback, and much stronger safety controls | Keep v1 tools read-only search and isolated computation only |
| Multi-tenant organization/team sharing in v1 | Fits the word “SaaS” | Multiplies authorization relationships, invitation flows, retention policy, and cross-tenant test surface | Use single-owner resources for the prototype; add organization tenancy only as a separately designed milestone |
| RAG, uploads, long-term memory, and connectors in v1 | Common chatbot expectations | Introduce ingestion security, indirect prompt injection, retention, malware, and data-isolation problems unrelated to the target demonstration | Explicitly defer; use durable conversation history only |
| Compliance or production-isolation claims | Helps presentation | A Docker Compose prototype and Docker sandbox are not by themselves evidence of production multi-tenant isolation or certification | State tested controls, assumptions, and known limitations precisely |

## Feature Dependencies

```text
[Structured correlation IDs]
    ├──requires──> [Shared event/log schema]
    ├──enables───> [Audit and security evidence]
    └──enables───> [Cross-service attack-test evidence]

[Registration/login]
    └──requires──> [User model + Argon2id password handling]
                       └──enables──> [Access JWT issuance]
                                        └──requires──> [Strict JWT validation]
                                        └──enables──> [RBAC + scopes]

[Persistent browser session]
    └──requires──> [Refresh token hashing + family rotation]
                       ├──requires──> [Transactional replay detection]
                       └──requires──> [HttpOnly cookie/BFF strategy + CSRF defense]

[Conversation/message APIs]
    ├──requires──> [Authenticated subject]
    └──requires──> [Ownership-constrained repository queries]
                       └──validated-by──> [Two-user BOLA tests]

[Admin evidence APIs]
    ├──requires──> [Admin role]
    ├──requires──> [admin:read/admin:write scopes]
    └──requires──> [Redacted audit/security event persistence]

[Tool execution]
    ├──requires──> [Allowlisted tool registry]
    ├──requires──> [Tool scopes + deterministic policy]
    ├──requires──> [Per-request budgets/timeouts]
    └──requires──> [ToolExecution audit record]

[Grounded Google Search]
    ├──requires──> [Pinned Gemini 2 + ADK integration]
    ├──requires──> [Dedicated search agent]
    └──requires──> [Grounding response schema + compliant retention]
                       └──requires──> [Citation + Search Suggestions UI]

[Python tool]
    └──requires──> [Dedicated sandbox worker]
                       └──requires──> [Disposable hardened container controls]
                                          └──validated-by──> [Timeout/network/memory/escape tests]

[Kong endpoint policy]
    ├──requires──> [Stable route inventory]
    ├──requires──> [Trusted proxy/client-IP policy]
    └──enhances──> [Application auth abuse and cost controls]

[Vietnamese final documentation]
    ├──requires──> [Stable startup/test commands]
    ├──requires──> [Implemented trust boundaries]
    └──requires──> [Generated evidence and known limitations]

[Arbitrary URL fetch] ──conflicts──> [No-SSRF/low-agency v1 scope]
[Networked package install] ──conflicts──> [Deterministic no-network sandbox]
[Gateway-only auth] ──conflicts──> [Complete mediation and BOLA defense]
[Raw HTML rendering] ──conflicts──> [Safe chat rendering]
```

### Dependency Notes

- **Identity precedes chat:** ownership, audit actor IDs, quotas, and tool scopes all depend on a stable authenticated subject.
- **Refresh rotation is transactional:** token-family state must be designed before frontend persistence. Adding replay detection after a stateless refresh implementation causes schema and UX rework.
- **Authorization has four independent inputs:** account state, role, scopes/tool permissions, and object relationship. All must be represented before route implementation is considered complete.
- **BOLA defense belongs in data access:** route checks should call owner-constrained repository/service methods so a missed post-fetch comparison cannot leak another user's object.
- **Grounding is an end-to-end feature:** search is incomplete until metadata survives provider parsing, API schemas, and frontend rendering. Database retention must be narrower than the live response contract where Google's terms restrict caching or storage.
- **ADK search and Python should remain separate in v1:** this matches the project's trust boundaries and avoids relying on rapidly changing multi-tool workarounds.
- **Sandbox tests require real runtime controls:** unit tests of command filtering do not establish no-network, filesystem, PID, memory, CPU, or timeout behavior.
- **Kong depends on route design:** rate limits, CORS, request-size rules, and optional JWT checks cannot be finalized before endpoint classes and browser-origin topology are known.
- **Evidence features start early:** correlation IDs and typed security events must be present during auth/tool implementation, not added as a final documentation phase.
- **Vietnamese docs should be continuously verified:** final translation after implementation is acceptable, but commands, diagrams, and security claims need automated or checklist-based validation against the running system.

## MVP Definition

### Launch With (v1)

Minimum viable product for validating the secure-agent concept:

- [ ] Local registration/login/logout/me with Argon2id and non-enumerating errors
- [ ] Strict short-lived access JWT validation and hashed rotating refresh-token families with replay detection
- [ ] Browser-safe session handling with no persistent JavaScript-readable refresh token
- [ ] User/Admin roles, required OAuth-style scopes, active-account checks, and explicit tool permissions
- [ ] Owner-constrained conversation/message CRUD with comprehensive two-user BOLA tests
- [ ] Durable chat history, safe Markdown/code rendering, clear loading/error state, and streaming only if persistence remains correct
- [ ] Configurable real OpenAI-compatible normal-chat adapter
- [ ] Deterministic coordinator with direct-chat, Google Search, and Python paths only
- [ ] Dedicated Gemini 2 ADK Google Search agent transporting citations and required Search Suggestions with terms-compliant retention and no source-link tracking
- [ ] Dedicated no-network Python sandbox worker with timeout, CPU, memory, PID, filesystem, capability, output, and cleanup controls
- [ ] Kong DB-less path-based routes with strict CORS, correlation IDs, request-size limits, and endpoint-specific rate limits
- [ ] FastAPI defense in depth for all authentication and authorization decisions
- [ ] Structured redacted JSON logs, audit records, security events, tool execution records, and minimal admin evidence APIs
- [ ] Automated functional tests plus BOLA, brute-force, token replay, SSRF, prompt/tool abuse, and sandbox attack simulations
- [ ] `docker compose up --build` startup and Vietnamese README/architecture/security/testing/runbook documentation

### Add After Validation (v1.x)

- [ ] Conversation search, archive, rename, and explicit retention controls — add after CRUD and pagination behavior are stable
- [ ] User session/device list with “revoke this session” and “revoke all sessions” — add after refresh-family semantics are proven
- [ ] Password reset and email verification — add when outbound email infrastructure can be implemented without mock security claims
- [ ] Adaptive Turnstile on login/register — add for a deployed Cloudflare demo; server-side Siteverify is mandatory
- [ ] Streaming cancel/resume refinements — add after proxy buffering, disconnect cleanup, and final-message persistence are reliable
- [ ] Per-user usage dashboard for messages, searches, sandbox runs, and denied actions — add after counters are trustworthy
- [ ] Exportable Vietnamese security evidence report — add after attack scripts produce stable machine-readable results
- [ ] Optional OpenTelemetry traces and Loki/Grafana profile — add when base JSON/correlation evidence is complete
- [ ] Key rotation runbook and multi-key JWT verification window — add before any persistent shared deployment

### Future Consideration (v2+)

- [ ] Real external OIDC/enterprise SSO — requires provider metadata, authorization code with PKCE, account linking, issuer mapping, and logout design
- [ ] MFA/WebAuthn and step-up authentication — valuable for admin/high-risk actions but not required to prove v1 boundaries
- [ ] Organization/team tenancy — requires a new relationship authorization model and cross-tenant test matrix
- [ ] Files, RAG, connectors, and long-term memory — require separate ingestion, retention, malware, privacy, and indirect-injection designs
- [ ] Conversation sharing/collaboration — requires explicit ACLs, revocation, link security, and data-copy semantics
- [ ] Additional tools or write actions — require per-tool threat models, user confirmation, idempotency, rollback, and least-privileged downstream identities
- [ ] Stronger sandbox technology such as gVisor, Kata Containers, or microVMs — evaluate before claiming hostile multi-tenant production isolation
- [ ] Billing/subscriptions and model routing optimization — outside the security-demonstration MVP

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Secure auth and token lifecycle | HIGH | HIGH | P1 |
| RBAC, scopes, tool permissions, active-user checks | HIGH | HIGH | P1 |
| Ownership/BOLA controls | HIGH | HIGH | P1 |
| Conversation and message history | HIGH | MEDIUM | P1 |
| Safe Markdown/code chat UX | HIGH | MEDIUM | P1 |
| Configurable normal-chat adapter | HIGH | MEDIUM | P1 |
| Deterministic agent coordinator | HIGH | HIGH | P1 |
| Google Search grounding and required UI | HIGH | HIGH | P1 |
| Hardened Python sandbox | HIGH | HIGH | P1 |
| Kong route controls and rate limits | HIGH | MEDIUM | P1 |
| Correlated logs/audit/security events | HIGH | HIGH | P1 |
| Security tests and attack simulations | HIGH | HIGH | P1 |
| Vietnamese operational/security docs | HIGH | MEDIUM | P1 |
| Minimal admin evidence APIs | MEDIUM | MEDIUM | P1 |
| Streaming responses | HIGH | HIGH | P2 |
| Security evidence center | HIGH | HIGH | P2 |
| Session/device management UI | MEDIUM | MEDIUM | P2 |
| Turnstile deployment profile | MEDIUM | MEDIUM | P2 |
| Usage/cost dashboard | MEDIUM | MEDIUM | P2 |
| OpenTelemetry/Loki/Grafana | MEDIUM | HIGH | P3 |
| External OIDC/SSO | MEDIUM | HIGH | P3 |
| MFA/WebAuthn | MEDIUM | HIGH | P3 |
| Multi-tenant organizations | MEDIUM | HIGH | P3 |
| RAG/files/connectors | MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have after core security behavior is proven
- P3: Future scope requiring separate design

## Competitor Feature Analysis

This comparison uses public user-facing documentation only. It does not infer undocumented internal security controls.

| Feature | ChatGPT Public UX | Gemini Apps Public UX | Our Approach |
|---------|-------------------|------------------------|--------------|
| Conversation persistence | Saved history, history search, archive, and delete controls are documented | Persistent chats and source-related interactions are part of the signed-in app experience | Ship durable owner-only history and deletion first; defer archive/search until v1.x |
| Web search | Search can run automatically or explicitly and provides inline citations plus a Sources panel | Responses may provide inline sources or a Sources panel and a Google double-check flow | Use an explicit scope-controlled Google Search path with structured inline citations and required Search Suggestions |
| Response retry | Search documentation describes retrying a response with web search | Consumer app supports follow-up and source inspection | Provide retry with preserved user input and explicit grounded/ungrounded state |
| Source transparency | Source links are visible to the user | Sources and related links are visible when available | Persist claim-to-source metadata; never label a response grounded when metadata is missing |
| Chat deletion | Deleted chats are removed from UI and documented with retention behavior | Product offers chat activity controls through Google account/app settings | Document prototype deletion and retention precisely; do not imply immediate physical erasure if audit/security retention applies |
| Tool execution visibility | Public UX exposes tool/search modes but not project-specific authorization evidence | Public UX exposes sources and connected app behavior | Show requested/running/denied/succeeded tool states plus a safe authorization receipt |
| Security-control evidence | Not evaluated from public consumer help pages | Not evaluated from public consumer help pages | Make BOLA, replay, rate-limit, prompt/tool abuse, and sandbox evidence a first-class evaluator feature |
| Local reproducibility | Hosted service | Hosted service | Entire required prototype path starts locally with Docker Compose; external credentials are needed only for real model/search calls |
| Vietnamese evaluator documentation | Product help localization exists, but not project-specific evidence | Product help localization exists, but not project-specific evidence | Deliver Vietnamese architecture, controls, attack tests, and incident runbooks tied to this implementation |

## Security Feature Acceptance Rules

These rules should be reused when turning features into roadmap requirements:

1. **Fail closed:** missing configuration, unknown role/scope/tool, malformed provider output, or unavailable policy data denies the sensitive action.
2. **Complete mediation:** authorization is checked on every request and again immediately before every tool execution.
3. **No security decision from model prose:** model output may request an action but cannot grant identity, role, scope, ownership, network access, or sandbox privilege.
4. **Negative test required:** every allow rule has at least one deny-path test using another user, missing scope, wrong role, revoked token, or disallowed input.
5. **Evidence required:** sensitive outcomes produce a redacted event with actor, action, object/tool, result, reason, timestamp, and correlation ID.
6. **No secret-bearing evidence:** tests and screenshots use synthetic values; logs never include password, raw JWT, refresh token, API key, cookie, database URL, or full environment dump.
7. **External content is untrusted:** search results and model responses cannot directly become executable HTML, authorization instructions, URLs to fetch, shell commands, or sandbox configuration.
8. **Bound every expensive operation:** request bytes, prompt size, model output, retries, wall time, tool calls, search calls, sandbox output, CPU, memory, PIDs, and concurrent jobs have explicit limits.
9. **Document actual behavior:** Vietnamese docs name assumptions and limitations and do not claim OIDC, tenant isolation, prompt-injection prevention, or production sandboxing beyond implemented evidence.

## Research Gaps and Phase Flags

- **ADK version behavior (MEDIUM confidence):** Google ADK and raw Gemini API documentation differ on supported models and tool combinations. Before implementation, pin ADK and Google Gen AI SDK versions and write a contract test that captures the actual event/grounding schema.
- **Google grounding retention and rendering (HIGH requirement):** Google's docs require display of returned Search Suggestions, while terms effective March 23, 2026 restrict caching/storage and link-level tracking. Treat grounding metadata as transient response data unless a specific retention allowance applies; verify `renderedContent`, CSP interaction, chat-history behavior, and no-click-tracking tests in the chosen frontend.
- **Kong JWT fit (HIGH confidence on limitation):** Kong's basic JWT plugin directly verifies only a limited set of registered claims such as `exp`/`nbf` and requires Consumer credentials. Prototype integration must be validated against custom local JWT issuance; do not force an awkward mapping if it weakens backend design.
- **Docker sandbox assurance (HIGH confidence on controls, MEDIUM on Windows-host behavior):** Linux container controls depend on the Docker Desktop/WSL2 runtime when developed on Windows. Record the effective runtime and skip no security test silently.
- **Browser auth architecture (MEDIUM confidence pending RFC publication):** the latest IETF browser-app guidance was approved but not yet published as an RFC when researched. Its BFF/token-mediation direction is strong, but implementation should cite the final RFC if published before the auth phase.
- **Retention semantics (project decision needed):** define whether deleting a conversation also deletes tool/audit summaries or retains redacted security evidence. The UI and Vietnamese docs must match.
- **Cloudflare source-IP trust (deployment-specific):** when Cloudflare is enabled, define exactly which proxy headers Kong trusts and prevent direct clients from spoofing them.

## Sources

### Identity and Authorization

- [RFC 9700: Best Current Practice for OAuth 2.0 Security](https://www.rfc-editor.org/rfc/rfc9700.html) — January 2025; refresh-token rotation/replay response, least privilege, audience restriction, PKCE, and deprecation of insecure grants. **HIGH confidence**
- [RFC 8725: JSON Web Token Best Current Practices](https://www.rfc-editor.org/rfc/rfc8725.html) — algorithm allowlisting, issuer/subject/audience validation, explicit typing, and SSRF risks from untrusted JWT URLs. **HIGH confidence**
- [OAuth 2.0 for Browser-Based Applications, draft-ietf-oauth-browser-based-apps-26](https://datatracker.ietf.org/doc/draft-ietf-oauth-browser-based-apps/) — IESG-approved BCP draft; BFF/token-mediating backend and browser token storage guidance. Awaiting final RFC publication when researched. **MEDIUM confidence**
- [NIST SP 800-63B-4: Authentication and Authenticator Management](https://pages.nist.gov/800-63-4/sp800-63b.html) — July 2025 final; password length/blocklist/composition guidance, secure hashing, rate limiting, and session timeouts. **HIGH confidence**
- [RFC 9106: Argon2 Memory-Hard Function](https://www.rfc-editor.org/rfc/rfc9106.html) — Argon2id recommendations. **HIGH confidence**
- [OWASP API1:2023 Broken Object Level Authorization](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/) — per-object authorization and negative testing. **HIGH confidence**
- [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html) — least privilege, deny by default, permission validation on every request, relationship-based controls, and authorization tests. **HIGH confidence**

### AI, Grounding, and Tool Security

- [Google ADK: Google Search tool](https://google.github.io/adk-docs/tools/gemini-api/google-search/) — Gemini 2 compatibility, required Search Suggestions display, and ADK single-tool warning. **HIGH confidence for documented ADK contract**
- [Google ADK: Tool limitations](https://google.github.io/adk-docs/tools/limitations/) — single built-in tool per agent and documented workarounds/caveats. **HIGH confidence for documented ADK contract**
- [Gemini API: Grounding with Google Search](https://ai.google.dev/gemini-api/docs/google-search) — grounding metadata fields, inline citation mapping, model support, tool combinations, and pricing semantics; last updated May 18, 2026. **HIGH confidence**
- [Gemini API Additional Terms: Grounding with Google Search](https://ai.google.dev/gemini-api/terms) — effective March 23, 2026; associated Search Suggestions, same-end-user display, retention limits, modification restrictions, and prohibition of link-level tracking. **HIGH confidence**
- [OWASP LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) — prompt injection is not fully preventable; constrain impact through privilege controls, separation of untrusted content, output validation, and adversarial tests. **HIGH confidence**
- [OWASP LLM06:2025 Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/) — minimize tools/functionality/permissions/autonomy, execute in user context, and enforce complete mediation outside the LLM. **HIGH confidence**
- [OWASP LLM10:2025 Unbounded Consumption](https://genai.owasp.org/llmrisk/llm102025-unbounded-consumption/) — input limits, quotas, timeouts, sandboxing, monitoring, and graceful degradation. **HIGH confidence**

### Sandbox, Gateway, and Evidence

- [Docker: Resource constraints](https://docs.docker.com/engine/containers/resource_constraints/) — containers have no resource constraints by default; explicit CPU and memory limits are required. **HIGH confidence**
- [Docker: Seccomp security profiles](https://docs.docker.com/engine/security/seccomp/) — default seccomp allowlist and recommendation not to disable it. **HIGH confidence**
- [Docker: None network driver](https://docs.docker.com/engine/network/drivers/none/) — `--network none` for network isolation. **HIGH confidence**
- [Docker: `docker container run`](https://docs.docker.com/reference/cli/docker/container/run) — capability dropping, read-only/resource options, and `no-new-privileges`. **HIGH confidence**
- [Docker: Rootless mode](https://docs.docker.com/engine/security/rootless/) — reducing daemon/runtime root privilege where environment supports it. **HIGH confidence**
- [Kong Gateway: Rate Limiting plugin](https://developer.konghq.com/plugins/rate-limiting/) — DB-less support, local/cluster/Redis strategies, client headers, and `429` behavior. **HIGH confidence**
- [Kong Gateway: JWT registered claims](https://developer.konghq.com/plugins/jwt/examples/verified-claim/) — basic plugin verification of `exp` and `nbf` and Consumer credential requirement. **HIGH confidence**
- [Kong Gateway: CORS plugin](https://developer.konghq.com/plugins/cors/) — approved-origin behavior and path/method route matching for browser preflight. **HIGH confidence**
- [Kong Gateway: Correlation ID plugin](https://developer.konghq.com/plugins/correlation-id/) — request/response correlation headers and JSON log integration. **HIGH confidence**
- [Kong Gateway: Request Size Limiting plugin](https://developer.konghq.com/plugins/request-size-limiting/) — request-body limits as DoS protection. **HIGH confidence**
- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) — auth/authorization/session/admin/security event coverage and data that must not be logged. **HIGH confidence**
- [OWASP ASVS 5.0](https://owasp.org/www-project-application-security-verification-standard/) — released May 30, 2025; current stable verification baseline and versioned requirement identifiers. **HIGH confidence**
- [OpenTelemetry Logs specification](https://opentelemetry.io/docs/specs/otel/logs/) — trace/span context for cross-component log correlation. **HIGH confidence**
- [NIST SP 800-218 SSDF 1.1](https://www.nist.gov/publications/secure-software-development-framework-ssdf-version-11-recommendations-mitigating-risk) — tracking security requirements, testing, provenance, and vulnerability response. **HIGH confidence**

### Edge and Product-Expectation References

- [Cloudflare Turnstile plans](https://developers.cloudflare.com/turnstile/plans/) — Free plan availability and standalone use; last updated April 16, 2026. **HIGH confidence**
- [Cloudflare Turnstile server-side validation](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/) — validation is mandatory; tokens are single-use and expire after five minutes. **HIGH confidence**
- [Cloudflare Bot Fight Mode](https://developers.cloudflare.com/bots/get-started/free/) — free domain-wide protection with limited customization and possible API/mobile challenges; last updated April 10, 2026. **HIGH confidence**
- [Cloudflare Tunnel](https://developers.cloudflare.com/tunnel/) — outbound-only origin connection and no public origin IP requirement; last updated May 5, 2026. **HIGH confidence**
- [OpenAI Help: Search chat history](https://help.openai.com/en/articles/10056348-how-do-i-search-my-chat-history-in-chatgpt) — current user expectation for discoverable durable chat history. **HIGH confidence**
- [OpenAI Help: ChatGPT Search](https://help.openai.com/en/articles/9237897-chatgpt-search) — search mode, automatic search, inline citations, and Sources panel. **HIGH confidence**
- [OpenAI Help: Delete and archive chats](https://help.openai.com/en/articles/8809935-how-to-delete-and-archive-chats-in-chatgpt/) — user controls and documented retention behavior. **HIGH confidence**
- [Gemini Apps Help: View sources and double-check responses](https://support.google.com/gemini/answer/14143489?hl=en) — source panel and response verification UX. **HIGH confidence**

---
*Feature research for: secure AI chatbot SaaS prototype with lightweight agent capabilities*
*Researched: 2026-06-08*
