# Phase 03 Plan 03-04 Summary

## Kết quả

Đã harden search path trước prompt injection, retention drift, và failure-state collapse; đồng thời bổ sung smoke path qua topology công khai để kiểm tra grounded/degraded flow và các evidence bám `correlation_id`.

## Thay đổi chính

- Hoàn thiện persistence và failure-state semantics cho grounded, missing-grounding, denied, unavailable, provider-failed, timeout, và retry.
- Thêm/hoàn thiện các test `test_search_persistence.py`, `test_search_failure_states.py`, `test_search_prompt_injection.py`, `test_search_secret_leakage.py`, `test_search_retention_allowlist.py`, và `test_google_search_flow.py`.
- Trong cùng nhánh Phase 3, bổ sung admin RBAC/evidence, JSON logging + Loki/Promtail/Grafana, deterministic attack-detection rule pack, và smoke test topology cho admin/search/logging để việc verify assembled stack thực tế hơn.

## Kiểm chứng

- `$env:SIMPAGENT_DATABASE_URL='postgresql+psycopg://postgres:postgres@127.0.0.1:55432/simpagent_test'; python -m pytest tests/integration/search/test_search_persistence.py tests/integration/search/test_search_failure_states.py tests/security/test_search_prompt_injection.py tests/security/test_search_secret_leakage.py tests/security/test_search_retention_allowlist.py tests/security/test_search_capability_token.py -q --tb=short`
- `python -m pytest tests/smoke -q --tb=short`

## Ghi chú

- Trong shell hiện tại, smoke suite chỉ verify ở mức collection/skip vì chưa chạy assembled Compose topology với `SIMPAGENT_RUN_SMOKE=true`.
- Full phase closeout vẫn cần một lượt `docker compose up --build --wait` + smoke/admin/search/logging verification trong topology thật.
