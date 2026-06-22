# Roadmap: Design a Secure Chatbot Application with Lightweight Agent Capabilities

## Overview

This roadmap delivers the prototype as dependency-ordered vertical slices: establish a runnable security and identity foundation, ship private direct chat, add policy-controlled Google Search, add isolated Python execution, harden the assembled gateway and evidence surfaces, then prove the complete system through adversarial verification and Vietnamese delivery documentation.

**Integrated slice note:** PR #2 ships Phase 4 as an integrated tooling slice. Phase 3 still needs dedicated plans and refreshed verification artifacts before it can be marked complete in strict dependency order.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions marked as INSERTED

- [x] **Phase 1: Secure Platform and Account Access** - The local topology runs and users can authenticate through strict, revocable sessions.
- [x] **Phase 2: Private Direct Chat** - Users can use a safe browser chat experience with owner-only conversation history.
- [ ] **Phase 3: Policy-Controlled Google Search** - Authorized users can receive grounded search answers through a bounded coordinator.
- [x] **Phase 4: Isolated Python Execution** - Authorized users can run bounded Python without host, secret, or network access.
- [x] **Phase 5: Final Product Hardening, OAuth, Gateway, Administration, and Security Evidence** - The assembled application supports local, Google, and GitHub login, hardened ingress, redacted observability, protected admin evidence, and a small production deployment profile. (completed 2026-06-16)
- [ ] **Phase 6: Adversarial Verification and Vietnamese Delivery** - Evaluators can verify the claimed controls and operate the documented prototype.

## Phase Details

### Phase 1: Secure Platform and Account Access

**Goal:** Developers can run the security foundation, and users can create and maintain protected local sessions.
**Mode:** mvp
**Depends on:** Nothing (first phase)
**Requirements:** PLAT-01, PLAT-02, PLAT-03, PLAT-04, PLAT-05, PLAT-06, AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, AUTH-07, AUTH-08, AUTH-09, AUTH-10, AUTHZ-01, AUTHZ-08
**Success Criteria** (what must be TRUE):

  1. Developer can start the required Compose topology, apply the reviewed schema, and distinguish healthy services from dependencies that are not ready.
  2. Operator can configure secrets, providers, origins, models, and security settings without source changes, while missing provider credentials produce a documented closed or degraded state without secret-bearing errors.
  3. User can register and log in without account enumeration, plaintext password handling, or an access token that omits the required strict JWT claims and validation policy.
  4. User can refresh and log out through a JavaScript-inaccessible protected session, while rotated-token reuse revokes the family and is denied.
  5. Authenticated user can inspect their safe identity attributes, while inactive principals and unknown roles, scopes, tools, or policy states fail closed.

**Plans:** 8/8 plans executed
**Wave 1**

- [x] 01-01-PLAN.md - Establish the PostgreSQL-only test, app, and sandbox foundations.

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md - Implement the real PostgreSQL registration/login/current-user API slice.

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 01-03-PLAN.md - Prove the first frontend-to-Kong-to-API-to-PostgreSQL journey.
- [x] 01-04-PLAN.md - Enforce provider-neutral identity, strict JWTs, and fail-closed principals.
- [x] 01-07-PLAN.md - Complete schema, configuration, readiness, and provider degradation.

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 01-05-PLAN.md - Add atomic refresh rotation, replay defense, CSRF, and logout.

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 01-06-PLAN.md - Complete browser session recovery and the account-access UI contract.

**Wave 6** *(blocked on Wave 5 completion)*

- [x] 01-08-PLAN.md - Provision demo/Admin accounts and verify the final assembled topology.

**UI hint:** no

### Phase 2: Private Direct Chat

**Goal:** Users can hold durable direct-LLM conversations in a safe browser interface without crossing ownership boundaries.
**Mode:** mvp
**Depends on:** Phase 1
**Requirements:** AUTHZ-03, AUTHZ-05, AUTHZ-06, CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05, CHAT-06, CHAT-07, CHAT-08, CHAT-09, CHAT-10, CHAT-11
**Success Criteria** (what must be TRUE):

  1. User can register, log in, log out, navigate conversations, compose messages, reload history, and understand pending or retryable error states in the frontend.
  2. User with the required chat scope can create, paginate, retrieve, and delete only their own conversations and cannot infer or alter another user's messages.
  3. User can submit a message once and receive one durably ordered assistant response without retries or duplicate submissions causing duplicate provider work.
  4. Configured OpenAI-compatible chat succeeds within bounded provider behavior, while provider failure creates no fabricated assistant message and returns a stable correlation-bearing error.
  5. Chat works through a correct non-streaming path and renders sanitized Markdown and code without executing raw HTML, scripts, handlers, or dangerous URLs.

