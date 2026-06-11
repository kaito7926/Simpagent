# SimpAgent

SimpAgent là prototype môn học về chatbot SaaS có định hướng an toàn. Trạng thái hiện tại của repo không còn dừng ở nền Phase 1 nữa: nền tảng xác thực/phiên vẫn là lớp cơ sở, còn nhánh làm việc hiện nay tập trung vào **Phase 3: Policy-Controlled Google Search** cùng các phần hỗ trợ như admin evidence, logging tập trung, và smoke test topology đầy đủ.

## Mục tiêu repo

- Chứng minh một hệ chatbot có thể xác thực, phân quyền, và chạy công cụ dưới ràng buộc rõ ràng.
- Giữ FastAPI là ranh giới ủy quyền và thực thi chính thức, kể cả khi Kong hoặc worker thực hiện coarse screening.
- Tách riêng biên quyền giữa direct chat, Google Search, và Python sandbox.
- Cung cấp đủ evidence, test, và tài liệu để trình diễn các kiểm soát an toàn trong môi trường Docker Compose cục bộ.

## Công nghệ đang dùng

- Frontend: Next.js 16, React 19, TypeScript, CSS token cục bộ.
- Backend: FastAPI, SQLAlchemy 2, Alembic, PostgreSQL.
- Gateway: Kong OSS DB-less.
- Search worker: Google ADK + Gemini search boundary.
- Sandbox: container Python health-only ở nhánh hiện tại.
- Observability: Grafana Loki + Promtail + backend JSON logs.
- Test: pytest, Node test runner qua `tsx`, Docker Compose.

## Cấu trúc chính

- `frontend/` — giao diện account access và chat/search shell.
- `backend/` — API auth, admin, conversations, search worker, logging, migration, provisioning.
- `kong/` — cấu hình gateway DB-less.
- `observability/` — Loki, Promtail, Grafana provisioning.
- `sandbox/` — nền sandbox health-only, chờ Phase 4.
- `.planning/` — roadmap, requirements, state, phase artifacts, quick-task artifacts theo GSD.

## Chạy dự án

### 1. Chuẩn bị

Cần có:

- Docker Desktop + Docker Compose
- Node 22+ nếu muốn chạy frontend ngoài container
- Python 3.13 nếu muốn chạy backend ngoài container

### 2. Môi trường

Dùng file mẫu:

- `D:\ADMIN\Documents\matmahoc\@DO_AN\Simpagent\.env.example`

Lưu ý:

- File mẫu chứa giá trị demo chỉ dành cho môi trường phát triển.
- Secret production thật phải đi qua file secret hoặc biến môi trường riêng, không commit vào repo.

### 3. Khởi động toàn hệ thống

```bash
docker compose up --build --wait
```

Public entrypoint mặc định:

- App/Kong: `http://localhost:8000`
- Grafana: `http://localhost:3001` (`admin` / `admin`)

### 4. Tài khoản demo phát triển

Khi Compose chạy ở chế độ development hiện tại, job seed sẽ tạo 2 tài khoản demo:

- User: `demo.user@simpagent.test`
- Admin: `demo.admin@simpagent.test`

Mật khẩu mẫu nằm trong `.env.example` và chỉ dùng để demo cục bộ.

## Lệnh kiểm thử quan trọng

### Backend suite trong topology test

```bash
docker compose -f compose.test.yaml run --rm backend-test pytest -q
```

### Full backend suite trên topology chính

```bash
docker compose run --rm backend python -m pytest -q
```

### Frontend tests

```bash
docker compose run --rm frontend npm run test -- tests/search-session.test.ts tests/search-rendering.test.tsx
```

### Frontend typecheck

```bash
docker compose run --rm frontend npm run typecheck
```

### Smoke test topology đầy đủ

```bash
docker compose up --build --wait
docker compose run --rm -e SIMPAGENT_RUN_SMOKE=true backend python -m pytest -q tests/smoke
```

Nếu muốn ép smoke search ở trạng thái grounded hoặc degraded cụ thể, đặt thêm `SIMPAGENT_EXPECT_SEARCH_STATE`.

### Kiểm tra observability cục bộ

Sau khi `docker compose up --build --wait`, mở:

- Grafana: `http://localhost:3001`
- Datasource Loki đã được provision sẵn

Luồng log hiện tại:

- `backend` xuất JSON logs có `correlation_id`, `method`, `path`, `status_code`, `duration_ms`
- `backend` ghi thêm các event `security_event` và `tool_execution`
- `kong` ghi access/error log vào volume chung để Promtail scrape

### Migration drift check

```bash
docker compose run --rm backend alembic check
```

