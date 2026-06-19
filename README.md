# SimpAgent

SimpAgent là prototype chatbot SaaS có định hướng an toàn. Repo này ghép các lát chính đã có trong code hiện tại: local auth, OAuth Google/GitHub, chat riêng tư, Google Search có kiểm soát, Python sandbox, Kong gateway, observability, admin evidence đã redact, và bộ xác minh Phase 6 bằng tiếng Việt.

## Tài liệu chính

- [Kiến trúc](docs/architecture.vi.md)
- [Bảo mật](docs/security.vi.md)
- [Kiểm thử](docs/testing.vi.md)
- [Runbook](docs/runbook.vi.md)
- [Giới hạn](docs/limitations.vi.md)
- [Security tests](security-tests/README.md)

## Stack hiện tại

- Frontend: Next.js 16, React 19, TypeScript
- Backend: FastAPI, SQLAlchemy 2, Alembic, PostgreSQL
- Gateway: Kong OSS DB-less
- Search: backend-owned search service boundary gọi Google Search provider khi được cấu hình
- Sandbox: container supervisor riêng cho Python
- Observability: Loki, Promtail, Grafana
- Test: pytest, `tsx --test`, PowerShell runners

## Tính năng đã có

- Đăng ký, đăng nhập, refresh rotation, logout, `/api/auth/me`
- Google OAuth và GitHub OAuth start/callback fail-closed khi thiếu cấu hình
- Conversation riêng tư với list, retrieve, send, retry, delete, undo-delete
- Guardrail + coordinator allowlist cho `direct_chat`, `google_search`, `python`
- Search state rõ ràng: `grounded`, `missing_grounding`, `denied`, `search_unavailable`, `provider_failed`, `timeout`
- Python sandbox có policy, capability token, sliding session TTL ngắn, và artifact download path backend-owned
- Kong CORS, correlation id, request-size limits, rate limits
- Admin evidence cho users, security events, tool executions, gateway evidence, metrics

## Chuẩn bị môi trường

Cần có:

- Docker Desktop đang chạy
- PowerShell trên Windows
- Node 22+ nếu muốn chạy frontend ngoài container
- Python 3.13 nếu muốn chạy backend ngoài container

Biến môi trường mẫu nằm ở `.env.example`.

Lưu ý:

- Secret thật không được commit vào repo.
- Nếu không có `LLM_API_KEY`, direct chat sẽ fail-closed hoặc chỉ còn các path không cần provider thật.
- Nếu không có `GOOGLE_API_KEY`, search readiness sẽ degraded/unconfigured thay vì giả thành công.

## Chạy local

```powershell
docker compose up --build --wait
```

Entrypoint local:

- App/Kong: `http://localhost:8000`
- Grafana: `http://localhost:3001`

Demo accounts khi seed dev bật:

- User: `demo.user@simpagent.test`
- Admin: `demo.admin@simpagent.test`

Password mẫu nằm trong `.env.example` và chỉ dùng cho local demo.

## Small-production profile

Repo có profile cấu hình nhỏ để kiểm tra environment contract, không phải claim production-ready đầy đủ:

```powershell
docker compose --profile small-production config -q
```

Khi dùng profile này:

- phải cung cấp secret file thật
- phải có public origin / redirect URI đúng
- phải giữ `COOKIE_SECURE=true`
- phải cấu hình trusted proxy đúng nếu đặt edge thật ở phía trước Kong

## API surface chính

Route chính hiện được expose qua Kong:

- `/api/auth/*`
- `/api/auth/oauth/*`
- `/api/conversations`
- `/api/conversations/{id}/messages`
- `/api/conversations/{id}/turns`
- `/api/python/artifacts/{id}`
- `/api/admin/*`
- `/health`
- `/ready`

FastAPI Swagger/OpenAPI không được publish qua Kong public route trong topology hiện tại. Route contract được giữ trong code, test, và tài liệu tiếng Việt này.

## Kiểm thử nhanh

### Backend test topology

```powershell
docker compose -f compose.test.yaml run --rm backend-test pytest -q
```

### Frontend tests

```powershell
docker compose run --rm frontend npm test --
```

### Frontend typecheck

```powershell
docker compose run --rm frontend npm run typecheck
```

### Phase 6 matrix

```powershell
powershell -ExecutionPolicy Bypass -File security-tests/run-phase6-matrix.ps1
```

### Phase 6 attacks

```powershell
powershell -ExecutionPolicy Bypass -File security-tests/run-phase6-attacks.ps1
```

## Security features cần hiểu đúng

- Kong chỉ là ingress và coarse filter; FastAPI mới là authority cuối cùng cho token, role, scope, ownership, và tool policy.
- Refresh token dùng family rotation; replay sẽ revoke cả family.
- BOLA phải fail-closed với conversation/message routes.
- Search hiện là service boundary trong backend, chưa là container riêng.
- Python sandbox là boundary container riêng, nhưng vẫn là Docker-based prototype isolation chứ chưa phải hostile multi-tenant production sandbox.
- Admin evidence đã được redact; ordinary user và under-scoped admin không được đọc.

## Những giới hạn nổi bật

- Single-node Compose, khoảng 100 user/tháng
- Không có HA, distributed rate limiting, MFA, password reset, email verification
- Search / chat / OAuth phụ thuộc provider thật nếu muốn chạy end-to-end
- Phase 3 planning debt vẫn còn trong `.planning`; Phase 6 chỉ làm rõ bằng chứng và tài liệu, không xóa lịch sử đó
- Runner Phase 6 trên Windows phải dùng `subst` tạm để tránh lỗi Docker Compose với đường dẫn Unicode

Chi tiết xem thêm ở [Giới hạn](docs/limitations.vi.md).
