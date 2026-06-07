# Pitfalls Research

**Domain:** Secure multi-user AI chatbot/API with FastAPI, Next.js, Google ADK tools, Kong, and Docker sandboxing
**Researched:** 2026-06-08
**Confidence:** HIGH

This report uses the six implementation phases defined in `prompt.md`:

1. Backend, data model, authentication, and core APIs
2. Frontend and browser token handling
3. LLM, ADK orchestration, web search, and Python sandbox
4. Authorization, application hardening, and security logging
5. Kong, Docker Compose, network boundaries, and deployment guidance
6. Automated verification, attack simulations, and final documentation

## Critical Pitfalls

### Pitfall 1: JWT Validation That Checks a Signature but Not the Token's Meaning

**What goes wrong:**
The API accepts a correctly signed token that was issued for another audience, another token purpose, another issuer, or another environment. An OpenID Connect ID token may be accepted as an API access token, an old signing algorithm may remain enabled, or Kong may accept a token that FastAPI interprets differently. A valid signature then becomes mistaken for complete authorization.

**Why it happens:**
JWT libraries make signature verification easy, while the required semantic checks are distributed across standards and application configuration. Developers often validate only `exp`, trust the token-supplied `alg`, omit `aud`, or use one decoder configuration for access tokens, ID tokens, password-reset tokens, and refresh artifacts.

**How to avoid:**
- Define one explicit access-token profile and reject all other JWT types at the API boundary.
- Pin an allowlist of signing algorithms in configuration; never derive the accepted algorithm from the token alone.
- Validate signature, exact `iss`, expected `aud`, token type such as `typ=at+jwt` or a private equivalent, `exp`, `nbf` when present, bounded `iat`, required `sub`, and required `jti`.
- Use mutually exclusive validation rules and keys or audiences for access tokens, ID tokens, reset tokens, and service tokens.
- Prefer asymmetric signing so Kong and FastAPI receive verification keys, not a shared signing secret.
- Treat claims as authenticated inputs, not authorization decisions. FastAPI must still enforce current endpoint policy, scopes, role, ownership, and account state.

**Warning signs:**
- Decoder calls use options such as `verify_aud=False`.
- The accepted algorithm is read from the JWT header.
- The same helper validates access, refresh, email-verification, and password-reset tokens.
- Tests prove only invalid signature and expiration behavior.
- Kong accepts a token, so backend claim validation is skipped.
- A browser OIDC `id_token` works in the API `Authorization` header.

**Verification evidence:**
- A negative token matrix showing rejection of wrong issuer, wrong audience, missing audience, wrong `typ`, `alg=none`, disallowed HMAC/RSA algorithm substitution, future `nbf`, expired `exp`, implausible future `iat`, missing `sub`, and missing `jti`.
- A test showing a valid ID token from the configured issuer is rejected as an API access token.
- Configuration evidence listing the exact accepted algorithm, issuer, audience, and token type.
- The same malformed-token corpus run against both Kong and direct FastAPI validation, with backend rejection required even where the gateway is less strict.

**Phase to address:**
Phase 1. Re-verify the final Kong/backend validation chain in Phases 5 and 6.

---

### Pitfall 2: Refresh Rotation That Is Replayable, Racy, or Impossible to Revoke Correctly

**What goes wrong:**
A stolen refresh token continues minting access tokens after logout, or two concurrent refresh requests both succeed. A naive rotation implementation deletes the old row and loses the token-family relationship needed to detect reuse. Conversely, normal retries or two browser tabs may trigger inconsistent behavior because rotation is not atomic.

**Why it happens:**
Refresh tokens are treated as long-lived JWTs rather than security-sensitive session records. Implementations commonly store raw tokens, update rows without a transaction or conditional lock, revoke only one token instead of its family, or test refresh sequentially when the real failure is concurrent.

**How to avoid:**
- Generate high-entropy opaque refresh tokens and store only a keyed hash or cryptographic hash suitable for lookup; never store or log the bearer value.
- Model a refresh-token family or grant with `family_id`, token identifier, parent identifier, creation/expiry, consumed/replaced time, and revocation reason.
- Rotate in one database transaction using row locking or a conditional update that permits exactly one transition from active to consumed.
- Retain the relationship to the replacement token. Reuse of a consumed token must revoke the active token family and create a security event.
- Revoke the family on logout, password reset/change, account disablement, or confirmed compromise.
- Use short access-token lifetimes so refresh-family revocation becomes effective quickly.
- Decide how duplicate client retries are handled. For this prototype, serialize refresh per session and fail closed rather than introducing a broad grace window that makes replay useful.

**Warning signs:**
- Refresh tokens are self-contained and there is no server-side grant/family state.
- The database stores the plaintext token.
- `revoked_at` exists, but there is no `consumed_at`, parent, replacement, or family concept.
- Two parallel calls using the same refresh token both return `200`.
- Logout revokes only the presented token while its replacement remains active.
- Replay detection logs an event but does not revoke descendants.

**Verification evidence:**
- A database-backed concurrency test sends the same refresh token in parallel and proves no more than one rotation commits.
- Reusing the consumed token revokes the entire family; the latest replacement then fails.
- Logout, password change, and account disablement invalidate the family.
- Database inspection confirms only token hashes are stored.
- Logs contain token identifiers or family identifiers but no bearer token values.

**Phase to address:**
Phase 1, with concurrency and replay attack simulations in Phase 6.

---

### Pitfall 3: OIDC-Ready Code That Confuses Authentication Tokens, Providers, and Subjects

**What goes wrong:**
The local-auth adapter appears replaceable but bakes in assumptions that break or weaken OIDC: ID tokens are sent to resource APIs, issuer validation is omitted, subjects collide across providers, discovery/JWKS locations are influenced by user input, or a token from one configured provider is replayed through another provider's callback.

**Why it happens:**
OAuth authorization, OIDC authentication, JWT encoding, and API authorization are often treated as one feature. A local `sub=user_id` token design may not account for the fact that an OIDC identity is identified by the issuer-subject pair. Multi-provider callback state and nonce binding are also easy to postpone because the first release uses passwords.

**How to avoid:**
- Define the identity adapter contract around a stable internal user ID plus external identity records keyed by exact `(issuer, subject)`.
- Keep ID-token validation separate from access-token validation. ID tokens authenticate the client session; access tokens authorize resource-server calls.
- For a future browser OIDC flow, require Authorization Code Flow with PKCE, exact redirect URI matching, `state`, `nonce`, exact issuer binding, and provider metadata loaded only from administrator-configured HTTPS issuers.
- Validate ID-token `iss`, `aud`, `azp` when applicable, signature, `exp`, and `nonce`.
- Do not accept arbitrary `jwks_uri`, `issuer`, or discovery URLs from a login request or token.
- Keep local credentials as one identity provider behind the same internal-user boundary rather than trying to make locally issued tokens look like third-party ID tokens.

