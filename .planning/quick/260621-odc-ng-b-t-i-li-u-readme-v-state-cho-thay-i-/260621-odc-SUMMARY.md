---
status: complete
date: 2026-06-21
commit: uncommitted
---

# Quick Task 260621-odc Summary

## Completed

- Updated `README.md` to clarify the current deployment context as local-first/self-hosted internal demo, with optional Cloudflare edge in front of Kong.
- Added a dedicated security section summarizing the implemented controls for auth/session, fail-closed authorization, sandbox isolation, redaction, encryption at rest, and safe Markdown rendering.
- Updated the observability section to include the Grafana health endpoint and the `restart: unless-stopped` contract for long-running Compose services.
- Recorded this synchronization task in `.planning/STATE.md`.

## Verification

- Re-read the updated README sections for topology, security, observability, and current status.
- Re-checked `compose.yaml` to confirm the long-running services are configured with `restart: unless-stopped`.
- No automated tests were run because this quick task only synchronized documentation/state artifacts to existing implemented behavior.

## Notes

- The runtime fix for stack auto-recovery was already applied separately in `compose.yaml` and gateway integration coverage; this quick task only brought README/STATE back in sync with that state.
