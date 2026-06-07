# Stack Research

**Domain:** Greenfield secure chatbot SaaS prototype with controlled agent tools
**Researched:** 2026-06-08
**Overall confidence:** HIGH

## Recommendation Summary

Use current stable framework generations, but pin compatible minor lines and commit lockfiles. The main compatibility anchor is `google-adk` 2.2: it requires FastAPI `>=0.133`, Pydantic `>=2.12`, and `google-genai >=2.4,<3`. Python 3.13 is preferred over 3.14 because ADK 2.2 explicitly classifies support through 3.13.

### Frontend

| Technology | Recommended version | Purpose | Rationale | Confidence |
|---|---:|---|---|---|
| Next.js | `>=16.2,<16.3` | App Router frontend and server runtime | 16.x is Active LTS; 16.2 is the current stable minor and includes React 19.2 integration. | HIGH |
| React / React DOM | `>=19.2,<19.3` | Chat UI, streaming state, rendering | Current documented React release and the line used by Next.js 16. | HIGH |
| TypeScript | `>=5.9,<6` | Static typing | Conservative pin while TypeScript 6.0, released immediately before this research, is still a transition release and ecosystem plugins catch up. | MEDIUM |
| Tailwind CSS | `>=4.3,<4.4` | Styling | Current stable minor; use the v4 CSS-first configuration and `@tailwindcss/postcss`. | HIGH |

Use Node.js satisfying Next.js 16's minimum `>=20.9`; select one maintained LTS line in CI and Docker, then pin the exact image digest. Do not use `next@canary`.

### Backend and Data

| Technology | Recommended version | Purpose | Rationale | Confidence |
|---|---:|---|---|---|
| Python | `>=3.13,<3.14` | Backend and trusted sandbox runtime | Modern typing/performance while remaining explicitly covered by ADK 2.2 package classifiers. | HIGH |
| FastAPI | `>=0.136,<0.137` | HTTP API, OpenAPI, dependency injection | Current release line and compatible with ADK 2.2's `>=0.133,<1` requirement. | HIGH |
| Pydantic | `>=2.12,<3` | Request, config, and provider validation | Required floor for ADK 2.2; v2 is the supported FastAPI line. | HIGH |
| SQLAlchemy | `>=2.0.50,<2.1` | ORM and transactions | Current stable 2.0 release; avoid the 2.1 beta line. | HIGH |
| Alembic | `>=1.18.4,<1.19` | Schema migrations | Current released 1.18 line; compatible with SQLAlchemy 2.0 bulk reflection. | HIGH |
| PostgreSQL | `18.4` | Durable application data | Current supported major/minor; use the current patch and pin the container digest. | HIGH |
| psycopg | `>=3.2,<4` | PostgreSQL driver | Native SQLAlchemy 2.0 sync/async support; prefer Psycopg 3 over psycopg2 for new code. | HIGH |

Prefer explicit SQLAlchemy 2.0 models and repositories over SQLModel. Keep migrations hand-reviewed: Alembic autogenerate is a draft generator, not an approval mechanism.

### Authentication and Tokens

| Library / mechanism | Recommended version | Use | Security notes | Confidence |
|---|---:|---|---|---|
| PyJWT with crypto extra | `>=2.13,<3` | Short-lived access JWTs | Use an explicit algorithm allowlist and RS256 for Kong interoperability; validate `iss`, `aud`, `exp`, `nbf`, and token type. | HIGH |
| pwdlib with Argon2 | `>=0.3,<0.4` | Password hashing | `PasswordHash.recommended()` uses modern Argon2 support; store only encoded hashes. | HIGH |
| Opaque refresh tokens | Application design | Rotation and revocation | Generate at least 256 random bits, store only a keyed hash, rotate on every use, and revoke the token family on replay. | HIGH |

Recommended browser flow:

- Keep the 5-10 minute access token in memory and send it as a Bearer token.
- Keep the refresh token only in a `Secure`, `HttpOnly`, `SameSite` cookie.
- Protect cookie-based refresh/logout endpoints with Origin checks and a CSRF token.
- Never store access or refresh tokens in `localStorage`.
- Maintain an identity adapter boundary so local credentials can later be replaced by OIDC.

### LLM and Agent Clients

| Component | Recommended version / model | Purpose | Compatibility notes | Confidence |
|---|---:|---|---|---|
| OpenAI Python SDK | `>=2,<3` | OpenAI-compatible normal chat client | Configure `base_url`, API key, timeout, retry ceiling, and model name. Use only endpoint features implemented by the selected provider. | MEDIUM |
| google-adk | `>=2.2,<2.3` | Lightweight orchestration | 2.2 is current and has breaking API/session changes from 1.x; do not mix 1.x examples or persisted sessions. | HIGH |
| google-genai | `>=2.8,<2.9` | Gemini API types and grounding metadata | Fits ADK 2.2's declared `>=2.4,<3` range. Use `google.genai`, not the legacy generative AI SDK. | HIGH |
| Gemini model | `gemini-2.5-flash` | Built-in Google Search worker | Stable, currently available, explicitly supports Google Search grounding, and satisfies the project's Gemini 2 requirement. | HIGH |