**Warning signs:**
- One table column named `oidc_sub` has no issuer.
- The backend accepts either `id_token` or `access_token` in the same bearer-token dependency.
- Provider selection is recovered only from callback query parameters.
- Discovery is performed against a URL supplied by the browser.
- Tests decode claims but do not validate `state`, `nonce`, issuer, audience, or authorized party.

**Verification evidence:**
- A valid ID token is rejected by protected API endpoints.
- Tokens with the correct signature but wrong `aud`, `iss`, `nonce`, or `azp` are rejected in adapter tests.
- Two test providers may issue the same `sub` without mapping to the same internal identity.
- Callback tests prove provider/issuer binding cannot be switched after authorization starts.
- The adapter interface and schema preserve exact issuer-subject identity while returning a stable internal user ID.

**Phase to address:**
Phase 1. Document and test the external-provider contract again in Phase 6 even if hosted OIDC remains out of scope.

---

### Pitfall 4: BOLA Hidden Behind UUIDs, Nested Routes, or ORM Convenience

**What goes wrong:**
A user reads, deletes, or appends messages to another user's conversation by replacing a UUID. The top-level conversation endpoint may be protected while nested message endpoints, deletion paths, list filters, exports, or service-layer functions perform lookup by object ID alone.

**Why it happens:**
Unpredictable IDs are mistaken for authorization. Ownership checks are repeated ad hoc in route handlers, and later code paths call lower-level repository functions without the same guard. Parent-child relationships are especially error-prone: checking that a message belongs to a conversation is not enough unless the conversation belongs to the caller.

**How to avoid:**
- Make tenant/user ownership part of every repository query, such as selecting a conversation by both `conversation_id` and `user_id`.
- Resolve nested resources through the authorized parent.
- Centralize object authorization helpers, but keep the ownership predicate visible and testable at each data-access boundary.
- Use response schemas that cannot expose another tenant's metadata through joins or eager loading.
- Treat administrator access as a separate explicit policy, not an implicit bypass inside ordinary user queries.
- UUIDs are useful for reducing enumeration but must never replace access control.

**Warning signs:**
- Repository methods are named `get_by_id()` and callers are expected to remember a later owner check.
- A route compares a path `user_id` with token `sub`, but the requested object's actual owner is never loaded.
- Message creation checks only that the conversation exists.
- List endpoints filter by user, while get/delete endpoints do not.
- Security tests use one account or only nonexistent object IDs.

**Verification evidence:**
- A two-user matrix covers create, list, read, append message, list messages, update if present, and delete.
- Each test uses a real object owned by the other user and verifies both response denial and unchanged database state.
- Direct service/repository tests prove an object ID alone cannot retrieve tenant-owned data.
- SQL/query inspection or repository assertions show the owner predicate is applied in the database query.
- Error behavior does not reveal whether another user's object exists.

**Phase to address:**
Phase 1 for data-access design; Phase 4 for centralized policy review; Phase 6 for attack simulation.

---

### Pitfall 5: Scope, Role, and Tool-Permission Checks That Can Be Bypassed Through Another Entry Point

**What goes wrong:**
A normal user reaches an admin function by changing an HTTP method or calling a service directly. A user without `tool:python` cannot call `/api/tools/python` but can induce the agent to call the same executor. Authorization logic uses `role == admin OR scope present` when both were intended, trusts a client-supplied user ID, or accepts stale scopes from a long-lived token after permissions change.

**Why it happens:**
RBAC, OAuth scopes, ownership, and model tool selection are implemented by different modules. Route decorators create a false sense that internal calls are safe. Tool execution is sometimes treated as a model feature instead of a privileged server operation.

**How to avoid:**
- Define a deny-by-default authorization matrix for every endpoint and every tool execution.
- Require the intended combination explicitly: authentication, active account, role where applicable, required scope, object ownership, and tool allowlist.
- Enforce tool authorization immediately before execution in a deterministic coordinator. Do not rely only on the HTTP route or the model prompt.
- Derive actor identity and conversation ownership from the authenticated server context, never model output or request fields.
- Use the same policy service for direct tool endpoints and agent-initiated calls.
- Keep access tokens short-lived and define how role/scope changes take effect; perform authoritative account-state checks for high-risk operations.
- Ensure method variants and internal service calls cannot skip dependencies.

**Warning signs:**
- Authorization exists only as FastAPI route dependencies.
- Tool functions accept `user_id`, `role`, or `scopes` from model-generated arguments.
- The agent can import or call executor functions without a policy context.
- Admin endpoints check role but not admin scope, or scope but not role.
- Scope strings are substring matched rather than parsed as exact values.
- Unit tests call only public routes and never the coordinator/service boundary.

**Verification evidence:**
- A policy matrix test covers anonymous, user with no scope, user with one tool scope, admin missing admin scope, disabled user, and resource owner/non-owner.
- Direct coordinator tests prove model-generated calls cannot bypass missing scopes.
- HTTP verb and alternate-route tests cover GET/POST/PATCH/DELETE and nested endpoints.
- Audit evidence records denied tool attempts without executing the tool.
- A side-effect assertion proves denied requests create no tool job, process, database mutation, or provider call.

**Phase to address:**
Define the policy contract in Phase 1, enforce tool policy in Phase 3, and complete the cross-entry-point review in Phase 4.

---

### Pitfall 6: Rate Limits That Disappear Across Workers, Nodes, Identities, or Expensive Operations

**What goes wrong:**
Login or tool limits work in a single-container demo but multiply when Kong or FastAPI is scaled. IP-only limits punish users behind NAT and are bypassed by distributed clients. User-only limits do not protect unauthenticated login. A streaming chat request is counted once even though it holds a connection and spends model tokens for minutes. Local Kong counters diverge by node.

**Why it happens:**
Rate limiting is configured as one generic requests-per-minute plugin rather than a layered resource-control design. In Kong DB-less mode, the `local` policy is easy to configure, while shared `cluster` counters are unavailable; a Redis dependency is often omitted without documenting the resulting limit.

**How to avoid:**
- Apply endpoint-specific limits for registration, login, refresh, chat, web search, Python execution, and admin APIs.
- Use multiple keys as appropriate: trusted client IP for unauthenticated abuse, account/email hash for login, authenticated subject/consumer for normal APIs, and global concurrency/cost ceilings for LLM and sandbox work.
- In a multi-node deployment, use a shared Redis policy. Treat Kong `local` counters as a documented single-node prototype limitation.
- Strip and reconstruct forwarded identity headers at the trusted edge. Configure the exact Cloudflare/Kong proxy chain before trusting client IP.
- Add application-level concurrency, timeout, input-size, output-size, model-token, search-result, and sandbox-resource budgets; request-rate limits alone do not control cost.
- Decide fail-open/fail-closed behavior for limiter-store outages and test it.