## Trạng thái hiện tại

### Đã có trong repo

- Nền Phase 1: register, login, `/me`, refresh/logout, demo seed, readiness, Kong + PostgreSQL + sandbox health-only.
- Backend Phase 3:
  - `/api/conversations/{conversation_id}/turns` với state matrix rõ ràng cho `direct_chat` và `google_search`
  - dedicated Google Search worker boundary, grounding normalizer, capability token, provider capability check
  - admin endpoints cho users, security events, tool executions, metrics, cùng nhánh `admin:write`
  - JSON logging, correlation-aware access log, Loki/Promtail/Grafana stack
  - deterministic attack-detection rule pack để chuẩn bị cho Phase 4
- Frontend Phase 3:
  - `/chat` shell tối thiểu
  - controller cho mode switch, retry, suggestion prefill
  - grounded/degraded rendering contract cho search
- Test:
  - backend integration/security cho search, admin, token boundary, guardrails
  - unit test cho logging và attack detection
  - smoke test cho topology, search, admin, và logging flow

### Đang còn mở

- Verify full assembled topology bằng Docker Compose trong một phiên có `docker` khả dụng.
- Chốt phase-level verification/closeout artifact cho Phase 3.
- Bắt đầu cắm attack-detection vào runtime Python execution khi sang Phase 4.

## Góp ý và cộng tác theo GSD

Repo này nên được làm theo workflow GSD để tránh lệch plan, lệch phase, và lệch artifact.

### Luồng làm việc khuyến nghị cho 3 người

- Người 1: frontend/UI và interaction
- Người 2: backend/API/database/auth
- Người 3: verification, compose, docs, security checks

Không nhất thiết khóa cứng vai trò, nhưng mọi thay đổi nên bám phase và plan.

### Quy tắc cộng tác

1. Không code thẳng khi chưa đọc `.planning/` liên quan.
2. Mỗi task nên bám đúng phase hiện tại hoặc một gap được tạo từ verification.
3. Không tự ý mở rộng scope sang phase sau.
4. Không commit secret thật, token, private key, password production.
5. Khi sửa backend/frontend, luôn chạy test liên quan trước khi push.

## Dùng Coding Agent đúng cách

### Bắt đầu từ đâu

Trước khi yêu cầu Coding Agent làm việc, hãy đọc:

- `D:\ADMIN\Documents\matmahoc\@DO_AN\Simpagent\.planning\ROADMAP.md`
- `D:\ADMIN\Documents\matmahoc\@DO_AN\Simpagent\.planning\REQUIREMENTS.md`
- `D:\ADMIN\Documents\matmahoc\@DO_AN\Simpagent\.planning\STATE.md`
- phase đang làm trong `D:\ADMIN\Documents\matmahoc\@DO_AN\Simpagent\.planning\phases\`

### Các lệnh GSD nên dùng

- `/gsd-execute-phase <phase>` — khi đang thực thi phase đã có plan
- `/gsd-debug` — khi có bug/test fail
- `/gsd-quick` — khi chỉ sửa nhỏ, dọn mã, chỉnh docs ngắn
- `/gsd-progress` — xem tiến độ phase/milestone
- `/gsd-plan-phase <phase>` — nếu phase chưa có plan hoặc cần tạo gap plan
- `/gsd-code-review <phase>` — rà soát mã sau khi hoàn tất phase

### Prompt mẫu cho Coding Agent

```text
Đọc .planning/STATE.md, ROADMAP.md và phase 3 plans.
Chỉ làm trong scope phase 03 hiện tại.
Sau khi sửa xong, chạy test liên quan và báo các file đã đổi.
```

### Khi nào cần tạo plan/gap mới

- Khi verification phát hiện thiếu requirement
- Khi test chỉ ra scope hiện tại chưa đủ để pass
- Khi muốn thêm tính năng phase sau: không chen vào phase hiện tại, hãy plan phase mới

## Quy ước branch và commit

- Giữ commit nhỏ, có ý nghĩa.
- Ưu tiên commit theo đơn vị hành vi hoặc plan.
- Không bypass hook nếu chưa hiểu nguyên nhân fail.
- Trước khi push, kiểm tra lại `git status` để tránh đẩy artifact ngoài ý muốn.

## Việc nên làm tiếp theo

- Chạy assembled smoke thật trên Docker Compose với `SIMPAGENT_RUN_SMOKE=true`.
- Chốt verification cho Phase 3 rồi cập nhật phase status trong `.planning/`.
- Nếu tiếp tục sang nhánh Python execution, bắt đầu bằng `/gsd-plan-phase 4`.
