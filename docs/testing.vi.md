# Kiểm thử và xác minh

## Nguyên tắc

Phase 6 dùng nhiều lớp bằng chứng:

- unit / integration / security tests cho contract và deny-path
- smoke tests cho topology ghép thật
- attack scripts trong `security-tests/`
- scanner guidance cho SAST, dependency, image, và DAST

Scanner chỉ là lớp bổ sung. Những control như BOLA, refresh replay, guardrail, và sandbox deny-path phải được chứng minh bằng test hoặc attack runner, không chỉ bằng report scanner.

## Runner chính

### Matrix runner

```powershell
powershell -ExecutionPolicy Bypass -File security-tests/run-phase6-matrix.ps1
```

Runner này map các requirement:

- `TEST-01`
- `TEST-02`
- `TEST-03`
- `TEST-04`
- `TEST-05`
- `TEST-06`
- `TEST-09`
- `TEST-10`

Nó dùng cả `compose.test.yaml` lẫn main Compose stack để chạy subset backend, frontend, và smoke phù hợp.

### Attack runner

```powershell
powershell -ExecutionPolicy Bypass -File security-tests/run-phase6-attacks.ps1
```

Runner này cover `TEST-07` với các scenario:

- brute-force login rate limit
- refresh replay
- BOLA giữa hai user
- prompt/tool abuse bị guardrail chặn
- SSRF/internal reachability bị python policy chặn
- sandbox escape probe bị policy chặn

## Lệnh hữu ích riêng lẻ

### Full backend trên test topology

```powershell
docker compose -f compose.test.yaml run --rm backend-test pytest -q
```

### Full backend trên topology chính

```powershell
docker compose run --rm backend python -m pytest -q
```

### Frontend tests

```powershell
docker compose run --rm frontend npm test --
```

### Frontend typecheck

```powershell
docker compose run --rm frontend npm run typecheck
```

### Smoke subset cần observability

```powershell
docker compose up --build --wait
docker compose run --rm -e SIMPAGENT_RUN_SMOKE=true backend python -m pytest -q tests/smoke/test_logging_flow.py
```

## Scanner guidance

Chi tiết copy-pasteable nằm ở:

- `security-tests/scanners/README.md`
- `security-tests/scanners/semgrep.md`
- `security-tests/scanners/dependency-and-image.md`
- `security-tests/scanners/burp-awvs-zap.md`

Những tool chính Phase 6 kỳ vọng evaluator biết cách chạy:

- Semgrep
- `pip-audit`
- `npm audit`
- Trivy config / image
- Burp Suite
- AWVS
- ZAP

Ghi chú:

- Bandit có thể dùng như Python-only lint bổ sung, nhưng repo này ưu tiên Semgrep vì cover được cả Python lẫn TypeScript và rule packs phong phú hơn.
- Kết quả scanner nên được tóm tắt bằng `security-tests/templates/finding-template.md`, không nên commit toàn bộ raw dump môi trường.

## Quy ước lưu evidence

- Output do runner sinh ra: `security-tests/output/phase6-*.json`
- Output scanner do evaluator sinh ra: `security-tests/output/scanners/...`
- Index tổng hợp: `security-tests/templates/evidence-index-template.md`

## Cách đọc pass/fail

- `matrix` fail: có regression ở contract, deny-path, secret redaction, hoặc smoke evidence.
- `attacks` fail: có allow-path hoặc side effect cấm trong topology local.
- `scanner` fail: chỉ là tín hiệu cần triage; chưa đủ để kết luận repo không pass Phase 6 nếu chưa đối chiếu với behavior thật.