**Warning signs:**
- Limits are keyed only by `X-Forwarded-For`.
- FastAPI uses a process-local dictionary or in-memory cache with multiple workers.
- Kong DB-less config uses `policy: local`, but documentation claims distributed enforcement.
- All routes share the same threshold.
- There is no limit on concurrent streams, model tokens, code output, or tool duration.
- A Redis outage silently removes or substantially weakens protection.

**Verification evidence:**
- Parallel tests show the exact threshold and `429` behavior for each sensitive endpoint.
- A two-node or two-worker test proves whether counters are shared. If the prototype intentionally stays single-node, the test and documentation explicitly demonstrate that limitation.
- Tests cover IP rotation plus one account, many accounts behind one IP, and authenticated per-user limits.
- LLM/tool tests prove concurrency, timeout, payload, output, and spending-budget controls independently of request count.
- Proxy tests show spoofed forwarding headers do not change the limiter identity.

**Phase to address:**
Phase 5 for Kong/shared-counter topology, with application resource budgets added in Phases 3 and 4 and verified in Phase 6.

---

### Pitfall 7: Treating Prompt Guardrails as the Tool Security Boundary

**What goes wrong:**
A direct prompt, malicious search result, or stored conversation message instructs the model to ignore policy, reveal hidden context, or call Python despite missing permission. The model may produce a syntactically valid tool call that reaches an executor because the application trusts the agent's decision. A refusal-looking response can hide that a forbidden tool already ran.

**Why it happens:**
System prompts are visible in the same reasoning environment as untrusted content and are probabilistic, while developers need deterministic authorization. Search content introduces indirect prompt injection. Tool schemas can also expose capabilities or parameters broader than the product intends.

**How to avoid:**
- Treat all model output as untrusted proposals.
- Put a deterministic policy-enforcing coordinator between the model and every tool.
- Expose only allowlisted, narrow tools with strict typed arguments. Do not expose arbitrary URL fetch, shell, file, package-install, Docker, or unknown API tools.
- Re-check authenticated identity, scope, ownership, per-tool budget, argument policy, and conversation binding immediately before execution.
- Separate instructions from untrusted search/tool content and clearly label external content as data, while recognizing that labeling does not eliminate injection.
- Never place API keys, refresh tokens, environment dumps, raw authorization headers, or unnecessary personal data in model context.
- Validate and safely render model/tool outputs. Do not execute generated code except through the dedicated sandbox.
- Record proposed, allowed, denied, started, and completed tool states so a textual refusal cannot conceal a side effect.

**Warning signs:**
- Security requirements are written mainly in the system prompt.
- Tool descriptions include “call any URL,” “run command,” or generic credential-bearing clients.
- The model supplies actor identity or scopes in tool arguments.
- Search results are appended to the system prompt without an untrusted-data boundary.
- Prompt-injection tests pass when the answer contains “I cannot,” without checking tool logs.
- Tool code is callable directly from the agent module without a policy object.

**Verification evidence:**
- Direct and indirect prompt-injection corpora attempt policy override, secret extraction, role impersonation, tool substitution, argument smuggling, and instructions embedded in search content.
- Tests assert zero forbidden side effects using tool-execution rows, sandbox jobs, outbound network capture, and provider mocks.
- Authorized tool calls still work, proving the test is not merely disabling all tools.
- Audit records link user, conversation, policy decision, sanitized input summary, status, and correlation ID.
- Fuzz/property tests reject unknown tool names and unexpected argument fields.

**Phase to address:**
Phase 3, with adversarial and side-effect verification in Phase 6.

---

### Pitfall 8: Violating Google ADK Tool-Composition Constraints

**What goes wrong:**
Google Search, built-in code execution, and custom Python tools are placed in one ADK agent even though specific built-in tools must be used alone. The design may fail at runtime, silently drop a tool, or be “fixed” with a version-specific bypass flag that is mistaken for a security control. Built-in Gemini code execution may also be confused with the project's separately hardened Python sandbox.

**Why it happens:**
ADK supports many tools generally, but has special composition restrictions for Google Search, code execution, and Vertex AI Search. Examples from older versions or other languages are copied without checking the current tool-limitations page.

**How to avoid:**
- Use a dedicated Google Search agent/worker and expose it to a coordinator through the supported `AgentTool` pattern or the currently documented Python workaround.
- Keep the custom Python sandbox as a separate application-controlled tool. Do not substitute Gemini built-in code execution for the required Docker-isolated worker.
- Make the application coordinator authoritative for tool selection and authorization; ADK composition is orchestration, not policy.
- Pin the ADK version, record the chosen workaround, and test upgrades against the official tool-limitations documentation.
- Fail startup when the configured model/tool combination is unsupported instead of degrading to an ungrounded or unrestricted path.

**Warning signs:**
- One `Agent` contains `google_search` plus a custom sandbox function.
- Google Search and a built-in code executor are attached to the same agent object.
- `bypass_multi_tools_limit=True` appears with no version pin, rationale, or integration test.
- The design calls Gemini code execution “the Docker sandbox.”
- Search is silently disabled when another tool is enabled.

**Verification evidence:**
- An integration test runs direct chat, authorized search, authorized Python, and denied tool calls through the real coordinator.
- ADK event traces show search is executed only by the dedicated search agent.
- Startup/configuration tests fail for unsupported combinations.
- Dependency lock evidence records the tested ADK version.
- Sandbox execution logs prove Python ran in the project worker, not Gemini built-in code execution or the backend process.

**Phase to address:**
Phase 3.

---

### Pitfall 9: Dropping or Misrepresenting Google Search Grounding Evidence

**What goes wrong:**
The backend stores only generated text and discards `groundingMetadata`, source chunks, support mappings, or `searchEntryPoint`. The frontend invents citations from a URL list, displays stale citations after rewriting the answer, or omits required Google Search suggestions. A response is labeled “grounded” when the provider returned no grounding metadata.

**Why it happens:**
Grounding data is treated as cosmetic UI metadata instead of part of the response contract. Chat schemas designed before search integration contain only `content`. Streaming and persistence make source-to-text offsets and vendor-provided rendered content easy to lose.

**How to avoid:**
- Preserve the provider's grounded response, `groundingChunks`, `groundingSupports`, search queries, and `searchEntryPoint`/`renderedContent` needed by the applicable Google terms.
- Store enough immutable metadata with the assistant message to reproduce citations after reload.
- Mark a result grounded only when grounding metadata is actually present; Google documents that some responses will not be grounded.
- Render support for claims using the returned support mappings rather than attaching every URL to the whole answer.
- When Google Search suggestions are returned, display them as required and keep them visible with the grounded response. Do not restyle or rewrite vendor-provided suggestion content contrary to the display requirements.
- Isolate vendor-provided rendered content from application secrets and use a restrictive content security policy. Do not concatenate model-generated HTML into it.
- Version the persisted metadata schema because provider fields can evolve.

