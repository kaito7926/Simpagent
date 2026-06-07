# Architecture Research

**Domain:** Secure multi-provider chatbot SaaS with bounded agent tools
**Researched:** 2026-06-08
**Confidence:** HIGH

## Executive Recommendation

Build a modular FastAPI monolith as the policy and persistence authority, with two separately deployed tool services:

1. A Google ADK search agent that has Google credentials and only the built-in Google Search tool.
2. A trusted sandbox supervisor that creates one ephemeral, network-disabled container per Python execution.

The browser, LLMs, provider output, search results, and user Python are all untrusted. Kong performs edge-adjacent controls, but the FastAPI backend must repeat token validation and exclusively own RBAC, scopes, object ownership, refresh-token state, tool authorization, and audit decisions. PostgreSQL is reachable only from the backend. No end-user access token or refresh token crosses into a tool service.

This separation remains recommended even though current ADK Python versions have workarounds for older built-in-tool composition limitations. The reason is now primarily security, credential isolation, independent failure handling, and preservation of Google grounding metadata rather than framework necessity.

## Standard Architecture

### System Overview

```text
                               OPTIONAL DEPLOYED EDGE
                    +--------------------------------------+
                    | Cloudflare DNS/TLS/WAF/Turnstile     |
                    | Bot Fight Mode + Cloudflare Tunnel   |
                    +------------------+-------------------+
                                       |
                             Public trust boundary
                                       |
               +-----------------------v-----------------------+
               |                  INGRESS ZONE                  |
               |  +-------------+             +-------------+  |
Browser <------+->| Next.js UI  |             | Kong OSS    |  |
               |  | untrusted   |-- API ----->| DB-less     |  |
               |  +-------------+             +------+------+  |
               +-------------------------------------|----------+
                                                     |
                                           Gateway/app boundary
                                                     |
               +-------------------------------------v----------+
               |                APPLICATION ZONE                |
               |  +------------------------------------------+  |
               |  | FastAPI backend                         |  |
               |  | - identity and token service            |  |
               |  | - authorization policy                  |  |
               |  | - conversation/message service          |  |
               |  | - coordinator and provider adapters     |  |
               |  | - audit/security event service          |  |
               |  +------+----------------+------------------+  |
               +---------|----------------|---------------------+
                         |                |
               Data boundary        Tool capability boundary
                         |                |
             +-----------v----+     +-----v--------------------------+
             | PostgreSQL     |     | TOOL ZONE                      |
             | app data       |     | +-------------+ +------------+ |
             | auth state     |     | | Search      | | Sandbox    | |
             | audit records  |     | | agent       | | supervisor | |
             +----------------+     | | Google ADK  | +------+-----+ |
                                    | +------+------+        |       |
                                    +--------|---------------|-------+
                                             |               |
                                      Provider boundary  Host/runtime boundary
                                             |               |
                                  +----------v---+    +------v------------+
                                  | Gemini API  |    | Ephemeral Python  |
                                  | Google      |    | job container     |
                                  | Search      |    | network=none      |
                                  +--------------+    +-------------------+

FastAPI also has outbound-only access to the configured OpenAI-compatible
provider and, when enabled, Cloudflare Turnstile Siteverify.
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Next.js frontend | Authentication UI, conversation UI, Markdown/code rendering, citation rendering, Search Suggestions display | Next.js, TypeScript, Tailwind; access token in memory; refresh token in an HttpOnly cookie |
| Cloudflare edge, optional | Public TLS, origin hiding through Tunnel, coarse WAF/bot controls, Turnstile widget delivery | Cloudflare Free-plan-compatible configuration; never treated as the authorization authority |
| Kong Gateway | Public API route allowlist, request size limits, strict CORS, coarse rate limits, optional JWT signature/`exp`/`nbf` verification, correlation header | Kong OSS in DB-less mode with declarative `kong.yml` |
| FastAPI backend | Sole business-policy authority; token issuance and full validation; RBAC/scopes/ownership; persistence; coordination; provider calls; audit | Modular monolith with thin routers and explicit services |
| Chat coordinator | Selects direct chat, search, or Python path; enforces deterministic policy before and after any model proposal | Typed state machine, bounded to one tool invocation per turn in v1 |
| OpenAI-compatible adapter | Normal chat only; provider-neutral `/v1/chat/completions` contract | Async client with operator-configured base URL, model, key, timeout, retry limit |
| Google ADK search agent | Search-grounded answer generation and complete grounding metadata extraction | Separate Python service; ADK agent with only `google_search`; Google key scoped to this service |
| Sandbox supervisor | Validates internal job capability, starts fixed execution image, enforces limits, captures bounded output, destroys job | Trusted minimal service using Docker Engine API; never executes user code in its own process |
| Python job container | Executes one untrusted Python submission | Immutable image by digest, non-root, read-only root, `network=none`, tmpfs workspace, seccomp/cgroups |
| PostgreSQL | Users, token state, conversations, messages, grounding metadata, tool state, audit and security events | Separate migration and runtime roles; no published host port by default |
| Structured telemetry | Cross-component request/tool traceability without secret or content leakage | JSON to stdout with W3C trace context; optional OpenTelemetry/Loki later |

## Trust Boundaries

| Boundary | Data Crossing | Required Controls |
|----------|---------------|-------------------|
| Browser to edge/API | Credentials, access JWT, refresh cookie, chat content, tool requests | TLS, Turnstile on abuse-prone auth endpoints, strict CORS, CSRF protection for cookie-authenticated endpoints, input and body-size limits |
| Cloudflare to Kong | Forwarded client identity and public HTTP requests | Tunnel or authenticated origin path; configure trusted proxy ranges; never accept client IP headers from arbitrary peers |
| Kong to FastAPI | Authenticated and public API requests | Backend not host-published; full backend JWT validation; ignore identity headers as authorization evidence |
| FastAPI to PostgreSQL | Auth and user data, messages, audit records | Private internal network, least-privilege runtime role, parameterized ORM access, migrations under separate role |
| FastAPI to search agent | Search query and invocation metadata | Internal network, short-lived audience-bound capability token, strict request schema and size, no end-user bearer token |
| Search agent to Google | Search prompt, model request, grounding response | Search-only Google credential, timeout, provider request ID, minimum necessary context |
| FastAPI to sandbox supervisor | Code, resource profile, invocation ID | Separate capability audience/key, strict code/output limits, no arbitrary image/command/mount/network options |
| Supervisor to Python job | Raw untrusted code | Per-job container, no network, no secrets, no host mounts, no Docker socket, hard resource/time/output limits |
| Supervisor to Docker daemon | Fixed container-create/start/inspect/kill/remove operations | Treat as a high-risk host boundary; minimal supervisor; hardcoded image/profile; production should move this onto an isolated worker host |
| Provider output to frontend | Markdown, URLs, Google-provided HTML/CSS | Sanitize Markdown; validate links; render Search Suggestions outside the main DOM in a restricted sandboxed frame |

## Recommended Project Structure

```text
secure-chatbot-agent/
|-- frontend/
|   |-- app/                         # Routes and server/client boundaries
|   |-- components/chat/             # Messages, Markdown, code, citations
|   |-- components/auth/             # Login, register, Turnstile integration
|   |-- lib/api/                     # Kong-facing typed API client
|   `-- lib/security/                # Token memory store and safe rendering
|-- backend/
|   |-- app/
|   |   |-- api/                     # Thin FastAPI routers
|   |   |-- core/                    # Settings, startup, errors, request context
|   |   |-- security/                # JWT, refresh rotation, RBAC, scopes, CSRF
|   |   |-- authorization/           # Ownership and tool policy decisions
|   |   |-- models/                  # SQLAlchemy models
|   |   |-- schemas/                 # Pydantic transport contracts
|   |   |-- repositories/            # Owner-scoped persistence operations
|   |   |-- services/                # Auth, conversation, message, audit
|   |   |-- agent/
|   |   |   |-- coordinator.py       # Bounded state machine
|   |   |   |-- decisions.py         # Typed ToolDecision contracts
|   |   |   `-- policy.py            # Allowlist, scope, budget, timeout checks
|   |   |-- providers/
|   |   |   `-- openai_compatible.py # Normal-chat adapter
|   |   |-- tools/
|   |   |   |-- search_client.py     # Internal search RPC client
|   |   |   `-- sandbox_client.py    # Internal sandbox RPC client
|   |   |-- observability/            # JSON logs, trace propagation, redaction
|   |   `-- main.py
|   |-- alembic/
|   `-- tests/
|-- search-agent/
|   |-- app/
|   |   |-- agent.py                 # ADK search-only agent
|   |   |-- grounding.py             # Metadata-preserving adapter
|   |   |-- auth.py                  # Internal capability verification
|   |   `-- main.py                  # Internal-only HTTP service
|   `-- Dockerfile
|-- sandbox/
|   |-- supervisor/                  # Trusted Docker job controller
|   |-- runtime/                     # Minimal immutable Python image
|   |-- seccomp/                     # Optional stricter job profile
|   `-- tests/
|-- kong/
|   `-- kong.yml
|-- security-tests/
|-- docs/
|-- docker-compose.yml
`-- .env.example
```

