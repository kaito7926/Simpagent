# Phase 03 Plan 03-01 Summary

## Kết quả

Đã triển khai contract backend đầu tiên cho search turn với state matrix trung thực, route conversation chuyên biệt, và lớp persistence đủ để frontend phân biệt rõ direct chat, denied, missing-grounding, unavailable, timeout, và grounded.

## Thay đổi chính

- Thêm `backend/app/api/routes/conversations.py` và đăng ký route trong backend API.
- Thêm schema typed cho turn request/response tại `backend/app/schemas/chat.py` và `backend/app/schemas/search.py`.
- Triển khai `ChatTurnsService` với allowlist mode rõ ràng, deny trước provider call, lifecycle metadata, và persisted tool execution có `correlation_id`.
- Thêm repository/domain support cho conversation, message, tool execution và metadata search.
- Thêm test backend cho search authz, explicit turn routing, grounding honesty, và guardrails nền.

## Kiểm chứng

- `$env:SIMPAGENT_DATABASE_URL='postgresql+psycopg://postgres:postgres@127.0.0.1:55432/simpagent_test'; python -m pytest tests/integration/search/test_search_authz.py tests/integration/search/test_turn_routing.py tests/integration/search/test_grounding_contract.py tests/security/test_search_guardrails.py -q --tb=short`

## Ghi chú

- Nhánh `direct_chat` hiện vẫn là placeholder tối thiểu để giữ explicit mode contract trong khi roadmap Phase 2 chưa được backfill summary theo cùng định dạng.
