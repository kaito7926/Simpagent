---
status: complete
quick_task: 260611-rv4
description: develop attack simulation code detection rule structure
completed: 2026-06-11
---

## Result

Added a deterministic attack-simulation code detection package for the backend security layer, with reusable rule definitions and scan results that can fail closed before future Python execution flows.

## Changes

- Added `backend/app/security/attack_detection/` with `schemas.py`, `rules.py`, and `engine.py`.
- Defined a default rule pack covering reverse shells, internal-target SSRF, secret exfiltration, sensitive host files, container-escape primitives, and privilege-escalation indicators.
- Exported `scan_attack_simulation` and related rule/result types through `app.security`.
- Added `backend/tests/unit/test_attack_detection.py` to lock malicious-vs-benign behavior and multi-signal thresholds.

## Verification

- `cd backend && python -m pytest tests/unit/test_attack_detection.py -q --tb=short`
- `cd backend && python -m pytest tests/unit/test_attack_detection.py tests/security/test_jwt_profile.py tests/security/test_search_capability_token.py -q --tb=short`

## Notes

- Phase 3 does not yet have a live Python execution path, so this quick task delivers the rule engine and tests without wiring runtime blocking into a sandbox endpoint.
- The exported API is ready to plug into future code-submission, moderation, or audit flows.
