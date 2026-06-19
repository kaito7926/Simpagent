---
phase: 06-adversarial-verification-and-vietnamese-delivery
plan: "04"
subsystem: vietnamese-docs
tags: [phase-06, README, architecture, security, mermaid, vietnamese]

requires:
  - phase: 06-adversarial-verification-and-vietnamese-delivery
    provides: verified runtime behavior and scanner guidance
provides:
  - Vietnamese README entrypoint aligned to the implemented stack
  - Dedicated architecture and security docs with Mermaid diagrams and truthful trust-boundary explanations
  - Explicit documentation of provider dependence, gateway scope, sandbox limits, and Phase 03 historical debt
affects: [phase-06, docs, README]

tech-stack:
  added: []
  patterns:
    - README as evaluator/operator entrypoint with deeper architecture/security material split into `docs/*.vi.md`

key-files:
  created:
    - .planning/phases/06-adversarial-verification-and-vietnamese-delivery/06-04-SUMMARY.md
    - docs/architecture.vi.md
    - docs/security.vi.md
  modified:
    - README.md

key-decisions:
  - The docs describe the real stack and its current limitations instead of reconstructing an idealized dependency-order history.
  - Mermaid diagrams live in the architecture doc, while security control explanations stay in the dedicated security doc.

patterns-established:
  - The README now links directly to the deeper Vietnamese docs and the Phase 6 security-test entrypoint.

requirements-completed: [DOCS-01, DOCS-02, DOCS-03]

duration: "1 session"
completed: 2026-06-19
---

# Phase 06 Plan 04: README, Architecture, and Security Docs Summary

**Delivered the core Vietnamese documentation set that explains the implemented prototype and its real trust boundaries.**

## Accomplishments

- Updated `README.md` so it acts as the truthful operator/evaluator entrypoint for startup, stack shape, demo accounts, testing entrypoints, and limitations.
- Added `docs/architecture.vi.md` with Mermaid component, trust-boundary, request-flow, and network-flow diagrams.
- Added `docs/security.vi.md` covering local auth, OAuth, JWT lifecycle, refresh replay, scopes/RBAC, BOLA, coordinator/tool policy, grounding, sandbox isolation, logging, and admin evidence.
- Kept the historical Phase 03 planning debt visible in both README and docs instead of silently rewriting the artifact history.

## Task Commits

No task commits were created during this closeout session. The work remains in the current working tree.

## Verification

- `rg -n "```mermaid|JWT|OAuth|BOLA|grounding|sandbox|Cloudflare|Kong" README.md docs` - expected architecture/security topics and Mermaid diagrams are present.

## Next Phase Readiness

Plan 04 completed the core Vietnamese documentation layer. Ready for testing/runbook/limitations docs and the final closeout artifacts.