### Structure Rationale

- **`backend/app/authorization/`:** Keeps authorization decisions out of routers, provider adapters, and prompts so every entry point can call the same fail-closed policy.
- **`backend/app/agent/`:** The coordinator is a backend policy component, not a free-running autonomous agent.
- **`search-agent/`:** Gives Google credentials, ADK dependencies, grounding behavior, and provider failures a separate deployment and trust boundary.
- **`sandbox/supervisor/` versus `sandbox/runtime/`:** Trusted orchestration code and untrusted execution must never share a process or image role.
- **`repositories/`:** Owner-scoped query methods make BOLA-resistant access the default, for example `get_for_owner(conversation_id, user_id)`.

## Architectural Patterns

### Pattern 1: Policy-Enforcing Coordinator

**What:** Treat model output as a proposal. The coordinator alone decides whether a tool may execute after checking the authenticated principal, required scope, object ownership, tool allowlist, input limits, budget, and current execution count.

**When to use:** Every message that may invoke search or Python.

**Trade-offs:** Less autonomous than an open-ended agent loop, but far easier to test, audit, bound, and explain for a security prototype.

```python
decision = planner.propose(message_context)  # Untrusted proposal

authorization.require_conversation_owner(principal, conversation)
policy.require_allowed_tool(decision.tool_name)
policy.require_scope(principal, decision.required_scope)
policy.require_within_limits(decision, max_tools=1)

execution = tool_log.accept(decision, principal, conversation)
result = await tool_router.execute(execution)
```

The planner must never receive password hashes, tokens, API keys, raw environment variables, unrelated audit data, or another user's messages.