Agent structure:

- Put `GoogleSearchTool` in a dedicated search agent. ADK documents that Google Search cannot share an agent object with arbitrary other tools.
- Keep the custom Python sandbox outside that search agent and route both through a policy-enforcing coordinator.
- Persist `groundingMetadata`, including search queries, chunks, supports, and `searchEntryPoint.renderedContent`.
- Render Google's required Search Suggestions only from trusted Gemini response fields in a dedicated component; never merge that HTML into user Markdown.
- Make the model ID configuration-driven and perform a startup capability check. Do not silently fall back to an ungrounded model.

`gemini-3.5-flash` is the current Google Search documentation example, but it is not the default here because the project explicitly requires Gemini 2 and Gemini 3 has different tool-combination and search-billing behavior.

### Gateway and Local Infrastructure

| Component | Recommended version | Purpose | Notes | Confidence |
|---|---:|---|---|---|
| Docker Engine | `>=28,<31` | Container runtime | Use Linux cgroup v2; rootless mode is preferred for the sandbox host where practical. | MEDIUM |
| Docker Compose | v2, `>=2.35,<3` | Local multi-service startup | Use the current Compose Specification, not legacy `version: "3"` semantics. | MEDIUM |
| Kong Gateway OSS | `3.9.1`, pinned digest | DB-less API gateway | This is the current tag listed by the Docker Official Image. It is suitable for the prototype but is already past full support and remains in sunset support only through 2026-12-12. | HIGH |
| Kong declarative format | `_format_version: "3.0"` | DB-less configuration | Set `KONG_DATABASE=off`; keep the Admin API unexposed outside the private Compose network. | HIGH |

Kong configuration guidance:

- Use DB-less declarative Services, Routes, Consumers, JWT credentials, CORS, correlation-id, and route-specific rate limiting.
- Treat Kong OSS 3.9.1 as a constrained prototype dependency. Track disclosed gateway/OpenResty issues and reassess before any public deployment.
- Use RS256 public-key verification at Kong as coarse token screening; FastAPI must independently validate the token and enforce scopes, roles, ownership, and tool permissions.
- In DB-less mode, use `policy: local` only for the single-node prototype. Counters are node-local and do not coordinate across replicas.
- Apply strict CORS to the known frontend origin. Do not combine wildcard origins with credentials.
- Rate-limit registration/login by trusted client IP and expensive chat/tool routes separately.
- Do not expose ports `8001`/`8444` for the Admin API to the host.
- `decK sync` is not the DB-less configuration mechanism; the declarative file is the source of truth.

### Sandbox Controls

The untrusted Python process must run in a separate container, never in FastAPI, Kong, or the host process. A baseline Compose service should enforce:

```yaml
network_mode: "none"
read_only: true
user: "65532:65532"
cap_drop: ["ALL"]
security_opt:
  - no-new-privileges:true
pids_limit: 64
mem_limit: 256m
cpus: 0.50
shm_size: 32m
tmpfs:
  - /tmp:rw,noexec,nosuid,nodev,size=64m
init: true
```

Also enforce a hard wall-clock timeout, output-size limit, file-count/size limits, restrictive `ulimits`, a default or stricter seccomp profile, and no host paths, devices, secrets, API keys, or Docker socket. Build a minimal image with no shell/package manager where feasible.

Compose controls are defense in depth, not a complete hostile multi-tenant sandbox. Rootless resource limits require cgroup v2 and systemd delegation; verify effective limits with runtime tests. A production service executing adversarial code should use a stronger boundary such as gVisor, Kata, Firecracker, or a disposable VM.

### Testing and Security Tooling

| Tool | Recommended version | Purpose | Notes | Confidence |
|---|---:|---|---|---|
| pytest | `>=9,<10` | Unit/integration/security tests | Matches ADK 2.2's test dependency line; use native TOML config. | HIGH |
| pytest-asyncio | `>=1,<2` | Async API/DB tests | Use explicit async mode and event-loop scope. | MEDIUM |
| pytest-cov | `>=6,<8` | Coverage | Measure branch coverage for authorization and token paths. | MEDIUM |
| HTTPX | `>=0.28,<1` | ASGI and black-box HTTP tests | Also fits ADK 2.2's `>=0.27,<1` range. | HIGH |
| Ruff | Pin one tested minor `<1` | Lint and format | Ruff minor releases may be breaking before 1.0; update deliberately. | HIGH |
| mypy | `>=1.15,<2` | Static typing | Run on backend security and provider adapter modules. | MEDIUM |
| Bandit | `>=1.8,<2` | Python SAST | Useful baseline; do not treat findings or absence of findings as proof. | MEDIUM |
| pip-audit | `>=2.9,<3` | Python dependency audit | Run against the locked environment in CI. | MEDIUM |
| Semgrep CLI | `>=1,<2` | Custom security rules | Add project rules for missing ownership checks, unsafe subprocess use, and secret logging. | MEDIUM |
| Trivy | `>=0.60,<1` | Image, filesystem, and IaC scan | Scan built images and Compose configuration; fail on fixable high/critical issues. | MEDIUM |
| OWASP ZAP | Stable Docker image pinned by digest | DAST | Run baseline plus authenticated API scans only against the owned test stack. | MEDIUM |

