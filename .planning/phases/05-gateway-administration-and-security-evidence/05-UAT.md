---
status: testing
phase: 05-gateway-administration-and-security-evidence
source:
  - 05-VERIFICATION.md
started: 2026-06-16T10:48:05Z
updated: 2026-06-16T10:48:05Z
---

## Current Test

number: 1
name: Run real Google and GitHub OAuth login in a browser with provider credentials configured.
expected: |
  Each provider starts from the auth shell, returns through /api/auth/oauth/{provider}/callback, sets the same protected session model as local login, and lands in the authenticated workspace without token material in the URL or browser storage.
awaiting: user response

## Tests

### 1. Run real Google and GitHub OAuth login in a browser with provider credentials configured.

expected: Each provider starts from the auth shell, returns through /api/auth/oauth/{provider}/callback, sets the same protected session model as local login, and lands in the authenticated workspace without token material in the URL or browser storage.
result: pending

### 2. Trigger gateway-only 429 or oversized-body denials, then inspect the admin Gateway evidence page.

expected: The UI distinguishes Kong-backed gateway evidence from FastAPI security-event rows and shows only bounded redacted snippets.
result: pending

### 3. Review the small-production and Cloudflare README guidance against the local stack.

expected: Documentation is Vietnamese, keeps local Compose as primary, marks Cloudflare optional, states trusted-proxy/source-IP assumptions, and avoids HA, distributed rate-limit, enterprise edge, or production-grade sandbox claims.
result: pending

### 4. Run the assembled smoke suite with SIMPAGENT_RUN_SMOKE=true against the full Compose topology.

expected: Startup/readiness, local login, OAuth readiness/start, gateway routing, admin evidence, chat, Search, and Python smoke paths complete or degrade exactly as documented.
result: pending

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
