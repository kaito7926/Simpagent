You are a senior full-stack security-focused coding agent.

Your task is to build a secure AI chatbot SaaS prototype for a university project named:

“Design a Secure Chatbot Application with Lightweight Agent Capabilities”

The project is a prototype of a cloud API-based network application security system for small company services. The application should work like a lightweight ChatGPT clone with secure API design, authentication, authorization, API Gateway protection, logging, and basic agent capabilities.

====================================================
1. HIGH-LEVEL GOAL
====================================================

Build a full-stack chatbot web application that includes:

- Frontend chatbot UI using NextJS.
- Backend API using FastAPI.
- PostgreSQL database.
- LLM API adapter.
- Conversation and message history.
- Lightweight agent orchestration using Google ADK.
- Web search tool.
- Python sandbox tool.
- OAuth2/OIDC authentication.
- JWT authorization.
- RBAC with Admin/User roles.
- Tool-level permission control.
- Object-level authorization for user-owned resources.
- Kong Gateway configuration for JWT verification, CORS, TLS routing, and rate limiting.
- Cloudflare-compatible deployment assumptions: Tunnel, WAF rules, Turnstile, Bot Fight Mode.
- Structured JSON logging with correlation ID.
- Security testing scripts for OWASP API Security Top 10 and OWASP LLM risks.

The project must be easy to run locally using Docker Compose.

Final expected command:

docker compose up --build

====================================================
2. TECH STACK
====================================================

Use the following stack:

Frontend:
- NextJS
- TypeScript
- TailwindCSS
- Markdown rendering
- Code block rendering
- Auth token handling

Backend:
- FastAPI
- Python 3.11+
- SQLAlchemy or SQLModel
- Pydantic
- PostgreSQL
- Alembic migrations

Agent:
- Google ADK for agent orchestration
- Tool interface for:
  - Web search
  - Python sandbox execution

Security:
- OAuth2/OIDC login flow
- JWT access token
- Refresh token
- RBAC: Admin/User
- OAuth2 scopes
- Object-level authorization
- Tool permission checks
- Rate limiting
- CORS hardening
- Security headers
- Input validation
- Secret management using environment variables

Gateway:
- Kong Gateway OSS
- JWT verification plugin
- Rate limiting plugin
- CORS plugin
- Route control

Cloudflare:
- Assume Cloudflare sits in front of Kong
- Prepare documentation/config notes for:
  - Cloudflare Tunnel
  - WAF Custom Rules
  - Turnstile on login/register
  - Bot Fight Mode
  - TLS/HTTPS

Logging:
- Structured JSON logs
- Correlation ID per request
- Auth failure logging
- Rate limit logging
- Tool execution logging
- Admin action audit logs
- Optional Loki/Grafana support

Testing:
- Pytest
- Semgrep config
- Snyk-compatible dependency setup
- Burp Suite testing guide
- AWVS testing guide
- Custom attack simulation scripts

====================================================
3. CORE FEATURES
====================================================

Implement these core product features:

A. Authentication

- User registration.
- User login.
- OAuth2/OIDC-ready structure.
- JWT access token.
- Refresh token.
- Logout / token revocation.
- Password hashing with Argon2 or bcrypt.
- Admin/User role support.
- Token claims should include:
  - sub
  - role
  - scopes
  - exp
  - iat
  - jti

B. Authorization

Implement:

- RBAC:
  - Admin can view system-level admin APIs.
  - User can only manage their own conversations/messages.
- OAuth2 scopes:
  - chat:read
  - chat:write
  - tool:websearch
  - tool:python
  - admin:read
  - admin:write
- Object-level authorization:
  - A user must not access another user’s conversations.
  - Add explicit checks to prevent BOLA.

C. Chatbot

Implement:

- Create conversation.
- List own conversations.
- Read own conversation.
- Delete own conversation.
- Send message to conversation.
- Store user message and assistant response.
- Stream response if possible; otherwise return normal JSON response.
- Render markdown/code on frontend.

D. LLM Adapter

Create a backend abstraction for LLM API:

- LLM_PROVIDER
- LLM_API_BASE
- LLM_API_KEY
- LLM_MODEL

The adapter should be OpenAI-compatible by default.

Do not hardcode secrets.

E. Lightweight Agent

