---
status: complete
quick_id: 260625-fix
created: 2026-06-25
---

# Quick Task 260625-fix Plan

Fix lỗi `docker compose up --build --wait` bị dừng ở bước parse YAML vì các biến môi trường Firecrawl bị khai báo trùng trong `compose.yaml`.

## Tasks

1. Xác định cụm key bị trùng trong Compose.
2. Giữ một bộ cấu hình Firecrawl duy nhất cho backend development service.
3. Dọn bản sao tương ứng trong cấu hình backend để tránh shadow field.
4. Verify bằng `docker compose config --quiet`.

