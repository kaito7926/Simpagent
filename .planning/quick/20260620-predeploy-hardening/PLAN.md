---
status: in_progress
created: 2026-06-20
slug: predeploy-hardening
---

# Predeploy hardening

Implement the final pre-internet deployment fixes from the deployment review.

Scope:

- Ignore production env and secret directories.
- Make the production example default to one public origin for app and API.
- Move production PostgreSQL password to a secret file.
- Add optional invite-code gating for public registration.
- Add basic browser security headers.
- Improve production container behavior where possible without changing the local startup contract.
- Document the deployment checklist and validation commands in Vietnamese.

Verification:

- `docker compose --env-file .env.production.example -f compose.yaml -f compose.prod.yaml config -q`
- Frontend typecheck and audit.
- Targeted backend tests when the Python test environment is available.