**Plans:** 7/7 plans executed
**UI hint:** yes

### Phase 3: Policy-Controlled Google Search

**Goal:** Authorized users can request current information and receive verifiable Google-grounded answers through a coordinator that cannot be overruled by model or tool content.
**Mode:** mvp
**Depends on:** Phase 2
**Requirements:** AUTHZ-04, AUTHZ-07, AGNT-01, AGNT-02, AGNT-03, AGNT-04, AGNT-05, AGNT-06, AGNT-07, SRCH-01, SRCH-02, SRCH-03, SRCH-04, SRCH-05, SRCH-06, SRCH-07, SRCH-08
**Success Criteria** (what must be TRUE):

  1. Authorized user can request Google Search and receive answer text, claim-linked citations, and required Search Suggestions only when live grounding evidence is present.
  2. User can visibly distinguish a successful grounded answer from missing grounding, provider failure, timeout, or an unavailable configured Gemini 2 search capability.
  3. Each turn selects only direct chat, Google Search, or Python from an explicit allowlist and permits at most one invocation within bounded request, output, retry, concurrency, time, and cost budgets.
  4. Model output can propose but cannot authorize a tool; execution rechecks scope and policy and uses a short-lived audience-bound capability instead of the user's bearer token.
  5. Search and Python remain separate typed credential boundaries, every tool decision has a persisted correlated state, and untrusted prompts or search content cannot change policy, expose secrets, fetch internal URLs, or trigger arbitrary actions.

**Plans:** TBD
**UI hint:** yes

### Phase 4: Isolated Python Execution

**Goal:** Authorized users can run bounded Python and receive useful results without granting code access to the backend, host, application network, secrets, or runtime policy.
**Mode:** mvp
**Depends on:** Phase 3
**Requirements:** CHAT-12, SBOX-01, SBOX-02, SBOX-03, SBOX-04, SBOX-05, SBOX-06, SBOX-07, SBOX-08
**Success Criteria** (what must be TRUE):

  1. Authorized user can request Python through the chat workflow and can distinguish the resulting Python-tool response from direct chat and Google-grounded Search.
  2. Submitted code executes only behind the fixed sandbox boundary and cannot use backend or host-process evaluation, shells, interpreters, files, Docker authority, or application secrets.
  3. Sandbox code runs non-root with no network, a read-only root, temporary writable space, dropped capabilities, `no-new-privileges`, seccomp enforcement, and no access to internal or metadata addresses.
  4. User receives bounded stdout, stderr, exit status, duration, and the specific terminating limit when time, CPU, memory, PID, process, file, or output controls stop execution.
  5. Temporary execution data is removed, and package installation, arbitrary external commands, user-controlled runtime settings, mounts, devices, namespaces, and privileged operation are denied.

**Plans:** 5/5 plans executed
**Ship note:** Shipped on PR #2 as an integrated tooling slice. Phase 3 planning and refreshed verification artifacts are still pending in `.planning/phases/03-policy-controlled-google-search/`.
**UI hint:** yes

### Phase 5: Final Product Hardening, OAuth, Gateway, Administration, and Security Evidence

**Goal:** Users can sign in with local credentials, Google, or GitHub, while operators and authorized administrators can run the assembled application through hardened ingress, redacted correlated evidence, and a small production deployment profile sized for about 100 users/month without weakening backend authority.
**Mode:** mvp
**Depends on:** Phase 4
**Requirements:** AUTHZ-02, IDEN-03, IDEN-06, IDEN-07, IDEN-08, GATE-01, GATE-02, GATE-03, GATE-04, GATE-05, GATE-06, GATE-07, GATE-08, OBS-01, OBS-02, OBS-03, OBS-04, OBS-05, OBS-06, OBS-07, PRODREADY-01, PRODREADY-02, PRODREADY-03, PRODREADY-04, PRODREADY-05
**Success Criteria** (what must be TRUE):

  1. Users can authenticate with Google or GitHub through OAuth2/OIDC-safe redirect flows, provider secrets remain environment-only, and OAuth sessions land in the same short-lived JWT plus protected refresh-token model as local email/password login.
  2. OAuth account linking and provisioning prevent account takeover by failing closed on missing, unverified, or conflicting provider email identity and by preserving existing local-account security semantics.
  3. Client traffic reaches only approved application and health routes through DB-less Kong with strict CORS, request-size controls, validated correlation IDs, and tighter useful rate limits on authentication and tool endpoints.
  4. FastAPI remains authoritative for complete token, account, role, scope, ownership, and tool-policy decisions even when Kong performs coarse JWT rejection, and no database, worker control plane, or Kong Admin API is publicly exposed.
  5. Requests, provider calls, tool calls, denials, replay, rate limits, sandbox violations, and administrative actions produce correlated structured evidence with recursive secret and sensitive-content redaction; gateway-only rate-limit evidence is represented through Kong config and verification evidence rather than fabricated admin rows.
  6. Properly scoped administrators can page through bounded users, audits, security events, tool executions, failed logins, rate-limit evidence, aggregate metrics, and orchestration controls, while ordinary and under-scoped users are denied.
  7. Operator can follow a documented small-production deployment profile for about 100 users/month, including Cloudflare-to-Kong routing, trusted-proxy assumptions, secure cookies/origins, migrations, backup/restore, smoke checks, and explicit limits without overclaiming distributed rate limiting, edge protection, or production-grade guarantees.

