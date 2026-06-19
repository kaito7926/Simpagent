# SimpAgent

SimpAgent là prototype chatbot SaaS có định hướng an toàn. Repo này ghép các lát chính đã có trong code hiện tại: local auth, OAuth Google/GitHub, chat riêng tư, Google Search có kiểm soát, Python sandbox, Kong gateway, observability, admin evidence đã redact, và bộ xác minh Phase 6 bằng tiếng Việt.

## Tài liệu chính

- [Kiến trúc](docs/architecture.vi.md)
- [Bảo mật](docs/security.vi.md)
- [Deploy internet nhỏ](docs/deploy-production.vi.md)
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

Biến môi trường mẫu nằm ở `.env.example`. Production override dùng thêm `.env.production.example`.

Lưu ý:

- File mẫu chứa giá trị demo chỉ dành cho môi trường phát triển.
- Secret thật không được commit vào repo, không ghi vào README, `.env.example`, log, hoặc prompt gửi model.
- Nếu không có `LLM_API_KEY`, direct chat sẽ fail-closed hoặc chỉ còn các path không cần provider thật.
- Nếu không có `GOOGLE_API_KEY`, search readiness sẽ degraded/unconfigured thay vì giả thành công.
- Backend đọc các biến `SIMPAGENT_*` trong container; `.env` và `.env.production` dùng host-env key không prefix rồi Compose map sang `SIMPAGENT_*`.
- Với LLM và Google provider, backend hỗ trợ cả secret trực tiếp từ env và `*_FILE`; nếu cả hai cùng được set thì env trực tiếp được ưu tiên.

## Chạy local

```powershell
docker compose up --build --wait
```

Entrypoint local:

- App/Kong: `http://localhost:8000`
- Backend docs trực tiếp: `http://localhost:4000/docs`
- Grafana: `http://localhost:3001`

Demo accounts khi seed dev bật:

- User: `demo.user@simpagent.test`
- Admin: `demo.admin@simpagent.test`

Password mẫu nằm trong `.env.example` và chỉ dùng cho local demo.

## Small-production profile

Repo có hai mức tài liệu production nhỏ để kiểm tra environment contract, không phải claim production-ready đầy đủ:

1. `small-production` profile trong `compose.yaml` là mẫu tham chiếu environment-only.
2. `compose.prod.yaml` + `.env.production.example` là override đầy đủ hơn cho topology single-node nhỏ trên các service hiện có.

Cả hai chỉ nhắm đến prototype khoảng 100 người dùng/tháng.

### Kiểm tra profile tham chiếu

```powershell
docker compose --profile small-production config -q
```

### Runbook cho production override

```powershell
Copy-Item .env.production.example .env.production
docker compose --env-file .env.production -f compose.yaml -f compose.prod.yaml config -q
docker compose --env-file .env.production -f compose.yaml -f compose.prod.yaml up -d --build
```

Chi tiết từng bước, cách tạo `secrets-prod/`, bootstrap admin, kiểm tra CORS/health, và rollback nằm ở [Deploy internet nhỏ](docs/deploy-production.vi.md).

Trước khi chạy, chỉnh tối thiểu trong `.env.production`:

- `ALLOWED_ORIGINS`
- `PUBLIC_APP_ORIGIN`
- `PUBLIC_API_ORIGIN`
- `TRUSTED_PROXY_CIDRS`

Tạo `./secrets-prod/` và đặt tối thiểu:

- `postgres_password`
- `database_url`
- `jwt_private_key`
- `jwt_public_key`
- `refresh_hmac_key`
- `csrf_hmac_key`
- `registration_invite_code`
- `python_capability_secret`

Nếu dùng provider thật, thêm:

- `llm_api_key`
- `google_api_key`

Smoke/health sau khi stack lên:

```powershell
docker compose --env-file .env.production -f compose.yaml -f compose.prod.yaml ps
docker compose --env-file .env.production -f compose.yaml -f compose.prod.yaml logs -f kong backend frontend
docker compose --env-file .env.production -f compose.yaml -f compose.prod.yaml exec kong curl -fsS http://127.0.0.1:8000/health
docker compose --env-file .env.production -f compose.yaml -f compose.prod.yaml exec backend curl -fsS http://127.0.0.1:8000/ready
```

Bootstrap admin đầu tiên:

```powershell
docker compose --env-file .env.production -f compose.yaml -f compose.prod.yaml run --rm backend python -m app.cli.bootstrap_admin --email admin@example.com
```

Các nguyên tắc bắt buộc:

- `docker compose up --build` vẫn là đường local chính; `compose.prod.yaml` dành cho operator muốn bám topology production nhỏ mà không sửa `compose.yaml` gốc.
- `.env.production` dùng key host-env không prefix như `APP_ENV`, `COOKIE_SECURE`, `DEMO_SEED_ENABLED`, `ALLOWED_ORIGINS`, `PUBLIC_APP_ORIGIN`, `PUBLIC_API_ORIGIN`, `TRUSTED_PROXY_CIDRS`.
- `kong/kong.prod.yml` phải dùng origin CORS khớp với `ALLOWED_ORIGINS`.
- Kong chỉ là ingress coarse-grained. FastAPI vẫn tự validate token, role, scope, ownership và tool policy.
- Kong Admin API, PostgreSQL, sandbox control plane và search worker không được expose ra host/public internet.
- Cloudflare/Tunnel có thể dùng làm edge minh họa, nhưng trusted proxy CIDR phải là dải thật sự kiểm soát.

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

### Smoke topology đầy đủ

```powershell
docker compose up --build --wait
docker compose run --rm -e SIMPAGENT_RUN_SMOKE=true backend python -m pytest -q tests/smoke
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
