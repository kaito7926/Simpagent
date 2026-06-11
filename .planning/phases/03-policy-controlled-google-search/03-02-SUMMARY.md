# Phase 03 Plan 03-02 Summary

## Kết quả

Đã thay seam search giả bằng dedicated Google Search worker boundary, capability token nội bộ ngắn hạn, và lớp capability/provider check để search path chỉ chạy khi cấu hình thực sự hợp lệ.

## Thay đổi chính

- Thêm `backend/app/ai/search_worker/` cho dedicated ADK worker, grounding normalizer, typed reply schema, và service boundary.
- Thêm `backend/app/security/search_capability.py` để mint/validate internal capability token thay cho bearer token của người dùng.
- Mở rộng `backend/app/core/config.py`, `backend/app/core/provider_status.py`, và `backend/app/services/chat_turns.py` cho capability checks, budget enforcement, và startup readiness logic.
- Thêm test cho worker contract, capability check, search budgets, và capability token boundary.

## Kiểm chứng

- `$env:SIMPAGENT_DATABASE_URL='postgresql+psycopg://postgres:postgres@127.0.0.1:55432/simpagent_test'; python -m pytest tests/integration/search/test_search_worker_contract.py tests/integration/search/test_search_capability_check.py tests/integration/search/test_search_budgets.py tests/security/test_search_capability_token.py -q --tb=short`

## Ghi chú

- Search worker vẫn bị ràng buộc chỉ dùng dedicated Google Search boundary; không có Python tool hoặc arbitrary custom tool nào được nối vào cùng agent.