Implement an agent orchestrator using Google ADK or a clean adapter layer compatible with Google ADK.

The agent should decide whether to:

- Answer directly with LLM.
- Call web search tool.
- Call Python sandbox tool.

The agent must follow strict tool policy:

- Only call allowlisted tools.
- Enforce user scopes before tool execution.
- Log every tool call.
- Apply timeout per tool call.
- Prevent arbitrary external API calls.
- Do not allow sensitive actions such as sending email, payment, deleting data, or calling unknown APIs.

F. Web Search Tool

Implement a web search tool interface:

- Input: query string.
- Output: summarized search results with source URLs.
- Add timeout.
- Add result limit.
- Sanitize result text.
- Log search query and result count.
- Do not expose API keys to frontend.

Use a simple provider abstraction, for example:

- SearXNG
- Brave Search API
- Tavily
- Serper
- Firecrawl

Choose one default provider that is easy to run locally or configure by environment variables.

G. Python Sandbox Tool

Implement a sandbox for running Python code.

Requirements:

- Run code in isolated Docker container or restricted subprocess container.
- Timeout.
- Memory limit.
- CPU limit.
- No network access by default.
- Read-only base image if possible.
- Temporary working directory.
- Capture stdout/stderr.
- Return execution result safely.
- Prevent host file access.
- Prevent long-running loops.
- Prevent package installation unless explicitly allowlisted.

The backend must never execute Python directly on the host process.

H. Admin APIs

Implement basic admin endpoints:

- List users.
- View recent audit logs.
- View tool execution logs.
- View failed login attempts.
- View rate-limit events if available.

Admin APIs must require admin role and admin scopes.

====================================================
4. API DESIGN
====================================================

Create FastAPI routes similar to:

Auth:
- POST /api/auth/register
- POST /api/auth/login
- POST /api/auth/refresh
- POST /api/auth/logout
- GET  /api/auth/me

Users:
- GET /api/users/me
- PATCH /api/users/me
- GET /api/admin/users

Conversations:
- POST /api/conversations
- GET /api/conversations
- GET /api/conversations/{conversation_id}
- DELETE /api/conversations/{conversation_id}

Messages:
- POST /api/conversations/{conversation_id}/messages
- GET /api/conversations/{conversation_id}/messages

Tools:
- POST /api/tools/web-search
- POST /api/tools/python
- GET /api/tools/logs

Admin:
- GET /api/admin/audit-logs
- GET /api/admin/security-events
- GET /api/admin/metrics

Health:
- GET /health
- GET /ready

====================================================
5. DATABASE DESIGN
====================================================

Create database models for:

User:
- id
- email
- password_hash
- role
- scopes
- is_active
- created_at
- updated_at

RefreshToken:
- id
- user_id
- token_hash
- jti
- expires_at
- revoked_at
- created_at

Conversation:
- id
- user_id
- title
- created_at
- updated_at

Message:
- id
- conversation_id
- role: user/assistant/system/tool
- content
- metadata
- created_at

ToolExecution:
- id
- user_id
- conversation_id
- tool_name
- input_summary
- output_summary
- status
- duration_ms
- created_at

AuditLog:
- id
- user_id
- action
- resource_type
- resource_id
- ip_address
- user_agent
- correlation_id
- metadata
- created_at

SecurityEvent:
- id
- event_type
- severity
- user_id
- ip_address
- description
- metadata
- created_at

====================================================
6. SECURITY REQUIREMENTS
====================================================

Implement the following protections:

Authentication:
- Hash passwords securely.
- Short-lived access tokens.
- Refresh token rotation or revocation.
- JWT validation with exp, iat, jti.
- Secure token storage guidance for frontend.
- Avoid leaking token in logs.

Authorization:
- Enforce RBAC.
- Enforce scopes.
- Enforce object ownership.
- Add tests proving users cannot access other users’ conversations.

API Security:
- Validate all inputs with Pydantic.
- Configure CORS allowlist.
- Add security headers.
- Add request size limits if possible.
- Add rate limiting support at app level or gateway level.
- Add safe error responses without stack traces.

LLM Security:
- Add system prompt guardrails.
- Add prompt injection warning layer.
- Do not allow the model to override security policy.
- Do not expose secrets to LLM context.
- Do not pass full environment variables to tools.
- Restrict tools by permission.
- Log tool calls.