### Pattern 2: Narrow Internal Capability Tokens

**What:** The backend signs a short-lived internal token for exactly one tool invocation. The token contains `aud`, `jti`, `tool`, `invocation_id`, `input_hash`, `limits_profile`, `iat`, and an expiry measured in seconds. Each worker receives only the verification key for its own audience.

**When to use:** Backend-to-search-agent and backend-to-sandbox-supervisor calls.

**Trade-offs:** Adds key management and replay tracking, but prevents forwarding broad user credentials and produces an auditable service contract.

```json
{
  "typ": "tool-capability+jwt",
  "aud": "sandbox-worker",
  "jti": "b973...",
  "tool": "python",
  "invocation_id": "01J...",
  "input_hash": "sha256:...",
  "limits_profile": "python-basic-v1",
  "iat": 1780862400,
  "exp": 1780862430
}
```

Workers reject wrong audience, type, signature, expiry, reused `jti`, mismatched input hash, unknown profile, and any request field that attempts to override the fixed execution policy.

### Pattern 3: Grounding as First-Class Message Data

**What:** Store Google-grounded answer text and grounding metadata atomically with the assistant message. Do not flatten metadata into Markdown and do not discard Search Suggestions.

**When to use:** Every final ADK event containing `grounding_metadata`.

**Trade-offs:** More schema and rendering work, but citations remain verifiable and Google Search display requirements can be met.

Recommended normalized envelope:

```json
{
  "answer_text": "Exact final text returned by the grounded response",
  "web_search_queries": ["..."],
  "search_entry_point_html": "<style>...</style><div>...</div>",
  "grounding_chunks": [
    {"uri": "https://...", "title": "..."}
  ],
  "grounding_supports": [
    {
      "start_index": 0,
      "end_index": 42,
      "chunk_indices": [0]
    }
  ],
  "provider_request_id": "...",
  "schema_version": 1
}
```

`groundingSupports` offsets refer to the returned answer text. Persist that exact text before Markdown transformations. If inline citations are inserted, process support offsets from the end of the text toward the beginning, as shown in Google's official example.

### Pattern 4: Transactional State Around Non-Transactional Providers

**What:** Persist intent before an external call, never hold a database transaction open while waiting for an LLM or tool, and finalize state in a new transaction.

**When to use:** Normal chat, search, Python, refresh rotation, and any streamed response.

**Trade-offs:** Requires explicit state values and reconciliation, but avoids long-held locks and makes failures observable.

Suggested message/tool states:

```text
accepted -> running -> succeeded
                    -> failed
                    -> timed_out
                    -> cancelled
```

Use a client-generated idempotency key with a unique constraint on `(user_id, conversation_id, client_message_id)`. A retry returns the existing result or state instead of purchasing a duplicate provider call.

### Pattern 5: Defense-in-Depth Identity Validation

**What:** Kong rejects obviously invalid protected requests, while FastAPI independently validates the access JWT and performs all semantic authorization.

**When to use:** Every protected API route.

**Trade-offs:** Duplicate cryptographic work is minor. It prevents accidental direct-backend exposure or incomplete gateway claim validation from becoming an authorization bypass.

Kong OSS JWT can verify signatures and optionally `exp` and `nbf`. It does not replace backend validation of `iss`, `aud`, `typ`, `sub`, role, scopes, `jti`, account status, revocation-sensitive conditions, or object ownership.

## Authentication and Token Flow

### Access and Refresh Token Design

- Access token: short-lived JWT, preferably RS256 for straightforward Kong OSS verification.
- Required claims: `iss`, `aud`, `sub`, `role`, `scopes`, `exp`, `iat`, `jti`, and explicit `typ=access+jwt`.
- Refresh token: opaque, high-entropy random value in an `HttpOnly`, `Secure` production cookie with a narrow path such as `/api/auth`.
- Persist only a cryptographic hash of the refresh token plus token family, `jti`, expiry, rotation/replacement, revocation, and reuse-detection fields.
- Keep the access token in browser memory. On page reload, obtain a new access token through the refresh endpoint.
- Cookie-authenticated refresh/logout operations require strict `Origin` validation and CSRF protection in addition to `SameSite`.

### Login

```text
Browser
  -> Kong public /api/auth/login route
  -> FastAPI validates schema and Turnstile token when enabled
  -> FastAPI verifies password hash and account state
  -> PostgreSQL records successful/failed authentication event
  <- FastAPI returns access JWT and sets opaque refresh cookie
  <- Kong returns response with security and correlation headers
```

Turnstile validation is backend work. Cloudflare states that client-side widget completion alone is insufficient; Siteverify is mandatory, tokens expire after five minutes, and tokens are single-use.

### Protected Request

```text
Browser Authorization: Bearer <access JWT>
  -> Kong verifies configured signature and exp/nbf on protected routes
  -> FastAPI verifies algorithm allowlist, signature, iss, aud, typ,
     exp/iat/nbf policy, sub, jti, account state, role and scopes
  -> Endpoint/service performs owner-scoped database query
  -> Response
```

For DB-less Kong, configure one Consumer/JWT credential for the application issuer, not one declarative Consumer per local user. Consequently, Kong's authenticated-Consumer rate limiting would aggregate users. Use gateway per-IP/per-route limits and backend per-user/tool limits keyed by validated `sub`.

### Refresh Rotation