**Warning signs:**
- The message table has `content` but no structured metadata contract.
- Search responses become plain text before reaching the API schema.
- The frontend creates `[1]`, `[2]` citations by URL order without `groundingSupports`.
- Search suggestion chips disappear after page reload.
- Every search answer is shown as grounded even when metadata is absent.
- Sanitization rewrites required Google suggestion markup or branding.

**Verification evidence:**
- Captured fixtures cover grounded and ungrounded responses.
- API and database evidence show source chunks, support mappings, and search-entry content survive persistence and reload.
- Frontend DOM/screenshot tests show inline or associated citations and required search suggestions for grounded responses.
- Citation tests verify each displayed marker maps to the returned chunk indices and supported text segment.
- Ungrounded responses are clearly represented without fabricated citations or suggestions.

**Phase to address:**
Phase 3, including the required frontend schema/rendering extension; verify persistence and UI behavior in Phase 6.

---

### Pitfall 10: SSRF Filters That Check the URL Once but Not the Connection

**What goes wrong:**
A tool accepts a hostname that initially resolves to a public address and later resolves to loopback, a private Docker address, link-local metadata, or IPv6 local space. Redirects can jump from an allowed public URL to an internal target. Alternate IP encodings, mixed IPv4/IPv6 results, credentials in URLs, or non-HTTP schemes bypass string blocklists.

**Why it happens:**
URL parsing, DNS resolution, redirects, and socket connection are separate operations. Developers validate the textual hostname but allow the HTTP library to resolve it again later. Blocklists usually omit IPv6, Docker subnets, and provider metadata addresses.

**How to avoid:**
- Do not add arbitrary URL-fetch capability to the agent unless required. Google Search should receive a query, not a user-controlled fetch URL.
- For any fetch-like integration, allow only `https`/`http` as explicitly needed, parse with a standard URL library, reject userinfo, and disallow nonstandard ports unless allowlisted.
- Resolve every A and AAAA result and reject loopback, private, link-local, multicast, unspecified, reserved/non-global, metadata, and internal Docker/network ranges.
- Bind validation to the actual connection target or use an egress proxy that resolves and enforces policy. Revalidate every redirect and set a small redirect limit; disabling redirects is safer where possible.
- Apply network-layer egress controls so an application bug still cannot reach PostgreSQL, Kong Admin API, Docker APIs, host services, or metadata endpoints.
- Keep the Python sandbox on `network_mode: none`.

**Warning signs:**
- Protection is a string list containing only `localhost`, `127.0.0.1`, and `169.254.169.254`.
- Only the first DNS answer is checked.
- Redirects are enabled by default with no per-hop validation.
- IPv6 addresses are not tested.
- The backend and sandbox share unrestricted Compose networks.
- A “web search” tool accepts arbitrary URLs or fetch instructions.

**Verification evidence:**
- Tests cover loopback, RFC1918, link-local, IPv6 loopback/private/link-local, unspecified addresses, Docker service names, internal container IPs, metadata targets, alternate numeric IP forms, URL userinfo, and disallowed schemes.
- A controlled redirect from public to private is blocked.
- A controlled DNS-rebinding test or egress-proxy test proves the connection cannot switch to a non-global address after validation.
- Network capture/firewall logs show no packet reaches blocked targets.
- `docker compose` inspection confirms the sandbox has no network and sensitive services are not exposed unnecessarily.

**Phase to address:**
Phase 3 for tool behavior and Phase 5 for egress/network topology; verify in Phase 6.

---

### Pitfall 11: Giving the Sandbox Docker-Socket or Host-Level Power

**What goes wrong:**
The backend or sandbox mounts `/var/run/docker.sock` to create per-job containers. Compromising the web API or escaping user code then grants effective root control of the host through the Docker API. Other dangerous configurations include `privileged: true`, host PID/network namespaces, host directory mounts, root user, writable root filesystem, excess capabilities, package installation, and unrestricted process creation.

**Why it happens:**
Creating a fresh container per execution appears more isolated, but controlling the rootful Docker daemon is itself a host-privileged operation. Compose defaults also favor convenience: shared networks, writable filesystems, and inherited capabilities.

**How to avoid:**
- For this prototype, use a pre-created, dedicated sandbox worker reached over a narrow internal API. Do not mount the Docker socket into the backend or sandbox.
- Execute user code only as an unprivileged child inside the already isolated worker, with OS-level timeout and process/resource limits in addition to container limits.
- Configure a non-root user, `cap_drop: [ALL]`, `security_opt: [no-new-privileges:true]`, read-only root filesystem, bounded writable `tmpfs`, `network_mode: none`, PID/memory/CPU limits, output limits, and the default or stricter seccomp/AppArmor/SELinux profile.
- Mount no host directories, credentials, source tree, or daemon sockets into the worker.
- Use a minimal pinned image with no compiler/package manager unless demonstrably required. Recreate or clean per-job temporary state.
- If per-job container creation later becomes mandatory, isolate the broker and daemon on a separate VM/host with a narrowly designed API; do not expose general Docker control to the application tier.

**Warning signs:**
- Compose contains `/var/run/docker.sock`.
- The worker uses `privileged`, `network_mode: host`, `pid: host`, or broad host mounts.
- User code runs as root or in the FastAPI process.
- Resource limits exist only in Python code, not at the container/OS boundary.
- Package installation is available to generated code.
- Escape tests merely search the source for forbidden imports.

**Verification evidence:**
- `docker inspect`/Compose evidence shows no Docker socket, no privileged mode, non-root user, all capabilities dropped, no-new-privileges, read-only root, isolated tmpfs, no network, and resource/PID limits.
- Runtime tests prove infinite loops time out, fork/process bombs are bounded, memory exhaustion is killed, output is truncated, filesystem writes are limited to temporary space, and network calls fail.
- Escape attempts cannot read host files, Compose secrets, backend environment, Docker API, PostgreSQL, or sibling service endpoints.
- Backend process inspection proves user code never executes in the API container.
- Cleanup tests show files and processes do not survive into the next job.

**Phase to address:**
Phase 3 for runner design and Phase 5 for final Compose hardening; verify from the running stack in Phase 6.

---

### Pitfall 12: Kong JWT Configuration That Conflicts With Standard Issuer Semantics

**What goes wrong:**
Kong's basic JWT plugin uses a configurable key-identifying claim whose default is `iss`. Teams then overload the standard issuer claim with a Kong credential ID, weakening normal issuer validation, or create a Kong Consumer per application user and duplicate the application's identity database. The plugin verifies a signature and optional `exp`/`nbf`, but the backend mistakenly assumes it also verified audience, token purpose, scopes, role, account state, ownership, or revocation.

**Why it happens:**
The plugin's “Consumer” and `key_claim_name` model is not the same as a general OIDC resource server. DB-less declarative configuration also makes dynamic end-user credential management and key rotation awkward. Gateway authentication is easily confused with complete application authorization.