Required negative and attack tests should cover BOLA/IDOR, missing scopes, cross-tenant access, refresh replay, JWT algorithm/claim confusion, brute force, SSRF, prompt injection, unauthorized tool calls, sandbox network access, resource exhaustion, filesystem escape attempts, secret leakage, and log redaction.

## Installation Shape

Resolve these ranges once, commit lockfiles, and update with reviewed pull requests.

```bash
# Frontend
npm install next@">=16.2 <16.3" react@">=19.2 <19.3" react-dom@">=19.2 <19.3"
npm install tailwindcss@">=4.3 <4.4" @tailwindcss/postcss@">=4.3 <4.4"
npm install -D typescript@">=5.9 <6"

# Backend runtime
pip install "fastapi[standard]>=0.136,<0.137" "pydantic>=2.12,<3"
pip install "sqlalchemy>=2.0.50,<2.1" "alembic>=1.18.4,<1.19"
pip install "psycopg[binary,pool]>=3.2,<4"
pip install "PyJWT[crypto]>=2.13,<3" "pwdlib[argon2]>=0.3,<0.4"
pip install "openai>=2,<3" "google-adk>=2.2,<2.3" "google-genai>=2.8,<2.9"

# Test and security baseline
pip install "pytest>=9,<10" "pytest-asyncio>=1,<2" "pytest-cov>=6,<8" "httpx>=0.28,<1"
pip install "ruff<1" "mypy>=1.15,<2" "bandit>=1.8,<2" "pip-audit>=2.9,<3" "semgrep>=1,<2"
```

Use a lock tool with hashes for Python and the package-manager lockfile for Node. Pin PostgreSQL, Kong, ZAP, and sandbox base images by immutable digest in the resolved deployment manifest.

## Compatibility Notes

| Pair | Compatibility decision |
|---|---|
| Next.js 16.2 + React 19.2 | Supported current pairing. |
| Next.js 16.2 + TypeScript 5.9 | Supported and conservative; evaluate TypeScript 6 separately before widening the range. |
| google-adk 2.2 + FastAPI 0.136 | Compatible: ADK requires `>=0.133,<1`. |
| google-adk 2.2 + Pydantic 2.12 | Compatible: ADK requires `>=2.12,<3`. |
| google-adk 2.2 + google-genai 2.8 | Compatible: ADK requires `>=2.4,<3`. |
| google-adk 2.2 + Python 3.13 | Explicitly classified by the package; avoid 3.14 until ADK declares/tests it. |
| SQLAlchemy 2.0.50 + Alembic 1.18 | Stable pair; avoid SQLAlchemy 2.1 beta. |
| PostgreSQL 18.4 + psycopg 3 | Supported by SQLAlchemy's PostgreSQL dialect. |
| PyJWT RS256 + Kong JWT plugin | Kong can verify the public key; backend remains authoritative for claims and authorization. |
| Kong DB-less + local rate limit | Correct only for one gateway node; no shared counters or central coordination. |

## Alternatives Considered

| Recommended | Alternative | Use the alternative when |
|---|---|---|
| Python 3.13 | Python 3.12 | A dependency lacks 3.13 wheels; 3.12 remains acceptable but is a legacy security-fix line. |
| PostgreSQL 18 | PostgreSQL 17 | The evaluator or hosting platform standardizes on 17; it remains supported through 2029. |
| PyJWT + pwdlib | Authlib plus an external OIDC provider | The project moves from local credentials to full OAuth2/OIDC discovery, JWKS rotation, and provider flows. |
| OpenAI SDK | Raw HTTPX adapter | A provider's OpenAI compatibility diverges enough that the SDK adds workarounds rather than value. |
| `gemini-2.5-flash` | `gemini-3.5-flash` | The Gemini 2 constraint is removed and cost/tool-combination behavior is revalidated. |
| Kong OSS 3.9.1 | Licensed Kong Gateway 3.14 LTS | Current vendor support and newer security patches justify the licensed product. |
| Docker sandbox | gVisor/Kata/Firecracker | The system becomes internet-facing or executes genuinely adversarial multi-tenant code. |