```text
Browser refresh cookie
  -> FastAPI hashes presented token
  -> SELECT refresh row FOR UPDATE
  -> reject expired, revoked, replaced, reused, or wrong-family token
  -> revoke/replace current token and insert successor atomically
  <- new access JWT + new refresh cookie
```

If an already rotated refresh token is presented, revoke the entire family and emit a high-severity token replay security event. RFC 9700 requires public clients to use sender-constrained refresh tokens or refresh-token rotation; rotation is the practical prototype choice.

## Chat and Tool Data Flows

### Normal OpenAI-Compatible Chat

```text
POST conversation message
  -> authenticate + scope `chat:write`
  -> owner-scoped conversation lookup
  -> validate size and client idempotency key
  -> persist user message and pending assistant operation
  -> build minimal conversation context
  -> call fixed operator-configured OpenAI-compatible base URL
  -> validate and normalize response
  -> persist assistant message, model, usage, finish reason, request ID
  -> return JSON; add SSE later without changing persistence contracts
```

Use the Chat Completions shape for the compatibility adapter because it is broadly implemented by OpenAI-compatible providers. The provider base URL is configuration, never user input. Permit HTTPS, with an explicit local-development exception. Disable redirects and apply connect/read/write/total timeouts. Use bounded retries because SDK defaults can retry timeouts and 429/5xx responses, potentially increasing latency and cost.

Provider keys exist only in the backend environment. Logs may contain provider, model, latency, usage, status, and provider request ID, but not prompts, completion text, authorization headers, or keys.

### Google ADK Search

```text
Coordinator
  -> require owner + `tool:websearch` + allowlisted search decision
  -> create ToolExecution(accepted)
  -> sign search-agent capability
  -> send query, locale, invocation ID, trace context

Search agent
  -> verify capability and request limits
  -> invoke ADK agent with built-in Google Search only
  -> read final response event
  -> extract exact text + complete grounding metadata
  -> return typed SearchGroundingEnvelope

Backend
  -> validate envelope and maximum sizes
  -> persist assistant message + grounding row + succeeded execution
  -> return answer and grounding payload to frontend
```

The search agent receives only the minimum query/context needed for search. It does not receive the user's bearer token, refresh token, password, full environment, Python code, database credentials, or unrestricted conversation history.

Current Google documentation says grounded responses can include:

- `webSearchQueries`
- `searchEntryPoint.renderedContent`
- `groundingChunks`
- `groundingSupports`

When Search Suggestions are returned, Google requires them to be displayed. Preserve `renderedContent` unchanged in persistence and transport. Render it in a sandboxed iframe or equivalent isolated document with no scripts, forms, same-origin privilege, or access to application state. Never inject it with `dangerouslySetInnerHTML` into the authenticated application's main DOM.

### June 2026 Gemini 2 Availability Gate

Do not hardcode a Gemini 2 model identifier into the coordinator contract. As of June 8, 2026, Google's official deprecation page lists:

- Gemini 2.0 Flash with an earliest shutdown in February 2026.
- `gemini-2.5-flash` with an earliest shutdown in June 2026.
- `gemini-2.5-flash-lite` with an earliest shutdown in July 2026.

The current Google Search documentation examples already use a newer model family. Therefore:

1. Keep `GOOGLE_SEARCH_MODEL` as required deployment configuration.
2. Run a startup or deployment smoke test proving the configured model accepts the Google Search tool and returns grounding metadata.
3. For a strict university demonstration of "Gemini 2," use `gemini-2.5-flash` only if that smoke test succeeds on the demonstration date.
4. Keep the search-agent response contract model-neutral so a provider-mandated model replacement does not change backend persistence, authorization, or frontend grounding behavior.

Google's March 23, 2026 terms also state that prompts and responses submitted through unpaid services may be used to improve products and may be human-reviewed, and direct developers not to submit sensitive, confidential, or personal information to unpaid services. Use paid service credentials for any deployed real-user data, or constrain the university demo to non-sensitive test content and document the limitation.

### Python Sandbox

```text
Coordinator
  -> require owner + `tool:python`
  -> validate code length/language/profile
  -> create ToolExecution(accepted)
  -> sign sandbox-worker capability
  -> send code + fixed profile name

Trusted supervisor
  -> verify capability, nonce, hash and profile
  -> create ephemeral container from pinned local image digest
  -> stream code through stdin
  -> wait with hard wall-clock timeout
  -> cap stdout/stderr, inspect exit/OOM status
  -> kill and remove container in finally block
  -> return normalized result

Untrusted job container
  -> non-root UID
  -> network=none
  -> read-only root filesystem
  -> writable size-limited tmpfs only
  -> cap_drop=ALL
  -> no-new-privileges
  -> default or stricter seccomp profile
  -> CPU, memory, PID, file and output limits
  -> no devices, host mounts, secrets, package manager or Docker socket
```

The supervisor API accepts neither a command array nor image, mount, device, capability, environment, network, or Docker option from the caller. Those are hardcoded by the named policy profile.

Mounting the Docker socket gives the trusted supervisor host-equivalent power if compromised. Restrict the socket to this one minimal service, never expose the supervisor publicly, never run user code in it, and document that a production design would place execution on a separate worker host or stronger microVM/runtime boundary.

## PostgreSQL Persistence

### Recommended Ownership Model

