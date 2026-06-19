# Phase 6: Adversarial Verification and Vietnamese Delivery - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `06-CONTEXT.md` - this log preserves the alternatives considered.

**Date:** 2026-06-19
**Phase:** 6-Adversarial Verification and Vietnamese Delivery
**Areas discussed:** Phase split, attack-suite shape, documentation layout, scanner evidence policy

---

## Phase Split

| Option | Description | Selected |
|--------|-------------|----------|
| One large closeout plan | Put all tests, attacks, scanners, docs, and final verification into one plan. | |
| Five focused plans | Split the phase into automated verification, adversarial attacks, scanner guidance, core Vietnamese docs, and final docs/verification closeout. | yes |

**Selected by:** the agent, based on current repo state.
**Notes:** The repo already has broad test coverage but is missing `security-tests/`, `docs/`, and a final evidence pack. A five-plan split keeps execution slices reviewable.

---

## Attack Suite Shape

| Option | Description | Selected |
|--------|-------------|----------|
| One monolithic shell script | Single long script that runs every attack in sequence. | |
| Shared harness plus focused attack scripts | Small reusable helpers plus dedicated scripts for replay, BOLA, brute force, SSRF, prompt abuse, and sandbox abuse. | yes |
| Pure documentation only | Describe attacks without executable scripts. | |

**Selected by:** the agent.
**Notes:** Focused scripts are easier to rerun, easier to reason about, and better aligned with side-effect assertions.

---

## Documentation Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Keep everything in `README.md` | Expand the README until it covers setup, architecture, security, testing, runbooks, and limitations. | |
| README as entrypoint plus dedicated `docs/` files | Keep a practical top-level README and move deeper Vietnamese material into dedicated documents. | yes |
| Planning docs only | Rely on `.planning/` as the final evaluator documentation. | |

**Selected by:** the agent.
**Notes:** The roadmap explicitly asks for Vietnamese delivery documentation, not only internal planning artifacts.

---

## Scanner Evidence Policy

| Option | Description | Selected |
|--------|-------------|----------|
| Commit live scanner outputs | Store raw Semgrep/Trivy/ZAP/AWVS outputs in the repo. | |
| Commit runnable guidance and templates only | Document exact commands, report expectations, and a finding template; generated outputs stay environment-specific. | yes |
| Skip scanner guidance | Rely only on functional and attack tests. | |

**Selected by:** the agent.
**Notes:** Live scanner outputs are noisy and environment-dependent. The durable deliverable is the reproducible guidance plus the evaluator-facing finding template.

---

## Historical Accuracy

| Option | Description | Selected |
|--------|-------------|----------|
| Normalize the planning story | Quietly align Phase 3 history with shipped code and hide the artifact gap. | |
| Keep the debt visible | Plan and document Phase 6 with an explicit note that Phase 3 planning artifacts remain incomplete. | yes |

**Selected by:** the agent.
**Notes:** The repo already carries a stale `03-VERIFICATION.md`. Phase 6 docs should remain truthful about that state.
