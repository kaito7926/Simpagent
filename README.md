# SimpAgent

SimpAgent là prototype môn học về chatbot SaaS có định hướng an toàn. Ở trạng thái hiện tại, repo tập trung hoàn thành Phase 1: nền tảng chạy cục bộ, đăng ký/đăng nhập, phiên refresh an toàn, giao diện Next.js tiếng Việt, Kong gateway DB-less, PostgreSQL và sandbox Python health-only.

## Mục tiêu repo

- Chứng minh một luồng tài khoản an toàn: register -> login -> me -> refresh/logout.
- Giữ backend là ranh giới ủy quyền chính thức.
- Chuẩn bị nền cho các phase sau: chat riêng tư, Google Search có kiểm soát, Python sandbox, admin/audit, tài liệu và security verification.

## Công nghệ đang dùng

- Frontend: Next.js 16, React 19, TypeScript, CSS token cục bộ.
- Backend: FastAPI, SQLAlchemy 2, Alembic, PostgreSQL.
- Gateway: Kong OSS DB-less.
- Sandbox: container Python health-only.
- Test: pytest, Node test runner qua `tsx`, Docker Compose.

## Cấu trúc chính

- `frontend/` — giao diện Phase 1 account access.
- `backend/` — API auth/session/readiness, migration, CLI provisioning.
- `kong/` — cấu hình gateway DB-less.
- `sandbox/` — nền sandbox health-only.
- `.planning/` — roadmap, requirements, state và toàn bộ artifact GSD.

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

### 4. Tài khoản demo phát triển

Khi Compose chạy ở chế độ development hiện tại, job seed sẽ tạo 2 tài khoản demo:

- User: `demo.user@simpagent.test`
- Admin: `demo.admin@simpagent.test`

Mật khẩu mẫu nằm trong `.env.example` và chỉ dùng để demo cục bộ.

## Lệnh kiểm thử quan trọng

### Backend

```bash
docker compose -f compose.test.yaml run --rm backend-test pytest -q
```

### Full backend suite trên topology chính

```bash
docker compose run --rm backend python -m pytest -q
```

### Frontend tests

```bash
docker compose run --rm frontend npm run test -- tests/auth-session.test.ts tests/readiness.test.ts
```

### Frontend typecheck

```bash
docker compose run --rm frontend npm run typecheck
```

### Migration drift check

```bash
docker compose run --rm backend alembic check
```

## Góp ý và cộng tác theo GSD

Repo này nên được làm theo workflow GSD để tránh lệch plan, lệch phase và lệch artifact.

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
Đọc .planning/STATE.md, ROADMAP.md và phase 1 plans.
Chỉ làm trong scope plan 01-08.
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

## Trạng thái hiện tại

Phase 1 đã có:

- backend auth/session/readiness foundation
- frontend account-access flow tiếng Việt
- demo provisioning CLI/jobs
- compose topology với Kong + PostgreSQL + sandbox
- test suite backend/frontend ở mức Phase 1

## Việc nên làm tiếp theo

- Dùng `.planning/ROADMAP.md` để xác định phase kế tiếp.
- Nếu tiếp tục Phase 1, hãy tạo summary/verification/tracking artifact còn thiếu theo GSD.
- Nếu chuyển sang Phase 2, bắt đầu bằng `/gsd-plan-phase 2` hoặc `/gsd-execute-phase 2` sau khi review context.