| Table | Important Ownership/Integrity Rules |
|-------|-------------------------------------|
| `users` | Unique normalized email; role and scopes validated against controlled enums/sets |
| `refresh_tokens` | Hash only; unique `jti`; family/replacement chain; expiry and revocation indexes |
| `conversations` | Mandatory `user_id`; all normal queries include both conversation ID and owner ID |
| `messages` | Foreign key to conversation; immutable role/content after finalization; explicit status |
| `message_grounding` | One-to-one with grounded assistant message; exact answer metadata schema version |
| `tool_executions` | User, conversation, tool, state, duration, limits profile, safe summaries, provider request ID |
| `audit_logs` | Append-only security/business actions; no secrets or raw tokens |
| `security_events` | Append-only event type, severity, actor if known, network metadata, correlation/trace IDs |

Use UUIDv7/ULID-style sortable application IDs or PostgreSQL-generated UUIDs consistently. Use `timestamptz` in UTC. Index owner-scoped access paths such as `(user_id, updated_at desc)` and `(conversation_id, created_at, id)`.

Grounding data deserves a dedicated table rather than an opaque catch-all message blob because the frontend and compliance behavior depend on it. JSONB is appropriate for provider-shaped arrays, but retain explicit columns for `message_id`, schema version, and Search Suggestion HTML.

### Database Roles

- `app_migrator`: owns schema and runs Alembic; unavailable to the running API.
- `app_runtime`: CRUD only on required tables/sequences; cannot alter schema or create extensions.
- Optional `app_audit_writer`: insert-only for append-only audit/security tables.
- PostgreSQL is attached only to the private data network and has no default host port.

Application-level owner checks are mandatory. PostgreSQL Row-Level Security may be added as defense in depth after core owner-scoped repository tests are stable. If used, the runtime role must not own the table or have `BYPASSRLS`, `FORCE ROW LEVEL SECURITY` should be considered, and request identity must be set transaction-locally to avoid pooled-connection identity leakage.

### Transaction Rules

1. Never hold a database transaction open during an LLM, Google, Turnstile, or sandbox call.
2. Use a transaction for refresh-token rotation and family reuse detection.
3. Persist an accepted operation before outbound work; finalize in another transaction.
4. Use unique idempotency keys for user message submission and tool invocation.
5. Store failure class and safe provider request ID, not secret-bearing exception dumps.

## Gateway Versus Backend Controls

| Control | Cloudflare | Kong | FastAPI Backend |
|---------|------------|------|-----------------|
| Public TLS and origin hiding | Primary when deployed | TLS-ready origin; may terminate locally | Trust proxy headers only from known upstreams |
| DDoS/bot mitigation | Coarse edge controls | Coarse route rate limits | Per-account abuse state and lockout decisions |
| Turnstile widget | Delivers challenge | Passes token | Mandatory Siteverify validation and result decision |
| Route exposure | Host/path edge rules | Canonical API route/method allowlist | Endpoint definitions and authorization |
| CORS | Not authority | Canonical strict allowlist; path-based routes support preflight | Same allowlist as defense in depth; backend remains private |
| Request body limits | Optional edge rule | Request Size Limiting plugin | Schema-specific length/count limits |
| JWT signature check | No | Protected-route precheck | Mandatory full JWT and principal validation |
| Role/scope enforcement | No | Do not depend on OSS JWT for this | Sole authority |
| Object ownership/BOLA | No | No | Sole authority using owner-scoped queries |
| Refresh rotation/revocation | No | No | Sole authority with PostgreSQL state |
| Tool allowlist and permission | No | Coarse tool-route rate limit only | Sole authority |
| Prompt/tool-injection handling | No | No | Coordinator treats model output as untrusted |
| Per-user quotas/cost budget | No | Not reliable with issuer-level Consumer | Backend keyed by validated user/tool |
| Security headers | May add edge headers | Add consistent API headers | UI CSP primarily from Next.js; API fallback headers |
| Correlation/trace | Capture `CF-Ray` | Generate/echo edge correlation ID | Validate/generate trusted request ID and W3C trace; propagate internally |
| Audit event semantics | Edge event visibility | Access metadata | Sole authority for actor/action/resource/outcome |

Do not put business authorization in Kong declarative configuration. It cannot safely evaluate conversation ownership, refresh-token state, tool budget, or the current database account state.

### Kong-Specific Notes

- Use DB-less declarative configuration as the single source of gateway state.
- Keep the Admin API unexposed or bound to loopback for local debugging.
- Attach rate limits per route: strict on login/register/refresh and tools, moderate on chat, relaxed on health.
- For one local Kong node, `local` rate-limit counters are acceptable for a prototype. They are not globally accurate when Kong scales; use Redis if multiple nodes are introduced.
- Configure CORS on path/method-matched routes, not host-only routes, because browser preflight matching can fail for host-only routing.
- Enable request size limits on all API services/routes.
- If using Kong Correlation ID, remember it preserves a client-supplied header. Treat that value as untrusted metadata; the backend should generate a trusted ID when the value is absent or invalid.

## Docker Compose Networking

### Recommended Networks

| Network | Members | External Connectivity | Purpose |
|---------|---------|-----------------------|---------|
| `edge_rpc` | `cloudflared` optional, `frontend`, `kong` | `internal: true`; ingress members get separate egress where needed | Edge-to-local service routing |
| `app_rpc` | `kong`, `backend` | `internal: true` | Only Kong can reach backend HTTP |
| `data_rpc` | `backend`, `postgres` | `internal: true` | Database isolation |
| `search_rpc` | `backend`, `search-agent` | `internal: true` | Search service RPC only |
| `sandbox_rpc` | `backend`, `sandbox-worker` | `internal: true` | Sandbox supervisor RPC only |
| `backend_egress` | `backend` | Yes | OpenAI-compatible provider and Turnstile Siteverify |
| `search_egress` | `search-agent` | Yes | Gemini/Google Search only |
| `cloudflare_egress` | `cloudflared` optional | Yes | Outbound Cloudflare Tunnel connections |