**How to avoid:**
- Keep the standards-based `iss` value for the authorization server. Configure Kong's key lookup using a dedicated header/claim such as `kid` if compatible with the selected token profile and tested plugin version.
- Configure a static verifier credential/public key for the application's signing key rather than a Kong Consumer per end user.
- Enable `exp` and `nbf` verification and a bounded maximum expiration where supported, but retain full JWT validation in FastAPI.
- FastAPI remains authoritative for exact issuer, audience, token type, `iat`, `jti`, scope, role, account state, ownership, and refresh/revocation semantics.
- Prevent direct public access to FastAPI and strip/overwrite external `X-Consumer-*` or other trusted identity headers.
- Plan declarative key rotation with current/next public keys and tested configuration reload; do not replace a key without overlap.
- Keep Kong Admin API private and unexposed.

**Warning signs:**
- Access tokens put a random Kong credential ID in `iss`.
- There is one declarative Kong Consumer and secret per registered application user.
- Backend code trusts `X-Consumer-Username` as the application user without validating the token.
- `claims_to_verify` is empty.
- Documentation says “Kong validates JWT” as proof that scopes and audience are enforced.
- FastAPI is published directly on a host port, bypassing gateway controls.

**Verification evidence:**
- Architecture tests show invalid signatures and expired/not-yet-valid tokens fail at Kong.
- Wrong-audience, wrong-type, missing-scope, disabled-user, and cross-owner tokens fail at FastAPI even if Kong forwards them.
- Requests with spoofed `X-Consumer-*` headers cannot impersonate another user.
- Network tests show the backend is reachable only through the intended internal/gateway path.
- A key-rotation rehearsal proves old and new valid tokens overlap only for the planned window and unknown keys fail.
- Declarative configuration uses no raw private signing key where a public verification key is sufficient.

**Phase to address:**
Define the token contract in Phase 1 and implement the gateway architecture in Phase 5; run end-to-end bypass tests in Phase 6.

---

### Pitfall 13: Browser Token Storage That Trades XSS for CSRF Without a Complete Design

**What goes wrong:**
Access and refresh tokens are stored in `localStorage` or `sessionStorage`, allowing any successful XSS to steal them. Moving tokens into cookies without CSRF controls can make state-changing requests forgeable. Cookie domain/path scope may also expose a refresh token to unrelated applications or subdomains.

**Why it happens:**
Frontend tutorials favor local storage for convenience, while “use HttpOnly cookies” is applied without considering SameSite behavior, cross-origin deployment, refresh/logout CSRF, or the distinction between access and refresh tokens.

**How to avoid:**
- Prefer a same-origin Backend-for-Frontend or gateway pattern where the browser uses `HttpOnly; Secure; SameSite=Strict` or carefully justified `Lax` cookies.
- If the frontend calls the API with bearer access tokens, keep the access token in memory and put only the refresh/session artifact in an HttpOnly cookie with narrow path and host scope.
- Protect cookie-authenticated state-changing endpoints using SameSite plus explicit CSRF defenses where deployment/cross-origin behavior requires them.
- Never place tokens in URLs, client-readable persistent storage, page HTML, analytics, or service-worker caches.
- Set `Cache-Control: no-store` on authentication responses and sensitive user data.
- Document local HTTP development behavior separately from production HTTPS flags without weakening production defaults.

**Warning signs:**
- `localStorage.setItem("access_token", ...)` or refresh-token persistence in browser storage.
- JavaScript reads the refresh token to call `/refresh`.
- Cookies use a parent-domain scope or omit HttpOnly/Secure/SameSite.
- Refresh and logout accept cross-site requests without CSRF validation.
- Tokens appear in query parameters, Redux persistence, browser logs, or error monitoring.

**Verification evidence:**
- Browser inspection confirms no tokens in local/session storage, IndexedDB, URLs, or cached responses.
- JavaScript cannot read the refresh/session cookie.
- Cross-site refresh, logout, and other cookie-authenticated state changes fail under the deployed cookie/CSRF policy.
- An XSS test page cannot extract a persistent bearer token.
- Cookie flags, host/path scope, and `Cache-Control` headers are asserted in automated tests.

**Phase to address:**
Phase 2, with supporting auth-cookie and CSRF behavior defined in Phase 1 and browser security tests in Phase 6.

---

### Pitfall 14: Structured Logging That Becomes a Secret and Prompt Exfiltration Channel

**What goes wrong:**
Request middleware logs `Authorization`, cookies, login bodies, refresh tokens, model API keys, complete prompts, search results, generated code, stdout, or exception objects containing provider requests. Correlation IDs make incidents traceable but also make it easy to join sensitive data across logs. Log injection can forge JSON fields or terminal lines.

**Why it happens:**
Generic request/response logging is enabled before a data-classification policy exists. Debug logging from HTTP/LLM SDKs is left on. Redaction is implemented for top-level keys only and misses nested metadata, headers with different casing, serialized exceptions, and streamed payloads.

**How to avoid:**
- Use an allowlist logging schema for security events rather than dumping requests or model context.
- Log identifiers and bounded summaries: internal user ID, action, resource type/ID, tool name, status, duration, policy result, source IP under trusted-proxy rules, and correlation ID.
- Remove, mask, or keyed-hash session/token identifiers when correlation is needed. Never log passwords, bearer tokens, refresh tokens, cookies, API keys, database URLs, encryption keys, or raw secrets.
- Recursively redact known sensitive keys and authorization/cookie headers before serialization; sanitize control characters and enforce length limits.
- Keep prompt, search-query, code, output, and message logging off by default. Where demonstration evidence needs a summary, make it explicitly bounded and non-secret.
- Disable verbose provider/HTTP debug logs in normal operation and test error paths.
- Restrict log access and retention; audit access to admin log endpoints.

**Warning signs:**
- Middleware logs every request body and response body.
- Tool records persist full input/output under fields named “summary.”
- Exception logging serializes the full outbound provider request.
- Redaction tests cover only `password`.
- Authentication or model SDK debug mode is enabled in Compose.
- Admin log APIs return unbounded metadata to any admin role without scope filtering.

**Verification evidence:**
- Canary secrets are injected into passwords, access/refresh tokens, cookies, headers, prompts, code, search queries, provider errors, and nested JSON; a full log scan proves none appear.
- Logs still contain sufficient event identifiers to reconstruct denied BOLA, scope failure, token replay, rate limit, and tool execution timelines.
- Control-character payloads cannot create forged JSON events.
- Admin log endpoints enforce role, scope, pagination, and field minimization.
- Retention/access configuration and a documented redaction field list are included in the evidence.

**Phase to address:**
Phase 4, with leakage regression tests in Phase 6.

---

### Pitfall 15: Security Tests That Demonstrate a Script, Not a Security Property