Sandbox Security:
- No host execution.
- No network by default.
- Timeout.
- Memory limit.
- CPU limit.
- Clean temporary files after execution.
- Return stdout/stderr safely.

SSRF Protection:
- For web search or fetch-like tools, block:
  - localhost
  - 127.0.0.0/8
  - 0.0.0.0
  - private IP ranges
  - link-local IPs
  - metadata IP 169.254.169.254
  - internal Docker networks

Logging:
- Add correlation ID middleware.
- Log structured JSON.
- Log auth failures.
- Log forbidden access.
- Log tool executions.
- Log admin actions.
- Do not log passwords, refresh tokens, access tokens, API keys, or secrets.

====================================================
7. KONG GATEWAY
====================================================

Create Kong configuration for:

- Service: backend FastAPI.
- Routes:
  - /api/*
  - /health
- CORS plugin with strict allowed origins.
- Rate limiting plugin:
  - Login endpoints: strict limit.
  - Chat endpoints: moderate limit.
  - Tool endpoints: strict limit.
- JWT verification plugin if practical.
- Request/response logging if practical.

Provide declarative Kong config file:

- kong/kong.yml

Also provide documentation:

- How to run Kong with Docker Compose.
- How requests flow:
  Client -> Cloudflare -> Kong -> FastAPI -> DB/LLM/Tools

====================================================
8. CLOUDFLARE DEPLOYMENT NOTES
====================================================

Create docs/cloudflare.md explaining:

- Cloudflare Tunnel setup.
- DNS configuration.
- Turnstile integration points for login/register.
- Bot Fight Mode.
- WAF Custom Rules suggestions:
  - Block suspicious paths.
  - Challenge login/register abuse.
  - Block known scanner user agents.
  - Block requests with suspicious payload patterns.
- TLS/HTTPS recommendation.
- What Cloudflare Free can and cannot do.

Do not require paid Cloudflare features.

====================================================
9. DOCKER COMPOSE
====================================================

Create Docker Compose setup for:

- frontend
- backend
- postgres
- kong
- kong database if needed, or DB-less Kong mode
- optional searxng
- optional loki/grafana
- python-sandbox image

The system should run with:

docker compose up --build

Provide:

- .env.example
- README.md
- docs/architecture.md
- docs/security.md
- docs/testing.md

====================================================
10. TESTING REQUIREMENTS
====================================================

Write automated tests for:

Auth:
- Register
- Login
- Refresh
- Invalid token
- Expired token
- Logout/revoked token

Authorization:
- User cannot access another user’s conversation.
- User cannot call admin API.
- User without tool scope cannot call tool.
- Admin can access admin API.

Chat:
- Create conversation.
- Send message.
- List messages.

Tools:
- Web search requires scope.
- Python sandbox requires scope.
- Python sandbox times out infinite loop.
- Python sandbox blocks network.
- Python sandbox limits memory.

Security:
- BOLA simulation.
- Brute force simulation.
- Token replay simulation.
- Prompt injection simulation.
- SSRF blocked target simulation.
- Tool abuse simulation.
- Sandbox escape attempt simulation.

Create attack simulation scripts in:

security-tests/

Examples:

- bola_test.py
- brute_force_test.py
- token_replay_test.py
- ssrf_test.py
- sandbox_escape_test.py
- prompt_injection_test.py

====================================================
11. SAST / DAST
====================================================

Add:

- semgrep.yml or semgrep command guide.
- snyk test guide.
- Burp Suite testing checklist.
- AWVS testing checklist.

Create docs/security-testing-report-template.md with sections:

- Finding name
- Severity
- Affected endpoint
- Description
- Steps to reproduce
- Evidence
- Impact
- Root cause
- Fix
- Retest result

====================================================
12. PROJECT STRUCTURE
====================================================

Use a clean monorepo structure:

secure-chatbot-agent/
├── frontend/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── security/
│   │   ├── agent/
│   │   ├── tools/
│   │   ├── logging/
│   │   └── main.py
│   ├── tests/
│   └── Dockerfile
├── sandbox/
│   ├── Dockerfile
│   └── runner.py
├── kong/
│   └── kong.yml
├── security-tests/
├── docs/
│   ├── architecture.md
│   ├── cloudflare.md
│   ├── security.md
│   ├── testing.md
│   └── runbook.md
├── docker-compose.yml
├── .env.example
└── README.md

====================================================
13. DOCUMENTATION REQUIREMENTS
====================================================

Write documentation in Vietnamese.

README.md should include:

- Project overview.
- Architecture.
- Prerequisites.
- Environment variables.
- How to run.
- How to test.
- Demo accounts.
- API documentation URL.
- Security features.
- Known limitations.

docs/architecture.md should include:

- Component diagram in Mermaid.
- Request flow.
- Trust boundaries.
- Network flow:
  Client -> Cloudflare -> Kong -> FastAPI -> PostgreSQL/LLM/Tools

docs/security.md should include:

- OAuth2/OIDC flow.
- JWT lifecycle.
- RBAC/scopes.
- Object-level authorization.
- Tool permission model.
- Sandbox isolation model.
- Logging/audit model.

docs/testing.md should include:

- SAST guide.
- DAST guide.
- Manual Burp testing.
- Attack simulation guide.

docs/runbook.md should include:

- Brute force response.
- Token replay response.
- BOLA incident response.
- Prompt injection response.
- Sandbox abuse response.
- SSRF attempt response.

====================================================
14. NON-GOALS
====================================================

Do not implement:

- LLM training.
- LLM fine-tuning.
- RAG or knowledge base.
- Kubernetes.
- Large-scale production multi-cloud deployment.
- Sensitive agent actions like sending emails, payment, deleting external data, or calling arbitrary third-party APIs.
- Advanced ML-based anomaly detection.
- Real pentesting against third-party systems.

====================================================
15. ACCEPTANCE CRITERIA
====================================================

The project is complete when:

1. docker compose up --build starts the full system.
2. Frontend can register/login user.
3. User can create a conversation and send a message.
4. Conversation history is stored in PostgreSQL.
5. Backend can call LLM through configurable OpenAI-compatible API.
6. Agent can call web search when allowed.
7. Agent can run Python code in sandbox when allowed.
8. Sandbox has timeout, memory/CPU limit, and no network by default.
9. User cannot access another user’s conversation.
10. User without permission cannot call restricted tools.
11. Admin APIs require admin role.
12. Kong Gateway is configured with route, CORS, JWT/rate-limit plan.
13. Structured JSON logs include correlation ID.
14. Security test scripts exist and can demonstrate:
    - BOLA blocked
    - brute force rate-limited
    - token replay detected or blocked
    - SSRF blocked
    - sandbox escape attempt blocked
    - prompt/tool abuse controlled
15. Documentation is written in Vietnamese.
16. README explains how to run and test everything.

====================================================
16. DEVELOPMENT STRATEGY
====================================================

Work incrementally.

Phase 1:
- Create monorepo structure.
- Implement backend skeleton.
- Implement database models.
- Implement auth and JWT.
- Implement conversation/message APIs.

Phase 2:
- Implement frontend chatbot UI.
- Connect frontend to backend.
- Add markdown/code rendering.
- Add token handling.

Phase 3:
- Implement LLM adapter.
- Implement agent abstraction.
- Implement web search tool.
- Implement Python sandbox tool.

Phase 4:
- Add security hardening:
  - RBAC
  - scopes
  - object-level authorization
  - CORS
  - logging
  - correlation ID
  - audit log

Phase 5:
- Add Kong Gateway config.
- Add Docker Compose.
- Add Cloudflare documentation.

Phase 6:
- Add automated tests.
- Add security attack simulation scripts.
- Add SAST/DAST docs.
- Add final Vietnamese documentation.

====================================================
17. CODING RULES
====================================================

- Prefer simple, maintainable code.
- Do not hardcode secrets.
- Use environment variables.
- Add meaningful comments only for complex security logic.
- Add tests for security-sensitive logic.
- Fail securely by default.
- Never bypass authorization checks for convenience.
- Never execute sandbox code directly inside the backend process.
- Keep frontend and backend cleanly separated.
- Use typed schemas and validation everywhere.
- Use least privilege for tools.
- Log security events but never log secrets.

Start by creating the repository structure, Docker Compose foundation, backend FastAPI skeleton, database models, and authentication flow.