Services on separate bridge networks cannot communicate unless a service deliberately joins both. `postgres`, `search-agent`, and `sandbox-worker` must not join `app_rpc` or `edge_rpc`. The sandbox job container joins no network at all.

Only these local-development ports should be published:

- Frontend UI, for example `127.0.0.1:3000:3000`
- Kong proxy, for example `127.0.0.1:8000:8000`
- Optional Kong Admin API on loopback only during debugging

Do not publish backend, PostgreSQL, search-agent, or sandbox-worker ports. Docker warns that omitting a host IP binds published ports to all interfaces; specify `127.0.0.1` for local-only services.

Use service DNS names, never container IPs. Compose recreates containers with new IPs while service names remain stable. Add health checks and `depends_on: condition: service_healthy` for startup ordering, but retain runtime retry/reconnect logic because startup order is not availability.

## Structured Logging and Audit

### Log Record

Every service emits one JSON object per event to stdout:

```json
{
  "timestamp": "2026-06-08T03:00:00.000Z",
  "level": "INFO",
  "event": "tool.execution.completed",
  "service": "backend",
  "environment": "local",
  "request_id": "trusted-server-id",
  "edge_request_id": "kong-or-cf-id",
  "trace_id": "32-lowercase-hex",
  "span_id": "16-lowercase-hex",
  "user_id": "uuid",
  "conversation_id": "uuid",
  "tool_execution_id": "uuid",
  "tool_name": "web_search",
  "outcome": "succeeded",
  "duration_ms": 842,
  "provider_request_id": "provider-id"
}
```

Use W3C `traceparent` across backend, search-agent, and sandbox-worker. OpenTelemetry's stable logs data model supports `TraceId` and `SpanId` correlation, but an OpenTelemetry Collector is optional for the prototype.

### Never Log

- Authorization or cookie headers
- Access, refresh, Turnstile, or internal capability tokens
- Passwords or password hashes
- API keys, connection strings, private keys, or full environment dumps
- Raw prompts, full message content, Python source, stdout/stderr, or Google `renderedContent`
- URL query strings when they may contain user content or tokens

For search and tool auditing, store a redacted/truncated summary, input byte count, result count, and stable hash. Full user content already belongs in the protected message/tool persistence path, not general logs.

Audit records answer who did what to which resource with what outcome. Operational logs answer how the request behaved. Do not use ordinary application logs as the only audit trail.

## Cloudflare Placement

Cloudflare is optional and must not be required for `docker compose up --build`.

Recommended deployed flow:

```text
Browser -> Cloudflare -> cloudflared outbound tunnel -> frontend or Kong
```

Cloudflare Tunnel is available on all plans and uses outbound-only origin connections, avoiding a public origin IP. For the Free plan, current Cloudflare documentation lists five WAF custom rules and Bot Fight Mode as free, but Bot Fight Mode applies to the entire domain and cannot be bypassed or customized with WAF custom rules. It may challenge API traffic, so test it before enabling it on an API hostname.

Use the limited WAF rules for high-value coarse conditions, not application semantics:

1. Block obviously invalid methods/paths outside the public route allowlist.
2. Challenge suspicious login/register traffic.
3. Block direct access to administrative/scanner paths not used by the app.
4. Apply conservative known-bad client conditions.
5. Reserve one rule for incident response.

Turnstile belongs on registration and login UI, but the backend Siteverify call decides acceptance. Cloudflare-provided IP headers are trusted only when the request demonstrably came through Cloudflare/Tunnel.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Prototype to 1k users | Single backend, Kong node, search agent, sandbox supervisor, and PostgreSQL; synchronous bounded tools; local Kong rate limits |
| 1k to 100k users | PostgreSQL connection pooler, async job queue for tools, separate worker hosts, Redis-backed distributed rate limits, partition/retention strategy for audit data |
| 100k+ users | Multi-node gateway/backend, dedicated identity provider, isolated sandbox fleet or microVMs, provider quota service, centralized telemetry, regional data architecture |

### Scaling Priorities

1. **First bottleneck:** External provider latency/quota. Add timeouts, admission limits, per-user budgets, and queued tool execution before splitting the core backend.
2. **Second bottleneck:** Sandbox concurrency and host contention. Move the supervisor and jobs onto isolated worker hosts with a bounded queue.
3. **Third bottleneck:** Audit/tool log growth. Add retention, archival, and partitioning without moving conversations out of PostgreSQL prematurely.

The modular monolith should remain until independent scaling or failure isolation is demonstrated. Search and sandbox are already separate because their credentials and execution risks justify the boundary.

## Dependency-Aware Suggested Build Order

1. **Contracts and threat model**
   - Define principals, scopes, roles, tool names, message/tool states, provider envelopes, redaction rules, and trust boundaries.
   - This prevents later providers and UI code from inventing incompatible security semantics.

2. **Compose and network skeleton**
   - Create named networks, internal-only service ports, health checks, non-root images, and secret/config injection.
   - Validate that backend, database, search, and sandbox endpoints are unreachable from the host.