**What goes wrong:**
Attack scripts print “PASS” after receiving any non-200 response, prompt-injection tests accept a refusal sentence while a tool ran, SSRF tests cover only `127.0.0.1`, sandbox tests mock the runner, replay tests use an already expired token, and rate-limit tests run against one process. SAST/DAST output is presented as proof of authorization or agent safety even though those controls require stateful, role-aware testing.

**Why it happens:**
University demonstrations reward visible scripts, but security properties need multiple layers of evidence and negative side-effect assertions. Tests are often written against mocks before the full Compose topology exists and never promoted to black-box system tests.

**How to avoid:**
- Derive tests from explicit control statements and OWASP ASVS/API/LLM risks, with preconditions, attack action, expected denial, and expected absence of side effects.
- Combine unit policy tests, integration tests with PostgreSQL/tool workers, and black-box tests through Kong against the real Compose stack.
- Use at least two users, multiple roles/scope sets, valid attacker-owned objects, and valid but unauthorized tokens.
- For prompt/tool tests, inspect tool logs, jobs, network calls, and database state rather than model wording.
- For sandbox tests, verify runtime behavior and container configuration from outside the sandbox.
- For rate limits, test concurrency and the actual node/worker topology.
- Make scripts return nonzero on failure, save machine-readable evidence, and include positive controls showing permitted behavior still works.
- Treat Semgrep, Snyk, Burp, AWVS, and scanners as complementary evidence, not substitutes for business-logic tests.

**Warning signs:**
- Tests assert only status code class, not response semantics or side effects.
- All external services, database calls, and tools are mocked in “security” tests.
- Security scripts always exit `0`.
- Attack payloads are single happy-path examples copied from a checklist.
- No test goes through Cloudflare assumptions/Kong/FastAPI/service/database boundaries.
- A screenshot of a model refusal is the only prompt-injection evidence.

**Verification evidence:**
- A traceability table maps each security requirement to unit, integration, black-box, configuration, and log evidence.
- Tests run through `docker compose up --build` and produce JUnit/JSON results with nonzero failure behavior.
- BOLA, scope, replay, SSRF, prompt/tool abuse, and sandbox tests assert both denial and absence of forbidden side effects.
- Positive controls prove authorized chat/search/Python/admin flows remain functional.
- Scanner findings are triaged and manually verified; known scanner coverage gaps are documented.
- Re-running a test against an intentionally weakened local control causes the test to fail, demonstrating that it detects the targeted property rather than incidental behavior.

**Phase to address:**
Phase 6, but testable acceptance criteria and evidence hooks must be designed in every earlier phase.

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| One JWT decoder for every token type | Less code | Cross-token confusion and unsafe future OIDC migration | Never |
| Stateless refresh JWTs with no token-family records | Simple schema | No reliable replay detection, rotation, or family revocation | Never for this project |
| `get_by_id()` followed by optional owner checks | Fast CRUD development | Recurrent BOLA across nested and new endpoints | Never for tenant-owned objects |
| Route-only authorization | Concise FastAPI code | Agent and service-layer bypasses | Never for tools/admin actions |
| Kong `local` rate counters | No Redis dependency | Limits multiply per node | Acceptable only for the documented single-node local prototype |
| System-prompt-only tool restrictions | Easy demo | Probabilistic policy bypass | Never |
| One ADK agent with every tool | Simple mental model | Unsupported composition and unclear policy boundary | Never when it violates current ADK constraints |
| Store only search answer text | Small message schema | Lost citations, suggestions, and compliance evidence | Never for grounded responses |
| URL string blocklist | Easy SSRF test | DNS, IPv6, redirect, and parser bypasses | Never where arbitrary fetching exists |
| Mount Docker socket for per-job containers | Easy dynamic isolation | Host-root compromise path | Never in the application/sandbox containers |
| Store browser tokens in local storage | Simple SPA auth | Persistent token theft after XSS | Never |
| Log complete request/tool bodies | Convenient debugging | Credential, prompt, user-data, and API-key leakage | Only in isolated local debugging with synthetic data, never as a committed default |
| Mock-only security tests | Fast CI | No evidence that deployment controls work | Acceptable only as one layer, never as final evidence |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Local auth to future OIDC | Make local JWTs imitate ID tokens | Keep an identity adapter with stable internal users and exact issuer-subject external identities |
| Next.js to FastAPI auth | Persist access/refresh tokens in browser storage | Use HttpOnly session/refresh cookies or a BFF; keep bearer access tokens in memory if needed |
| Kong JWT plugin | Use default `iss` as a Kong credential key and assume full OIDC validation | Preserve standards issuer semantics, use a dedicated key identifier, and retain complete FastAPI validation |
| Kong DB-less rate limiting | Select `cluster` or claim shared limits with `local` | Use Redis for shared counters; otherwise document and test single-node limits |
| Cloudflare/Kong proxy headers | Trust arbitrary `X-Forwarded-For` | Strip inbound forwarding headers and trust only the configured proxy chain |
| Google ADK tools | Attach Google Search and custom tools to one unsupported agent | Separate search worker/agent and policy coordinator using supported composition |
| Google Search grounding | Return plain text and a hand-built URL list | Preserve and render grounding chunks, support mappings, and required search suggestions |
| ADK versus Python sandbox | Use Gemini built-in code execution as the project sandbox | Keep project-owned Docker worker isolation and policy evidence |
| Backend to sandbox | Mount Docker socket or execute locally | Call a pre-created hardened worker over a narrow internal interface |
| HTTP client/URL fetch | Validate hostname once, then follow redirects | Bind resolution to connection policy and validate every redirect with egress enforcement |
| LLM/provider SDK logging | Enable debug logs in Compose | Keep SDK debug disabled and emit application-owned redacted events |
| Security scanners | Treat a clean scan as proof of business authorization | Add stateful multi-user, role, tool, and deployment-aware tests |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Database lookup of raw refresh tokens without an indexed hash/JTI | Slow refresh and revocation queries | Store indexed token hashes/JTIs and family identifiers | As token history grows |
| Synchronous security/audit writes on every streamed token | Chat latency and database contention | Log one bounded request/tool lifecycle event, batch noncritical telemetry | During concurrent streaming |
| Process-local rate limiting | Different limits per worker | Redis/shared limiter or explicit single-worker constraint | As soon as a second worker/node starts |
| Unbounded LLM streams and model context | Long-held connections and cost spikes | Token/context/output/time limits and cancellation | With a few abusive concurrent users |
| Unbounded tool output | Memory, database, and UI pressure | Truncate stdout/stderr/results and store bounded summaries | A single verbose/infinite program can trigger it |
| Per-job Docker creation through the main daemon | High latency plus privileged socket exposure | Pre-created worker for prototype; isolated broker/host if future per-job containers are required | Even at low scale, security risk is immediate |
| Persisting large raw grounding payloads without a schema | Message rows and frontend payloads grow unpredictably | Store required structured evidence with size/version limits | Repeated search-heavy conversations |
| Global IP rate limit behind shared NAT | Legitimate users receive `429` | Layer IP, account, subject, endpoint, and global budgets | Small office/university networks |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Trusting token claims because they are signed | Wrong audience/type or stale privilege accepted | Validate token semantics, then apply current server policy |
| Using UUIDs as BOLA protection | Cross-user data access remains possible | Query by object plus owner and test every object operation |
| Letting the model decide authorization | Prompt injection becomes privilege escalation | Deterministic policy enforcement at the executor boundary |
| Passing secrets into model/tool context | Prompt or tool output leaks credentials | Minimize context and use server-side provider clients |
| Assuming Google Search output is trustworthy | Indirect prompt injection and misinformation | Treat search as untrusted evidence and preserve source mappings |
| Exposing arbitrary fetch functionality | SSRF into host, Docker, database, or metadata services | Avoid the feature or enforce connection-bound URL and egress policy |
| Mounting Docker socket read-only | Docker API can still create privileged host mounts | Do not mount the socket |
| Trusting Kong consumer headers from the internet | Header spoofing and identity confusion | Isolate backend and strip/overwrite trusted headers |
| Logging request bodies for investigations | Secrets and private chat/code become a second breach target | Allowlist event fields and test recursive redaction |
| Equating scanner results with authorization assurance | BOLA/scope/tool bypass survives | Stateful manual and automated business-logic tests |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Rotation races sign users out unpredictably | Multiple tabs or retries cause session loss | Serialize refresh and return a clear re-authentication path on detected reuse |
| Every authorization failure returns a different object-existence signal | Attackers enumerate resources; users see inconsistent errors | Use consistent error behavior while logging the internal reason |
| Rate limits have no retry information | Users repeatedly retry expensive operations | Return safe `Retry-After`/limit metadata and explain tool-specific limits |
| Search citations disappear after reload | Users cannot verify grounded answers | Persist and render grounding metadata with the message |
| Grounded and ungrounded answers look identical | Users over-trust unsupported claims | Clearly distinguish responses with actual grounding evidence |
| Tool denial is presented as a model failure | Users do not know permission is missing | Return deterministic application-level permission messaging |
| Sandbox errors expose internals | Users see paths, image details, or stack traces | Return bounded status/stdout/stderr while keeping diagnostics in redacted logs |
| Cookie/session expiry causes silent chat loss | User message may be duplicated after re-login | Preserve unsent client state and use idempotency where practical |

