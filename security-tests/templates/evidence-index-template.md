# Evidence Index Template

| Timestamp | Tool / Runner | Requirement | Command | Output Path | Result | Notes |
|-----------|---------------|-------------|---------|-------------|--------|-------|
| 2026-06-19T00:00:00Z | `run-phase6-matrix.ps1` | `TEST-01` | `powershell -ExecutionPolicy Bypass -File security-tests/run-phase6-matrix.ps1` | `security-tests/output/phase6-matrix-summary.json` | pass/fail | |
| 2026-06-19T00:00:00Z | `run-phase6-attacks.ps1` | `TEST-07` | `powershell -ExecutionPolicy Bypass -File security-tests/run-phase6-attacks.ps1` | `security-tests/output/phase6-attacks-summary.json` | pass/fail | |
| 2026-06-19T00:00:00Z | `semgrep` | `TEST-08` | `pipx run semgrep ...` | `security-tests/output/scanners/semgrep/report.json` | pass/fail | |
| 2026-06-19T00:00:00Z | `pip-audit` | `TEST-08` | `pipx run pip-audit --path backend` | `security-tests/output/scanners/pip-audit/backend.json` | pass/fail | |
| 2026-06-19T00:00:00Z | `trivy` | `TEST-08` | `trivy config ...` | `security-tests/output/scanners/trivy/` | pass/fail | |
| 2026-06-19T00:00:00Z | `Burp/AWVS/ZAP` | `TEST-08` | evaluator-specific | `security-tests/output/scanners/` | pass/fail | |

## Usage

- Thay mỗi dòng mẫu bằng output thật của evaluator.
- Nếu tool nào không chạy được trong môi trường hiện tại, ghi rõ blocker thay vì bỏ trống.
- Link finding chi tiết bằng `finding-template.md` cho các item cần triage sâu hơn.