3. **PostgreSQL schema and transaction primitives**
   - Add migration/runtime roles, users, refresh-token family state, conversations, messages, grounding, tool execution, audit, and security events.
   - Add ownership and idempotency indexes before APIs depend on them.

4. **Backend request context and observability**
   - Implement trusted request ID, W3C trace propagation, JSON logging, redaction, safe errors, and audit writer.
   - Security tests need evidence from the beginning.

5. **Authentication and token lifecycle**
   - Password hashing, login/register, access JWT, opaque refresh rotation, logout, replay-family revocation, CSRF/Origin checks, optional Turnstile adapter.

6. **Authorization and owner-scoped CRUD**
   - RBAC, scopes, active-account checks, conversation/message ownership, admin boundaries, and negative BOLA tests.
   - Do this before adding any costly or dangerous tool.

7. **Normal chat adapter**
   - Add the OpenAI-compatible interface, explicit timeouts/retries, idempotent message flow, provider request IDs, and non-streaming response first.

8. **Coordinator and internal tool contracts**
   - Add typed decisions, deterministic policy, execution state machine, capability signing, and mock search/sandbox clients.

9. **Google ADK search agent**
   - Implement search-only ADK service, final-event extraction, complete grounding envelope, persistence, citation tests, and Search Suggestions rendering contract.

10. **Sandbox supervisor and runtime**
    - Implement the fixed job profile and ephemeral `network=none` execution only after scope checks, capability auth, audit, and tool states exist.
    - Prove timeout, memory, PID, network, filesystem, output, and cleanup controls with automated tests.

11. **Kong declarative gateway**
    - Add path/method routes, request size limits, CORS, route-specific rate limits, correlation ID, and optional issuer-level JWT verification.
    - Verify the backend still rejects invalid or unauthorized requests when called directly from its private network.

12. **Frontend integration**
    - Add in-memory access-token handling, refresh-cookie flow, safe Markdown/code rendering, grounded citations, isolated Search Suggestions, and admin UI boundaries.

13. **Optional Cloudflare edge and final security evidence**
    - Add Tunnel/WAF/Turnstile/Bot Fight deployment notes, then run attack simulations and produce evidence from gateway, backend, database, search, and sandbox boundaries.

This order deliberately places identity, ownership, audit, and bounded execution contracts before real provider and sandbox access.

## Anti-Patterns

### Anti-Pattern 1: Model-as-Authorization-Engine

**What people do:** Put scopes and policies in a system prompt and trust the model not to call a forbidden tool.

**Why it is wrong:** Prompts are data, model output is probabilistic, and prompt injection can alter decisions.

**Do this instead:** Let the model propose a typed action; deterministic backend policy authorizes or rejects it.

### Anti-Pattern 2: One Agent with Every Credential and Tool

**What people do:** Give one process OpenAI, Google, database, and Docker access.

**Why it is wrong:** Any prompt/tool exploit gains the union of all privileges, and provider-specific response metadata becomes difficult to preserve.

**Do this instead:** Backend coordinator, search-only service, and sandbox supervisor each receive only their required credentials and network access.

### Anti-Pattern 3: User Code in the Networked Worker Process

**What people do:** Run `subprocess` inside the same long-lived container that exposes the worker HTTP API.

**Why it is wrong:** User code inherits the worker's network namespace, filesystem view, environment, service token, and process privileges.

**Do this instead:** The networked supervisor is trusted and never imports/executes user code; each submission runs in a separate `network=none` container.

### Anti-Pattern 4: Gateway-Only Authorization

**What people do:** Assume a JWT accepted by Kong is fully authorized.

**Why it is wrong:** Kong OSS JWT verification does not know object ownership, refresh-token state, current account status, tool policy, or all application claims.

**Do this instead:** Repeat full JWT validation and perform semantic authorization in FastAPI.

### Anti-Pattern 5: Grounding Flattened into Markdown

**What people do:** Append source URLs to text and discard Google metadata or insert provider HTML into the main page.

**Why it is wrong:** Citation offsets, source relationships, and required Search Suggestions are lost; direct HTML injection creates an avoidable UI trust problem.

**Do this instead:** Persist exact answer plus structured metadata and render provider HTML in an isolated document.

### Anti-Pattern 6: External Calls Inside Database Transactions

**What people do:** Open a transaction, call an LLM/tool for seconds, then commit everything.

**Why it is wrong:** Locks and connections are held across unpredictable network latency and cancellation.

**Do this instead:** Persist accepted state, perform the call without a transaction, then finalize in a short transaction.

### Anti-Pattern 7: One Default Compose Network

**What people do:** Attach frontend, gateway, backend, database, search, and sandbox to Compose's default network.

**Why it is wrong:** A compromise in any service gains unnecessary lateral reach.

**Do this instead:** Use explicit edge, app, data, search, sandbox, and service-specific egress networks.

### Anti-Pattern 8: Security Logging That Copies Secrets or Content

**What people do:** Log headers, request bodies, model prompts, Python code, or provider responses for debugging.

**Why it is wrong:** Logs become a second sensitive database and may expose bearer credentials or private conversation content.