## "Looks Done But Isn't" Checklist

- [ ] **JWT validation:** A signed and unexpired token is not enough; verify issuer, audience, type, algorithm, times, subject, and token ID.
- [ ] **Refresh rotation:** A new token is issued, but reuse detection, atomic concurrency, family revocation, and hashed storage are also proven.
- [ ] **OIDC readiness:** The adapter models issuer-subject identity and rejects ID tokens at resource APIs.
- [ ] **BOLA:** Every nested read/write/delete path is tested with a real object owned by another user.
- [ ] **Scopes:** Direct endpoints and model-initiated tools share the same deny-by-default policy.
- [ ] **Rate limiting:** Limits are tested across the real number of workers/nodes and include expensive-operation budgets.
- [ ] **Prompt injection:** Tests assert no forbidden side effect, not merely a refusal response.
- [ ] **ADK composition:** The selected version supports the search-worker/coordinator design.
- [ ] **Search grounding:** Metadata, citations, and required search suggestions survive persistence and reload.
- [ ] **SSRF:** Redirects, DNS rebinding, IPv6, Docker/internal networks, and metadata addresses are covered.
- [ ] **Sandbox:** No Docker socket, privileged mode, host mounts, host execution, or network path exists.
- [ ] **Kong JWT:** Gateway checks do not replace backend audience, scope, role, ownership, and account-state validation.
- [ ] **Token storage:** No bearer token is readable from persistent browser storage or leaked through CSRF-prone cookie design.
- [ ] **Logging:** Canary secrets are absent from normal, denial, provider-error, and tool-error logs.
- [ ] **Security evidence:** Tests run against the Compose stack, fail with nonzero exit status, and include positive controls.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| JWT/token-purpose confusion | HIGH | Rotate signing keys if needed, invalidate sessions, split validation profiles, add wrong-audience/type tests, review accepted tokens |
| Refresh-family replay flaw | HIGH | Revoke all refresh grants, force login, migrate to hashed family records, add atomic rotation and reuse detection |
| BOLA discovered after data exposure | HIGH | Disable affected endpoints, add owner predicates, audit access logs, notify according to policy, retest all object paths |
| Scope/tool-policy bypass | HIGH | Disable tools, revoke affected tokens, centralize policy at executor, inspect tool side effects, add direct coordinator tests |
| Non-shared rate limits | MEDIUM | Reduce worker count temporarily, deploy Redis/shared counters, add app concurrency budgets, document outage behavior |
| Prompt injection causing tool action | HIGH | Disable implicated tool, revoke credentials, inspect tool/audit logs, narrow tool schema and permissions, add attack fixture |
| ADK composition break after upgrade | MEDIUM | Pin last verified version, restore separated agents, add startup compatibility tests before upgrading |
| Lost grounding metadata | MEDIUM | Fix schemas, stop labeling responses grounded, preserve new metadata; historical citations may be unrecoverable |
| SSRF vulnerability | HIGH | Disable fetch path, block egress at network layer, rotate reachable credentials, inspect internal-service logs |
| Docker socket/sandbox host exposure | CRITICAL | Stop worker, isolate/rebuild host, rotate all host-accessible secrets, remove socket/mounts, redesign execution boundary |
| Kong issuer/key architecture error | HIGH | Block direct backend access, restore backend validation, migrate key claim without changing issuer semantics, rotate/reload keys |
| Browser token leakage | HIGH | Revoke token families, fix XSS/storage design, move to HttpOnly/BFF flow, review logs and telemetry for leaked values |
| Secret leakage in logs | HIGH | Restrict access, purge where feasible, rotate exposed secrets, deploy recursive redaction tests and retention controls |
| False-positive security test suite | MEDIUM | Freeze release claims, rewrite tests around properties and side effects, rerun against real Compose topology |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| JWT semantic/cross-token confusion | Phase 1 | Negative token corpus at backend and Kong chain |
| Refresh rotation/replay races | Phase 1 | Parallel refresh, family-reuse, logout/password-change tests |
| OIDC provider/token confusion | Phase 1 | Wrong issuer/audience/type/nonce/provider-binding tests |
| BOLA on conversations/messages | Phase 1 and Phase 4 | Two-user operation matrix plus unchanged database state |
| Scope/RBAC/tool bypass | Phase 3 and Phase 4 | Endpoint and direct coordinator policy matrix |
| Distributed and expensive-operation rate limits | Phase 5 | Multi-worker/node concurrency tests plus cost/resource ceilings |
| Prompt injection/tool-policy bypass | Phase 3 | Direct/indirect attack corpus with zero forbidden side effects |
| ADK tool composition failure | Phase 3 | Real ADK integration trace for chat/search/Python/denial |
| Grounding evidence/display loss | Phase 3 | Grounded/ungrounded fixtures, persistence, DOM/screenshot checks |
| SSRF/DNS rebinding | Phase 3 and Phase 5 | Redirect, rebinding, IPv4/IPv6, egress, and network-layout evidence |
| Docker socket/sandbox escape | Phase 3 and Phase 5 | `docker inspect`, resource attacks, host/sibling/network denial |
| Kong JWT architecture mistakes | Phase 5 | Gateway/backend split-validation and key-rotation rehearsal |
| Browser token storage/CSRF | Phase 2 | Storage inspection, cookie flags, cross-site request tests |
| Logging secret leakage | Phase 4 | Canary-secret scans across success and failure paths |
| Misleading security tests | Phase 6 | Traceability matrix, black-box Compose run, positive controls, nonzero failures |

