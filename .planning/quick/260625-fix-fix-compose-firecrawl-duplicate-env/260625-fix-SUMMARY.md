---
status: complete
quick_id: 260625-fix
completed: 2026-06-25
---

# Quick Task 260625-fix Summary

Đã sửa lỗi Compose không parse được do duplicate mapping key:

- Xoá cụm `SIMPAGENT_FIRECRAWL_API_KEY`, `SIMPAGENT_FIRECRAWL_API_KEY_FILE`, `SIMPAGENT_FIRECRAWL_API_BASE` bị lặp lần hai trong `compose.yaml`.
- Dọn bản sao các field `websearch_provider`/`firecrawl_*` trong `backend/app/core/config.py`; giữ lại một khai báo có `AliasChoices` đầy đủ cho biến `SIMPAGENT_*` và biến rút gọn.

## Verification

- `docker compose config --quiet`: passed.
- `rg` xác nhận backend development service chỉ còn một cụm Firecrawl API env; production profile vẫn giữ cấu hình riêng của nó.