**Do this instead:** Log identifiers, sizes, hashes, states, timings, counts, and safe error categories.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| OpenAI-compatible provider | Backend outbound HTTPS to fixed base URL | Chat Completions compatibility contract; explicit timeouts/retries; log provider request ID |
| Gemini API / Google Search | Search-agent outbound HTTPS through Google ADK | Preserve final event grounding metadata and required Search Suggestions |
| Cloudflare Turnstile | Backend POST to Siteverify | Mandatory server validation; five-minute, single-use tokens |
| Cloudflare Tunnel, optional | `cloudflared` outbound connection | Do not publish origin ports when deployed through Tunnel |
| Docker Engine | Sandbox supervisor only | Highest-risk local integration; hardcoded job spec and no user-controlled Docker fields |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Frontend to API | HTTPS JSON, optional SSE later | Browser is untrusted; all calls pass Kong |
| Kong to backend | Private HTTP on `app_rpc` | Backend revalidates JWT and ignores identity headers for authorization |
| Backend to PostgreSQL | SQLAlchemy over private network | Backend only; separate migration credentials |
| Backend to search agent | Internal HTTP JSON + capability JWT + trace context | No end-user bearer token; strict response-size limits |
| Backend to sandbox supervisor | Internal HTTP JSON + capability JWT + trace context | Fixed profile only; no arbitrary execution configuration |
| Supervisor to job container | Docker attach/stdin/stdout | Job has no network, service credential, or Docker socket |

## Research Confidence and Open Questions

| Area | Confidence | Notes |
|------|------------|-------|
| Component/trust boundaries | HIGH | Derived from official Docker, Kong, OAuth/JWT, and provider constraints |
| Google grounding flow | HIGH | Current Google API and ADK docs specify metadata and Search Suggestions behavior |
| Kong OSS JWT split | HIGH | Official plugin docs define signature and limited registered-claim verification |
| Cloudflare Free edge capabilities | HIGH | Current official pages list Tunnel availability, five Free custom rules, and Bot Fight Mode limitations |
| Sandbox containment | MEDIUM-HIGH | Docker controls are documented; Docker-socket supervisor remains an acknowledged prototype risk |

Open implementation questions to resolve during phase planning:

1. Resolve the Gemini 2 requirement against the configured account on the demonstration date. `gemini-2.5-flash` is already in its documented earliest-shutdown month as of June 8, 2026.
2. Decide whether v1 exposes non-streaming chat only or implements SSE immediately. The persistence model supports either.
3. Decide whether PostgreSQL RLS is included in the prototype milestone or documented as defense-in-depth after app-level BOLA controls.
4. Validate Search Suggestion iframe behavior against Google's current terms and the exact returned markup during integration testing.

## Sources

All factual constraints below use official or primary documentation.

- Google ADK, tool limitations and version-specific workarounds: https://adk.dev/tools/limitations/
- Google ADK, Google Search tool: https://adk.dev/tools/gemini-api/google-search/
- Gemini API, Google Search grounding metadata and citation structure: https://ai.google.dev/gemini-api/docs/google-search
- Gemini API model availability: https://ai.google.dev/models/gemini
- Gemini API deprecation schedule: https://ai.google.dev/gemini-api/docs/deprecations
- Gemini API Additional Terms, Grounding with Google Search: https://ai.google.dev/gemini-api/terms
- OpenAI API, Chat Completions reference: https://platform.openai.com/docs/api-reference/chat/create
- OpenAI Python SDK, request IDs, retries, and timeouts: https://github.com/openai/openai-python
- OAuth 2.0 Security Best Current Practice, RFC 9700: https://www.rfc-editor.org/rfc/rfc9700
- JSON Web Token Best Current Practices, RFC 8725: https://www.rfc-editor.org/rfc/rfc8725
- Kong Gateway DB-less mode: https://developer.konghq.com/gateway/db-less-mode/
- Kong JWT plugin: https://developer.konghq.com/plugins/jwt/
- Kong Rate Limiting plugin: https://developer.konghq.com/plugins/rate-limiting/
- Kong CORS plugin: https://developer.konghq.com/plugins/cors/
- Kong Request Size Limiting plugin: https://developer.konghq.com/plugins/request-size-limiting/
- Kong Correlation ID plugin: https://developer.konghq.com/plugins/correlation-id/
- Cloudflare Tunnel: https://developers.cloudflare.com/tunnel/
- Cloudflare WAF custom-rule availability: https://developers.cloudflare.com/waf/custom-rules/
- Cloudflare Bot Fight Mode: https://developers.cloudflare.com/bots/get-started/bot-fight-mode/
- Cloudflare Turnstile server-side validation: https://developers.cloudflare.com/turnstile/get-started/server-side-validation/
- Docker Compose networking: https://docs.docker.com/compose/how-tos/networking/
- Docker Compose network attributes, including `internal`: https://docs.docker.com/reference/compose-file/networks/
- Docker Compose service attributes and port binding warning: https://docs.docker.com/reference/compose-file/services/
- Docker `none` network driver: https://docs.docker.com/engine/network/drivers/none/
- Docker resource constraints: https://docs.docker.com/engine/containers/resource_constraints/
- Docker seccomp profiles: https://docs.docker.com/engine/security/seccomp/
- Docker tmpfs mounts: https://docs.docker.com/engine/storage/tmpfs/
- PostgreSQL Row-Level Security: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- OpenTelemetry Logs Data Model: https://opentelemetry.io/docs/specs/otel/logs/data-model/
- W3C Trace Context: https://www.w3.org/TR/trace-context/

---
*Architecture research for: Design a Secure Chatbot Application with Lightweight Agent Capabilities*
*Researched: 2026-06-08*