**Plans:** 8/8 plans complete
**Wave 1**

- [x] 05-02-PLAN.md - Hold the Authlib legitimacy gate inside the Google OAuth implementation plan, then ship the Google OAuth redirect/callback slice.
- [x] 05-04-PLAN.md - Deliver the first real admin slice with Overview and Orchestration surfaces.
- [x] 05-05-PLAN.md - Harden DB-less Kong ingress, correlation handling, and trusted-proxy hooks.

**Wave 2** *(blocked on Wave 1 completion where referenced)*

- [x] 05-03-PLAN.md - Add GitHub OAuth and fail-closed account-linking rules.
- [x] 05-06-PLAN.md - Build recursive redaction and gateway-evidence backend contracts.

**Wave 3** *(blocked on Wave 2 completion where referenced)*

- [x] 05-07-PLAN.md - Wire all six admin evidence surfaces into the shared shell and expose gateway evidence through the admin API.

**Wave 4** *(blocked on Wave 2-3 completion where referenced)*

- [x] 05-09-PLAN.md - Wire the shared Google and GitHub auth-shell CTA/readiness experience.
- [x] 05-08-PLAN.md - Finalize the small-production profile, Cloudflare/trusted-proxy documentation, and assembled smoke coverage.

**UI hint:** no

### Phase 6: Adversarial Verification and Vietnamese Delivery

**Goal:** Evaluators can reproduce the prototype, verify its security properties against the assembled topology, and understand its actual controls and limitations in Vietnamese.
**Mode:** mvp
**Depends on:** Phase 5
**Requirements:** TEST-01, TEST-02, TEST-03, TEST-04, TEST-05, TEST-06, TEST-07, TEST-08, TEST-09, TEST-10, DOCS-01, DOCS-02, DOCS-03, DOCS-04, DOCS-05, DOCS-06
**Success Criteria** (what must be TRUE):

  1. Automated tests prove authentication lifecycle, strict token handling, two-user BOLA denial, role/scope/tool denial, chat ordering and idempotency, provider failure behavior.
  2. Automated search and sandbox tests prove grounding contracts, prompt-injection resistance, time and resource limits, network and host denial, cleanup, and escape resistance through side-effect assertions.
  3. Evaluator can run attack scripts against the Compose topology and observe denied brute force, token replay, SSRF, BOLA, prompt/tool abuse, and sandbox escape attempts without forbidden side effects.
  4. Evaluator has practical SAST, dependency, container, Burp, AWVS, and DAST guidance plus a finding template and canary-secret evidence showing protected values do not leak.
  5. Vietnamese setup, architecture, trust-boundary, security, testing, incident-response, external-data-flow, and limitation documentation matches the implemented system and avoids unsupported production claims.

**Plans:** TBD
**UI hint:** no

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6

Note: PR #2 ships the Phase 4 Python slice before Phase 3 planning metadata was closed out. The table below reflects shipped code status, not strict dependency-order documentation completeness.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Secure Platform and Account Access | 8/8 | Complete | 2026-06-10 |
| 2. Private Direct Chat | 7/7 | Complete | 2026-06-12 |
| 3. Policy-Controlled Google Search | 0/TBD | Artifact closeout pending | - |
| 4. Isolated Python Execution | 5/5 | Shipped (PR #2) | 2026-06-13 |
| 5. Final Product Hardening, OAuth, Gateway, Administration, and Security Evidence | 8/8 | Complete   | 2026-06-16 |
| 6. Adversarial Verification and Vietnamese Delivery | 0/TBD | Not started | - |
