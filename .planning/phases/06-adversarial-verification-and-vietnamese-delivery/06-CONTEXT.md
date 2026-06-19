# Phase 6: Adversarial Verification and Vietnamese Delivery - Context

**Gathered:** 2026-06-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Close the project with proof and delivery work, not another product feature slice. Phase 6 must verify the assembled local topology against the claimed security properties, package the attack and scanner evidence into repeatable evaluator workflows, and ship Vietnamese documentation that matches the real implementation and its limits.

</domain>

<decisions>
## Implementation Decisions

### Scope and Evidence
- **D-01:** Phase 6 does not add net-new product features unless a verification blocker makes an existing claim false. Any runtime code change must be justified as proof-enabling or truth-restoring.
- **D-02:** Prefer wrapping and extending the existing auth/chat/search/python/gateway/admin tests into phase-level evidence runners before inventing broad new test surfaces from scratch.
- **D-03:** Attack scripts must run only against the owned local Compose topology and must assert real side effects in database, network, process, or persisted evidence state rather than relying only on HTTP wording or model refusal text.
- **D-04:** Search and Python abuse verification must prove zero forbidden side effects even when the UI or model text appears to deny the action.
- **D-05:** Canary-secret checks are part of the final proof pack. Phase 6 must keep scanning both success and failure paths for protected values in logs, evidence rows, API payloads, and generated artifacts.

### Delivery Shape
- **D-06:** Evaluator-facing attack assets live under `security-tests/`. They should be reproducible from the repo root and should emit bounded reports or exit codes suitable for manual review.
- **D-07:** Vietnamese delivery docs live under `docs/` while `README.md` stays the primary operator/evaluator entry point that links to the deeper documents.
- **D-08:** Scanner guidance and templates are supportive evidence, not replacements for business-logic tests. Semgrep, dependency audits, image scans, Burp, AWVS, and DAST must be documented as complementary layers.
- **D-09:** Final limitation documentation must explicitly cover prototype limits, external provider dependencies, Google grounding retention constraints, Windows/Docker caveats, and features intentionally not implemented.

### Historical Accuracy
- **D-10:** Phase 3 planning debt remains visible. Phase 6 may verify the shipped search behavior that exists in code, but it must not rewrite history or silently claim a clean dependency-order planning trail that the repo does not contain.
- **D-11:** Phase 5 is treated as verified and complete for downstream planning, because `05-VERIFICATION.md` passed on 2026-06-17 and UAT is complete.

### the agent's Discretion
- Choose whether phase evidence runners are PowerShell, Python, or mixed, as long as they are Windows-friendly in this repo and call the real Compose topology.
- Choose the exact split between README content and dedicated `docs/*.md` files, as long as the README remains a truthful entrypoint and deeper topics move into dedicated Vietnamese docs.
- Choose whether scanner instructions live in one guide or several focused guides, as long as TEST-08 and DOCS-04 are covered without overstating what scanners prove.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and Requirements
- `.planning/ROADMAP.md` - Defines the Phase 6 goal, requirements, and success criteria.
- `.planning/REQUIREMENTS.md` - Defines `TEST-01` through `TEST-10` and `DOCS-01` through `DOCS-06`.
- `.planning/STATE.md` - Records the current project focus and the unresolved Phase 3 planning debt.
- `.planning/PROJECT.md` - Defines the core value, Compose-first delivery model, and Vietnamese documentation constraint.

### Prior Phase Evidence
- `.planning/phases/05-gateway-administration-and-security-evidence/05-VERIFICATION.md` - Current authoritative verification of Phase 5.
- `.planning/phases/05-gateway-administration-and-security-evidence/05-UAT.md` - Completed human checks for OAuth, gateway evidence, and documentation truthfulness.
- `.planning/phases/04-isolated-python-execution/04-VERIFICATION.md` - Verified Python isolation evidence.
- `.planning/phases/03-policy-controlled-google-search/03-VERIFICATION.md` - Stale planning artifact that must stay visible as historical debt.

### Research and Risk Guidance
- `.planning/research/SUMMARY.md` - High-level recommended final-evidence shape.
- `.planning/research/PITFALLS.md` - Concrete adversarial pitfalls and required proof patterns.
- `.planning/research/FEATURES.md` - Documentation and evaluator-delivery expectations.

### Existing Test and Runtime Surfaces
- `backend/tests/integration/` - Existing auth/chat/search/python/gateway/admin integration coverage.
- `backend/tests/security/` - Existing policy, redaction, search, and sandbox security tests.
- `backend/tests/smoke/` - Existing assembled-topology smoke tests.
- `frontend/tests/` - Existing auth, readiness, workspace, search, Python, and admin UI tests.
- `compose.yaml` and `compose.test.yaml` - Current topology and test topology entry points.
- `README.md` and `.env.example` - Current Vietnamese operator guidance and environment contract.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- The repo already has broad backend coverage for registration, login, OAuth, chat CRUD, search routing, search grounding, Python orchestration, gateway policies, and admin evidence.
- `backend/tests/security/test_secret_leakage.py` and `backend/tests/security/test_search_secret_leakage.py` already establish canary-secret regression patterns.
- `backend/tests/smoke/` already covers topology, admin flow, Google Search flow, Python flow, OAuth, and logging.
- `README.md` is already Vietnamese and covers the operator path, but the deeper architecture/security/testing/runbook split required by Phase 6 is still missing.

### Missing Phase-6-Specific Surfaces
- There is no `security-tests/` directory yet, so the attack-suite deliverable is still absent.
- There is no `docs/` directory yet, so the dedicated Vietnamese architecture, security, testing, runbook, and limitations documents are still absent.
- There is no phase-level attack runner, evidence pack index, or final Phase 6 verification artifact.

### Integration Points
- Phase 6 should treat the current backend/frontend test suites as the source of truth for product behavior and then add missing gap tests or orchestration runners only where the roadmap still lacks proof.
- Attack scripts should exercise the live Compose topology through public routes first, and then use bounded database or evidence inspection helpers only when a side-effect assertion cannot be observed safely from HTTP alone.
- Documentation must stay truthful to the current code and planning state, including the search-planning inconsistency that still exists in `.planning/phases/03-policy-controlled-google-search/`.

</code_context>

<specifics>
## Specific Ideas

- Split Phase 6 into five plans:
  - `06-01`: automated verification matrix and gap closure
  - `06-02`: adversarial attack scripts under `security-tests/`
  - `06-03`: scanner guidance, evidence templates, and report conventions
  - `06-04`: Vietnamese README, architecture, and security docs
  - `06-05`: Vietnamese testing, runbook, limitations docs, plus final verification closeout
- Keep all final evidence runnable from the repo root on Windows with Docker Compose.
- Use the final verification artifact to map every `TEST-*` and `DOCS-*` requirement to executable or inspectable evidence.

</specifics>

<deferred>
## Deferred Ideas

- New product functionality unrelated to proof or documentation.
- Rewriting the historical Phase 3 planning trail instead of documenting the debt honestly.

</deferred>

---

*Phase: 6-Adversarial Verification and Vietnamese Delivery*
*Context gathered: 2026-06-19*
