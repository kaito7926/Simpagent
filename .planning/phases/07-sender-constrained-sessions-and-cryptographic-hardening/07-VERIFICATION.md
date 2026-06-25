---
phase: 07-sender-constrained-sessions-and-cryptographic-hardening
verified: 2026-06-25T23:18:20+07:00
status: passed
score: 4/4 must-haves verified, manual review passed
overrides_applied: 0
human_verification:
  source: user manual review and test
  completed: 2026-06-25T23:18:20+07:00
  passed: true
---

# Phase 7: Sender-Constrained Sessions and Cryptographic Hardening Verification Report

**Phase Goal:** Browser sessions, OAuth redirect artifacts, and internal capability boundaries become proof-of-possession or one-time cryptographic credentials so copied web-session material cannot be replayed as an unofficial API backend.
**Verified:** 2026-06-25T23:18:20+07:00
**Status:** passed
**Re-verification:** Yes - targeted backend and frontend checks were rerun after implementation, and manual review/testing passed before shipping.

## Goal Achievement

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Protected browser auth/session flows no longer rely only on reusable bearer material when DPoP is enabled. | VERIFIED | `backend/app/security/dpop.py`, `backend/app/authorization/principal.py`, `backend/app/services/sessions.py`, and `frontend/lib/auth-session.ts` enforce and attach proof material; backend auth tests passed. |
| 2 | Google and GitHub OAuth flows use PKCE S256 and sealed one-time provider-bound transactions before code exchange. | VERIFIED | `backend/app/security/oauth_transaction.py`, OAuth provider adapters, and route tests passed for PKCE challenge/verifier and replay denial. |
| 3 | Search and Python tool capabilities are audience-bound, asymmetric or one-time trust artifacts rejected on replay. | VERIFIED | Search worker consumes capability `jti` values through the replay journal; Python sandbox verifies backend-issued RS256 JWTs with a public key; replay tests passed. |
| 4 | Security evidence and Vietnamese rollout docs describe DPoP, PKCE, key-loss re-auth, and remaining limits truthfully. | VERIFIED | `docs/security.vi.md`, `docs/runbook.vi.md`, and `docs/limitations.vi.md` include Phase 7 rollout and limitation language; doc grep confirmed coverage. |

**Score:** 4/4 truths verified

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Backend auth, OAuth, DPoP, replay, and capability hardening suite | `docker compose -f compose.test.yaml run --rm --build backend-test python -m pytest -q tests/integration/auth/test_session_flow.py tests/security/test_jwt_profile.py tests/security/test_search_capability_token.py tests/security/test_python_request_hardening.py tests/integration/auth/test_oauth_flows.py tests/integration/auth/test_google_oauth.py tests/integration/auth/test_github_oauth.py tests/unit/test_oauth_state_cookie.py -x` | 37 passed, 1 skipped | PASS |
| Frontend auth-session and OAuth CTA regression suite | `npm test -- --runInBand tests/auth-session.test.ts tests/account-access-oauth.test.tsx` in `frontend/` | 10 passed | PASS |
| Frontend TypeScript check | `npm run typecheck` in `frontend/` | passed | PASS |
| Vietnamese rollout documentation coverage | `rg -n "DPoP|PKCE|sender-constrained|proof|re-auth|WebAuthn" docs/security.vi.md docs/runbook.vi.md docs/limitations.vi.md` | expected matches found in all three docs | PASS |
| Human review and manual test | User confirmed manual test/review pass on 2026-06-25 | passed | PASS |

## Requirements Coverage

| Requirement | Status | Evidence |
| --- | --- | --- |
| AUTH-11 | SATISFIED | DPoP proof validation, `cnf.jkt` access-token binding, frontend proof headers, and proof-loss re-auth behavior. |
| AUTH-12 | SATISFIED | Refresh-family sender binding, replay journal foundations, and mismatch/replay evidence. |
| IDEN-09 | SATISFIED | OAuth PKCE S256 and sealed one-time provider-bound transaction records. |
| AGNT-08 | SATISFIED | Search capability replay consumption through the shared replay journal. |
| AGNT-09 | SATISFIED | Python sandbox capability verification uses backend-issued RS256 JWTs and public-key validation. |
| OBS-08 | SATISFIED | Replay, mismatch, OAuth transaction, and capability denial evidence is recorded without logging raw secrets or proof material. |
| PRODREADY-06 | SATISFIED | Vietnamese rollout/runbook/limitations docs cover DPoP, PKCE, key loss, and WebAuthn deferral. |

## Human Verification

The user completed manual review and testing after Phase 7 implementation and reported that everything worked well enough to ship.

| Check | Result | Evidence |
| --- | --- | --- |
| Manual app behavior review | PASS | User confirmation in the shipping request on 2026-06-25. |
| Manual production-readiness review for this small hardening phase | PASS | User confirmation that this phase can be shipped to production. |

## Gaps Summary

No active Phase 7 ship blocker remains.

Known non-blocking notes:

- The Phase 7 requirement IDs are not present in the local `.planning/REQUIREMENTS.md` matrix, so traceability is recorded through plan summaries and this verification report.
- The backend test image still skips the static Kong config check from `tests/security/test_jwt_profile.py` because gateway files are outside that container context.
- WebAuthn step-up and multi-device session management remain explicitly deferred beyond this MVP phase.

---

_Verified: 2026-06-25T23:18:20+07:00_
_Verifier: agent rerun of targeted checks plus user-confirmed manual review_
