# Phase 1: Secure Platform and Account Access - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-06-08
**Phase:** 1-secure-platform-and-account-access
**Areas discussed:** Account defaults

---

## Account Defaults

### Default User Scopes

| Option | Description | Selected |
|--------|-------------|----------|
| Chat only | New users receive `chat:read` and `chat:write`; tool scopes require explicit assignment | |
| All user capabilities | New users receive chat, Web Search, and Python scopes | ✓ |
| Chat + Search | New users receive chat and Web Search; Python remains explicitly assigned | |

**User's choice:** All user capabilities.
**Notes:** New users receive `chat:read`, `chat:write`, `tool:websearch`, and `tool:python`.

### First Admin Bootstrap

| Option | Description | Selected |
|--------|-------------|----------|
| One-time bootstrap command | Explicit operator command creates or promotes the first Admin; no production default credentials | ✓ |
| Environment bootstrap | Startup creates an Admin from environment credentials | |
| Database seed | Compose always creates a documented Admin | |

**User's choice:** One-time bootstrap command.
**Notes:** Production must not automatically provision a default Admin.

### Registration Authority

| Option | Description | Selected |
|--------|-------------|----------|
| Never | Registration always creates an active User with fixed default scopes | ✓ |
| Invite code | A protected invite can assign a predefined scope bundle | |
| Development only | Development registration can choose roles or scopes | |

**User's choice:** Never.
**Notes:** Registration clients cannot choose or request roles and scopes.

### Demo Accounts

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit seed command | Demo accounts are created only when an operator runs a command | |
| No demo accounts | Evaluators register users and bootstrap Admin manually | |
| Automatic in development | Compose creates demo User and Admin accounts in development mode | ✓ |

**User's choice:** Automatic in development.
**Notes:** Exact credentials and reset behavior were left to the agent, with production seeding prohibited.

### Area Completion

| Option | Description | Selected |
|--------|-------------|----------|
| Clarify demo behavior | Continue discussing credentials and reset semantics | |
| Finish this area | Delegate remaining details within the locked security requirements | ✓ |

**User's choice:** Finish this area.
**Notes:** Session behavior, registration experience, and startup readiness were not selected for discussion.

---

## the agent's Discretion

- Session lifetimes, multi-device behavior, logout scope, and replay-response details.
- Password policy and safe registration error details.
- Development demo credentials and idempotent reseeding behavior.
- Provider startup versus degraded-readiness behavior.
- Technical architecture and implementation mechanics within the locked stack and requirements.

## Deferred Ideas

None.
