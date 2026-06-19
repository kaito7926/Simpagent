---
phase: 06-adversarial-verification-and-vietnamese-delivery
plan: "03"
subsystem: scanner-guidance
tags: [phase-06, scanners, semgrep, trivy, burp, awvs, zap, templates]

requires:
  - phase: 06-adversarial-verification-and-vietnamese-delivery
    provides: security-tests directory and evaluator entrypoint
provides:
  - Practical Phase 6 scanner guidance for Semgrep, dependency/image scans, and authenticated DAST
  - Reusable finding and evidence-index templates
  - Clear documentation that scanners complement rather than replace business-logic proofs
affects: [phase-06, security-tests, docs]

tech-stack:
  added: []
  patterns:
    - Repo-owned markdown guidance and templates instead of environment-specific raw scanner dumps

key-files:
  created:
    - .planning/phases/06-adversarial-verification-and-vietnamese-delivery/06-03-SUMMARY.md
    - security-tests/scanners/README.md
    - security-tests/scanners/semgrep.md
    - security-tests/scanners/dependency-and-image.md
    - security-tests/scanners/burp-awvs-zap.md
    - security-tests/templates/finding-template.md
    - security-tests/templates/evidence-index-template.md
  modified:
    - docs/testing.vi.md

key-decisions:
  - Keep scanner artifacts as guidance/templates, not committed raw outputs tied to one machine or one run.
  - State explicitly that scanner findings supplement, but do not prove, replay/BOLA/guardrail/sandbox controls.

patterns-established:
  - Evaluators have one scanner index plus two reusable templates for findings and evidence storage conventions.

requirements-completed: [TEST-08]

duration: "1 session"
completed: 2026-06-19
---

# Phase 06 Plan 03: Scanner Guidance and Evidence Templates Summary

**Added the practical scanner layer and report templates required to complete the evaluator evidence pack.**

## Accomplishments

- Added scanner guidance for Semgrep, dependency audits, image/config scanning, and authenticated DAST.
- Added focused usage guidance for Burp Suite, AWVS, and ZAP within the owned local stack.
- Added reusable templates for recording findings and indexing environment-specific evidence outside Git.
- Linked the scanner layer back into the Vietnamese testing documentation so evaluators can treat it as supportive proof instead of a replacement for logic-level tests.

## Task Commits

No task commits were created during this closeout session. The work remains in the current working tree.

## Verification

- `rg -n "Semgrep|Trivy|Bandit|pip-audit|Burp|AWVS|ZAP|finding template" security-tests docs README.md` - expected scanner and template references are present.

## Next Phase Readiness

Plan 03 completed the repo-owned scanner and evidence-template layer needed by the final Vietnamese testing/runbook/verification docs.