## Roadmap Research Flags

- **Phase 1 requires deeper design before coding:** freeze the access-token profile, refresh-family state machine, identity adapter, and ownership-query conventions together. Retrofitting any of these is expensive.
- **Phase 2 requires one explicit browser session architecture:** choose BFF/HttpOnly cookie behavior before building token persistence.
- **Phase 3 is the highest research-risk phase:** validate the exact Google ADK version, search-agent composition, grounding response schema, and sandbox execution boundary with a thin vertical spike before broad implementation.
- **Phase 4 must review internal call paths, not only routes:** policy and logging controls need service/coordinator coverage.
- **Phase 5 must state the local-versus-distributed limit honestly:** Kong DB-less plus local counters is acceptable for a one-node prototype, not evidence of cluster-wide limiting.
- **Phase 6 must collect runtime evidence:** configuration files, scanner reports, and model refusal text are insufficient without side-effect and deployment-topology checks.

## Sources

All sources were accessed on 2026-06-08. Official standards, OWASP projects, and vendor documentation are treated as HIGH-confidence sources.

### Identity, JWT, and Sessions

- IETF RFC 9700, *Best Current Practice for OAuth 2.0 Security* - refresh replay detection, rotation, sender constraints, mix-up defenses, and reverse-proxy header integrity: https://www.rfc-editor.org/rfc/rfc9700
- IETF RFC 8725, *JSON Web Token Best Current Practices* - algorithm verification, issuer/audience validation, explicit typing, and mutually exclusive validation rules: https://www.rfc-editor.org/rfc/rfc8725
- IETF RFC 9068, *JWT Profile for OAuth 2.0 Access Tokens* - `at+jwt`, required claims, issuer/audience validation, and ID-token confusion prevention: https://www.rfc-editor.org/rfc/rfc9068
- OpenID Foundation, *OpenID Connect Core 1.0* - ID-token purpose and `iss`, `aud`, `azp`, `exp`, and `nonce` validation: https://openid.net/specs/openid-connect-core-1_0-18.html
- OWASP Session Management Cheat Sheet - browser storage warning, cookie/session protections, and session logging: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- OWASP HTML5 Security Cheat Sheet - do not store session identifiers in local storage: https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html

### API Authorization, Resource Controls, SSRF, and Logging

- OWASP API1:2023, *Broken Object Level Authorization*: https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/
- OWASP API4:2023, *Unrestricted Resource Consumption*: https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/
- OWASP API5:2023, *Broken Function Level Authorization*: https://owasp.org/API-Security/editions/2023/en/0xa5-broken-function-level-authorization/
- OWASP API7:2023, *Server Side Request Forgery*: https://owasp.org/API-Security/editions/2023/en/0xa7-server-side-request-forgery/
- OWASP SSRF Prevention Cheat Sheet - URL/DNS validation, DNS pinning, A/AAAA checks, and network-layer controls: https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html
- OWASP Logging Cheat Sheet - security event fields and data that must be excluded or masked: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html

### Generative AI and Google ADK

- OWASP LLM01:2025, *Prompt Injection* - direct/indirect injection, least privilege, segregating external content, and adversarial testing: https://genai.owasp.org/llmrisk/llm01-prompt-injection/
- OWASP Top 10 for Agentic Applications 2026 - agent goal hijacking, tool misuse, identity/privilege abuse, and related agentic risks: https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
- Google ADK, *Limitations for ADK tools* - one-tool restrictions and supported workarounds for Google Search/code execution/Vertex AI Search: https://google.github.io/adk-docs/tools/limitations/
- Google ADK, *Understanding Google Search Grounding* - grounding chunks/supports and presentation of citations/search suggestions: https://google.github.io/adk-docs/grounding/google_search_grounding/
- Google Cloud, *Grounding with Google Search* - grounded-result metadata and search-suggestion obligations: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/grounding/grounding-with-google-search
- Google Cloud, *Use Google Search suggestions* - required visibility, exact rendering behavior, and `renderedContent`: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/grounding/grounding-search-suggestions
- Google Cloud, *GroundingMetadata REST reference* - `groundingChunks`, `groundingSupports`, and `searchEntryPoint`: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/reference/rest/v1beta1/GroundingMetadata

### Kong and Docker

- Kong, *JWT plugin* - Consumer credential model, default `iss` key lookup, forwarded JWT, and optional `exp`/`nbf` verification: https://docs.konghq.com/hub/kong-inc/jwt/
- Kong, *JWT plugin configuration* - DB-less limitations, `key_claim_name`, `claims_to_verify`, and `maximum_expiration`: https://docs.konghq.com/hub/kong-inc/jwt/configuration/
- Kong, *Rate Limiting plugin* - local, cluster, and Redis counter behavior: https://developer.konghq.com/plugins/rate-limiting/
- Kong, *Plugin compatibility* - DB-less does not support the cluster rate-limit policy; use local or Redis: https://developer.konghq.com/plugins/compatibility/
- Docker, *Docker Engine security* - Docker daemon attack surface, host filesystem control, namespaces, cgroups, and hardening: https://docs.docker.com/engine/security/
- Docker, *Networking in Compose* - `network_mode: none`: https://docs.docker.com/compose/how-tos/networking/
- OWASP Docker Security Cheat Sheet - never expose/mount the Docker socket, non-root user, dropped capabilities, no-new-privileges, resource limits, and read-only filesystems: https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html

### Verification

- OWASP Application Security Verification Standard 5.0.0 - security requirements and normalized verification rigor: https://owasp.org/www-project-application-security-verification-standard/
- OWASP Web Security Testing Guide - combined white-box, gray-box, and black-box verification and authorization/API testing: https://owasp.org/www-project-web-security-testing-guide/latest/

---
*Pitfalls research for: Design a Secure Chatbot Application with Lightweight Agent Capabilities*
*Researched: 2026-06-08*