## What Not to Use

| Avoid | Why | Use instead |
|---|---|---|
| Next.js canary, React experimental, preview Gemini aliases | Moving behavior and weak reproducibility. | Stable minor ranges and lockfiles. |
| TypeScript 6 immediately by default | It is a newly released transition line; tooling compatibility has not yet been demonstrated for this project. | TypeScript 5.9, then upgrade in a dedicated change. |
| Pydantic v1 or SQLAlchemy 1.4-style APIs | Legacy APIs conflict with the selected FastAPI/ADK stack and create migration debt. | Pydantic 2.12 and SQLAlchemy 2.0 typed APIs. |
| `passlib` | Maintenance and Python 3.13 compatibility concerns; FastAPI now documents pwdlib. | `pwdlib[argon2]`. |
| `python-jose` for this greenfield build | No benefit over the current FastAPI-documented PyJWT path. | `PyJWT[crypto]` with explicit validation. |
| Long-lived JWT refresh tokens with no server record | Cannot reliably rotate, revoke, or detect replay. | Opaque hashed refresh tokens and token-family rotation. |
| Browser token storage in `localStorage` | XSS turns into durable credential theft. | Memory access token plus HttpOnly refresh cookie. |
| Trusting Kong as application authorization | Gateway JWT checks cannot enforce object ownership or all domain scopes. | Repeat validation and authorization in FastAPI. |
| Assuming Kong 3.14 is an OSS image | Kong's 3.14 LTS documentation applies to the licensed Gateway line; the Docker Official Image currently lists OSS 3.9.1. | Pin `kong:3.9.1` by digest for the prototype or select a supported licensed/alternative gateway. |
| `privileged`, host networking, host PID/IPC, devices, bind-mounted host paths, or Docker socket in the sandbox | Collapses the isolation boundary. | Hardened unprivileged container with no network and strict limits. |
| Executing user Python with backend `exec`, `eval`, `shell=True`, or host subprocesses | Direct host/backend compromise path. | Dedicated sandbox execution service only. |
| LangChain/LiteLLM in v1 | Adds abstractions, transitive dependencies, and tool paths not required by the two explicit provider adapters. | Thin OpenAI and Google adapters behind local interfaces. |
| Rendering arbitrary model/user HTML | XSS risk. | Markdown with raw HTML disabled and sanitized link/code rendering. |
| SearXNG | Explicitly out of scope and duplicates Gemini built-in search. | Gemini Google Search grounding. |

## Official Sources

- Next.js 16.2 and support policy: https://nextjs.org/blog/next-16-2 and https://nextjs.org/support-policy
- Next.js installation requirements: https://nextjs.org/docs/app/getting-started/installation
- React current version: https://react.dev/versions
- TypeScript 6.0 transition release: https://www.typescriptlang.org/docs/handbook/release-notes/typescript-6-0.html
- Tailwind CSS 4.3: https://tailwindcss.com/blog
- Python version status: https://devguide.python.org/versions/
- FastAPI releases and JWT tutorial: https://fastapi.tiangolo.com/release-notes/ and https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
- Pydantic current docs and version policy: https://docs.pydantic.dev/ and https://docs.pydantic.dev/latest/version-policy/
- SQLAlchemy 2.0 current docs: https://docs.sqlalchemy.org/en/20/
- Alembic changelog: https://alembic.sqlalchemy.org/en/latest/changelog.html
- PostgreSQL versions: https://www.postgresql.org/support/versioning/
- OpenAI official SDK guidance: https://platform.openai.com/docs/libraries
- Google ADK package metadata: https://pypi.org/project/google-adk/
- Google Gen AI SDK: https://googleapis.github.io/python-genai/
- Gemini Google Search models and metadata: https://ai.google.dev/gemini-api/docs/google-search
- ADK tool limitations: https://google.github.io/adk-docs/tools/limitations/
- Docker Compose services and rootless limits: https://docs.docker.com/reference/compose-file/services/ and https://docs.docker.com/engine/security/rootless/tips/
- Kong OSS image, support status, DB-less, JWT, and rate limiting: https://hub.docker.com/_/kong/ , https://developer.konghq.com/gateway/version-support-policy/ , https://developer.konghq.com/gateway/db-less-mode/ , https://developer.konghq.com/plugins/jwt/ , and https://developer.konghq.com/plugins/rate-limiting/
- pytest 9: https://docs.pytest.org/en/9.0.x/
- Ruff versioning: https://docs.astral.sh/ruff/versioning/
- Semgrep CLI: https://semgrep.dev/docs/cli-reference

---
*Stack research for: Design a Secure Chatbot Application with Lightweight Agent Capabilities*
*Researched: 2026-06-08*
