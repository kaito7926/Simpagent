---
phase: 06-adversarial-verification-and-vietnamese-delivery
plan: "02"
subsystem: adversarial-verification
tags: [phase-06, security-tests, attacks, replay, bola, ssrf, guardrail, kong]

requires:
  - phase: 06-adversarial-verification-and-vietnamese-delivery
    provides: deterministic matrix runner and assembled Compose topology
provides:
  - Repo-owned black-box attack suite for TEST-07
  - Shared PowerShell attack helpers with bounded HTTP, session, evidence, and summary logic
  - Truth-restoring gateway fix so `undo-delete` reaches backend authorization through Kong
affects: [phase-06, security-tests, kong, public-routes]

tech-stack:
  added: []
  patterns:
    - Shared `phase6-common.ps1` session/evidence helpers for all attack scripts
    - Kong restart between scenarios to isolate auth-sensitive local rate-limit counters

key-files:
  created:
    - .planning/phases/06-adversarial-verification-and-vietnamese-delivery/06-02-SUMMARY.md
    - security-tests/README.md
    - security-tests/attacks/invoke-bola.ps1
    - security-tests/attacks/invoke-brute-force.ps1
    - security-tests/attacks/invoke-guardrail-abuse.ps1
    - security-tests/attacks/invoke-python-escape.ps1
    - security-tests/attacks/invoke-refresh-replay.ps1
    - security-tests/attacks/invoke-ssrf-probe.ps1
    - security-tests/lib/phase6-common.ps1
    - security-tests/run-phase6-attacks.ps1
  modified:
    - kong/kong.yml

key-decisions:
  - Attack probes stay limited to the owned local stack and assert denied side effects rather than destructive payload success.
  - The suite resets Kong between scenarios so the auth rate-limit plugin cannot contaminate unrelated probes.

patterns-established:
  - Attack runner emits `security-tests/output/phase6-attacks-summary.json` and fails the whole run on any unexpected allow-path.
  - Public-route verification now includes `undo-delete`, keeping BOLA coverage on the real gateway path instead of a frontend 404 fallback.

requirements-completed: [TEST-07, TEST-09]

duration: "1 session"
completed: 2026-06-19
---

# Phase 06 Plan 02: Black-Box Attack Suite Summary

**Delivered the repo-owned adversarial suite and fixed the last public-route/runtime issues that blocked truthful attack verification.**

## Performance

- **Duration:** 1 session
- **Completed:** 2026-06-19
- **Primary outputs:** attack helpers, six focused probes, runner orchestration, gateway/public-route correction

## Accomplishments

- Added shared helper infrastructure in `security-tests/lib/phase6-common.ps1` for sessions, CSRF/refresh handling, bounded HTTP calls, correlated admin-evidence lookups, and JSON summary output.
- Added six focused attack scripts for refresh replay, two-user BOLA, guardrail abuse, SSRF/internal reachability, Python escape attempts, and brute-force rate limiting.
- Added `security-tests/run-phase6-attacks.ps1` and `security-tests/README.md` so evaluators can run the suite from repo root on Windows.
- Fixed two truth-restoring issues exposed by the live suite: `System.Net.Http` assembly loading in the shared helper, and missing Kong routing for `undo-delete` on the public conversation surface.
- Hardened the runner so admin credentials are passed only to scripts that need them and Kong is restarted between scenarios to clear local auth rate-limit counters.

## Task Commits

No task commits were created during this closeout session. The work remains in the current working tree.

## Files Created/Modified

- `security-tests/lib/phase6-common.ps1` - Added shared session/evidence helpers, Windows-safe Compose handling, and PowerShell HTTP type initialization.
- `security-tests/attacks/*.ps1` - Added six focused adversarial probes.
- `security-tests/run-phase6-attacks.ps1` - Added orchestration, JSON summary output, admin-argument routing, and per-scenario Kong resets.
- `security-tests/README.md` - Added evaluator-facing usage and safety scope guidance.
- `kong/kong.yml` - Added public routing for `/api/conversations/{id}/undo-delete` so attacks hit backend authorization rather than frontend fallback behavior.

## Decisions Made

- A frontend 404 is not sufficient evidence for a BOLA check when the intended backend route exists; the public gateway must expose the route so the suite verifies the real authorization boundary.
- Kong restart is the cleanest way to reset local `rate-limiting` plugin state between probes without widening route limits or weakening the product configuration.
- Refresh/session helpers must gracefully handle both success JSON and error JSON so replay-denial scenarios can be asserted without helper crashes.

## Deviations from Plan

### Auto-fixed Issues

**1. Shared PowerShell helper failed on `System.Net.Http` types**
- **Found during:** first attack-runner execution
- **Issue:** Windows PowerShell did not have the HTTP assembly loaded when the helper created `HttpClientHandler`.
- **Fix:** Added `Add-Type -AssemblyName System.Net.Http` to `phase6-common.ps1`.
- **Verification:** Subsequent attack runs created sessions and completed end-to-end.

**2. The runner passed admin parameters to scripts that do not accept them**
- **Found during:** first attack-runner execution
- **Issue:** `invoke-bola.ps1` and `invoke-brute-force.ps1` failed before exercising the stack.
- **Fix:** Added per-scenario `RequiresAdmin` metadata and splatted only the supported arguments.
- **Verification:** The rerun reached real application behavior instead of failing at PowerShell parameter binding.

**3. The public `undo-delete` route was not proxied through Kong**
- **Found during:** BOLA probe debugging
- **Issue:** The attacker probe hit the Next.js frontend 404 page instead of the backend `conversation_not_found` authorization path.
- **Fix:** Added `~/api/conversations/[^/]+/undo-delete$` to the `backend-chat-turns` Kong route.
- **Verification:** Final BOLA scenario returned five backend 404 denials and the owner reload still succeeded.

**4. Auth-sensitive scenarios contaminated one another through Kong's local rate-limit counters**
- **Found during:** early full-suite reruns
- **Issue:** Later login/register-heavy probes received `429` before reaching the intended control under test.
- **Fix:** The attack runner now restarts Kong and waits for health before each scenario.
- **Verification:** Final attack suite passed all six scenarios without weakening the configured rate-limit policy.

## Verification

- `powershell -ExecutionPolicy Bypass -File security-tests/run-phase6-attacks.ps1 -SkipComposeUp` - all 6 attack scenarios passed and wrote `security-tests/output/phase6-attacks-summary.json`.

## Known Stubs

None introduced by Plan 02. The attack suite is repo-owned, Windows-runnable, and restricted to the local Compose stack.

## Threat Flags

None. The plan corrected gateway truthfulness and runner behavior without granting broader access or disabling protections.

## User Setup Required

Docker Desktop and the Phase 6 main stack must be running. The runner can also bring the stack up itself when `-SkipComposeUp` is omitted.

## Next Phase Readiness

Plan 02 finished with a passing black-box attack suite and a regenerated attack summary artifact. Ready for the scanner/template documentation plans and final closeout.

## Self-Check: PASSED

- Summary file created at `.planning/phases/06-adversarial-verification-and-vietnamese-delivery/06-02-SUMMARY.md`.
- Attack runner exists and passes all six planned scenarios.
- Public gateway route truthfulness for `undo-delete` is restored.
- JSON summary output is generated under `security-tests/output/`.
