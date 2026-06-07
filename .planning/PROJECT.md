# Design a Secure Chatbot Application with Lightweight Agent Capabilities

## What This Is

A university-project prototype of a secure, cloud API-based chatbot SaaS for small-company services. It provides a ChatGPT-like web experience backed by a security-focused FastAPI API, PostgreSQL persistence, dual LLM providers, lightweight Google ADK orchestration, and tightly controlled web-search and Python-sandbox tools.

The system is designed to run locally through Docker Compose while demonstrating practical API, identity, authorization, gateway, observability, LLM, and sandbox security controls.

## Core Value

Users can safely authenticate and use an AI chatbot with controlled agent tools without crossing tenant, role, scope, network, or host-execution boundaries.

## Requirements

### Validated

(None yet - ship to validate)

### Active

- [ ] A Next.js and TypeScript frontend supports registration, login, chatbot conversations, history, Markdown, and code rendering.
- [ ] A FastAPI backend persists users, refresh tokens, conversations, messages, tool executions, audit logs, and security events in PostgreSQL.
- [ ] Local email/password authentication issues short-lived JWT access tokens and revocable or rotated refresh tokens through an OAuth2/OIDC-ready adapter.
- [ ] RBAC, OAuth2 scopes, object ownership checks, and explicit tool permissions prevent unauthorized resource and tool access.
- [ ] An OpenAI-compatible provider handles normal chat while Gemini 2 through Google ADK provides built-in Google Search.
- [ ] A separate, scope-controlled Python sandbox worker executes code in Docker with no host execution, no network by default, and strict resource limits.
- [ ] Kong protects backend routes with strict CORS, TLS-ready routing, JWT verification where practical, and endpoint-specific rate limits.
- [ ] Structured JSON logs and correlation IDs cover requests, authentication failures, forbidden access, tool execution, administration, and security events without logging secrets.
- [ ] Docker Compose starts the frontend, backend, PostgreSQL, Kong, and Python sandbox foundation with `docker compose up --build`.
- [ ] Automated tests and attack simulations demonstrate controls against BOLA, brute force, token replay, SSRF, prompt injection, tool abuse, and sandbox escape attempts.
- [ ] Vietnamese documentation explains architecture, setup, operation, security controls, Cloudflare deployment assumptions, and SAST/DAST testing.

### Out of Scope

- LLM training or fine-tuning - the prototype consumes external model APIs.
- RAG or a knowledge base - not required to demonstrate the target agent and API security controls.
- Kubernetes or production-scale multi-cloud deployment - Docker Compose is the deployment target.
- Sensitive agent actions such as email, payments, external deletion, or arbitrary API calls - the tool model is intentionally allowlisted and low impact.
- Advanced ML anomaly detection - security events and deterministic controls are sufficient for the prototype.
- Real penetration testing of third-party systems - testing is limited to the owned local application.
- SearXNG or another standalone search provider - web search uses Google ADK's built-in Google Search capability.
- Fully hosted OIDC infrastructure in the default Compose stack - v1 uses local credentials behind an OIDC-ready identity abstraction.

## Context

- The project title is "Design a Secure Chatbot Application with Lightweight Agent Capabilities."
- The primary audience is a university evaluator and developers demonstrating a defensible secure network application for small-company use.
- The supplied brief defines a greenfield monorepo with `frontend/`, `backend/`, `sandbox/`, `kong/`, `security-tests/`, and `docs/`.
- Full chat operation requires real external model credentials; the default runtime does not provide a mock LLM.
- Normal chat uses a configurable OpenAI-compatible endpoint. Google Search uses a Gemini 2 model through Google ADK.
- Google Search grounding data and required search suggestions must be preserved by the backend and rendered by the frontend.
- Because ADK built-in tools have composition constraints, orchestration separates the Google Search worker from the custom Python sandbox worker behind a policy-enforcing coordinator.
- Cloudflare is documented as an optional edge layer in front of Kong, using Free-plan-compatible Tunnel, WAF, Turnstile, Bot Fight Mode, and TLS guidance where available.
- Security evidence is a product deliverable: controls need tests, logs, attack simulations, and clear documentation rather than configuration claims alone.

## Constraints

- **Frontend**: Next.js, TypeScript, Tailwind CSS, Markdown rendering, and code-block rendering - required by the project brief.
- **Backend**: FastAPI, Python 3.11+, Pydantic, SQLAlchemy or SQLModel, PostgreSQL, and Alembic - required by the project brief.
- **Agent**: Google ADK coordinates lightweight agent behavior; Gemini 2 is required for built-in Google Search.
- **LLM providers**: OpenAI-compatible credentials are required for normal chat and Google credentials are required for ADK search - no embedded or hardcoded secrets.
- **Authentication**: Local email/password authentication must work in v1 while identity code remains replaceable by a standards-based OAuth2/OIDC provider.
- **Authorization**: RBAC, scopes, ownership, and tool permissions must fail closed and must be covered by negative tests.
- **Sandbox**: User Python never executes in the backend or directly on the host; execution occurs only in an isolated Docker worker with timeout, CPU, memory, filesystem, process, and network restrictions.
- **Deployment**: `docker compose up --build` is the required local startup command.
- **Gateway**: Kong OSS runs DB-less unless a database becomes demonstrably necessary.
- **Documentation**: User-facing project documentation is written in Vietnamese.
- **Security**: Tokens, passwords, API keys, and secrets must never be logged or sent to tools or model context.
- **Scope**: Prefer a demonstrable, maintainable prototype over production-scale completeness.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use local email/password auth behind an OIDC-ready adapter | The local demo must be runnable without operating Keycloak or depending on university SSO while preserving a migration path | - Pending |
| Require real model credentials | The project should demonstrate actual LLM integration rather than a mock response path | - Pending |
| Use an OpenAI-compatible provider for normal chat | Preserves provider flexibility and matches the requested LLM adapter contract | - Pending |
| Use Gemini 2 and Google ADK built-in Google Search | The requested built-in search capability is Gemini-specific and removes the need for SearXNG | - Pending |
| Separate search and Python workers behind a policy coordinator | Supports ADK tool-composition constraints and keeps scope checks, logging, and execution boundaries explicit | - Pending |
| Use a dedicated Docker Python sandbox worker | Prevents untrusted code from executing in the backend or host process | - Pending |
| Use Kong OSS in DB-less mode by default | Keeps local operation simple while supporting declarative routes and plugins | - Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `$gsd-transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone:**
1. Review all sections for accuracy
2. Confirm the Core Value remains the correct priority
3. Audit Out of Scope reasons
4. Update Context with implementation evidence, feedback, and known limitations

---
*Last updated: 2026-06-08 after initialization*
