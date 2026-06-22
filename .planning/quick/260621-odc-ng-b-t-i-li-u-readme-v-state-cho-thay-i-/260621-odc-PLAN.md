---
status: in_progress
date: 2026-06-21
---

# Quick Task 260621-odc: Sync README/STATE for supplemental Grafana, deployment, security, and local resiliency changes

## Must Haves

- README must explicitly state the current deployment context as local-first/self-hosted internal demo with optional Cloudflare edge.
- README must summarize the security controls that are already implemented in the repo without overstating production guarantees.
- README must document the current Grafana/observability capabilities and the auto-restart contract for long-running Compose services.
- `.planning/STATE.md` must record this synchronization task and point to the quick-task directory.

## Tasks

1. Update the relevant README sections for deployment context, security controls, and local observability/resiliency.
2. Create quick-task artifacts and add the completed row to `.planning/STATE.md`.
3. Re-read the changed documentation and confirm it matches the current implementation.
