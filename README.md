# SimpAgent

SimpAgent là prototype môn học về chatbot SaaS có định hướng an toàn. Trạng thái hiện tại của repo đã ghép các lát chính của sản phẩm: đăng nhập local, OAuth Google/GitHub, chat riêng tư, Google Search có kiểm soát, Python sandbox, Kong gateway, observability, admin evidence đã redact, và hồ sơ vận hành nhỏ cho khoảng 100 người dùng/tháng.

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
- Sandbox: supervisor và runtime Python container tách khỏi backend, chạy với giới hạn tài nguyên và không có network mặc định.
- Observability: Grafana Loki + Promtail + Tempo + provisioned dashboards for backend logs/traces.
- Test: pytest, Node test runner qua `tsx`, Docker Compose.

## Cấu trúc chính

- `frontend/` — giao diện account access và chat/search shell.
- `backend/` — API auth, admin, conversations, search worker, logging, migration, provisioning.
- `kong/` — cấu hình gateway DB-less.
- `observability/` — Loki, Tempo, Promtail, Grafana provisioning.
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
- Với LLM provider cho local development, backend hỗ trợ cả `LLM_API_KEY` trực tiếp từ `.env`/environment và `LLM_API_KEY_FILE`; nếu cả hai cùng được set thì giá trị biến môi trường được ưu tiên.
- Tương tự, Google Gemini / Search worker hỗ trợ cả `GOOGLE_API_KEY` trực tiếp từ `.env`/environment và `GOOGLE_API_KEY_FILE`; nếu cả hai cùng được set thì giá trị biến môi trường được ưu tiên.
- OAuth Google/GitHub dùng các biến `SIMPAGENT_GOOGLE_CLIENT_ID`, `SIMPAGENT_GOOGLE_CLIENT_SECRET`, `SIMPAGENT_GOOGLE_REDIRECT_URI`, `SIMPAGENT_GITHUB_CLIENT_ID`, `SIMPAGENT_GITHUB_CLIENT_SECRET`, và `SIMPAGENT_GITHUB_REDIRECT_URI`. Secret thật không được ghi vào README, `.env.example`, log, hoặc prompt gửi model.

### 3. Khởi động toàn hệ thống

```bash
docker compose up --build --wait
```

Public entrypoint mặc định:

- App/Kong: `http://localhost:8000`
- Grafana: `http://localhost:3001` (`admin` / `admin`)

Ghi chú topology Compose hiện tại:

- `backend` vẫn nằm trên mạng `private` để nói chuyện với `postgres`, `kong` và các service nội bộ.
- `backend` đồng thời được nối thêm vào mạng `egress` không-internal để có thể gọi LLM provider bên ngoài internet.
- `frontend` và `kong` tiếp tục dùng mạng `public` để phục vụ truy cập từ máy host.
- Local Compose là đường chạy chính để demo: `Client -> Kong -> FastAPI -> PostgreSQL/LLM/Tools`.
- Đường edge tùy chọn là `Client -> Cloudflare -> Kong -> FastAPI -> PostgreSQL/LLM/Tools`; Cloudflare không bắt buộc cho demo local.

### 3.1. Bối cảnh triển khai hiện tại

- Repo hiện được đóng khung theo bối cảnh self-hosted/internal-first: chạy trên máy dev, lab, hoặc server nhỏ do chính operator kiểm soát; không giả định multi-node hay public SaaS mặc định.
- Ở profile local mặc định, chỉ `kong` và `grafana` publish cổng ra host. `postgres`, `backend`, `sandbox`, `loki`, `tempo`, và `promtail` ở lại trong mạng Compose để giảm bề mặt phơi lộ.
- Nếu cần public ingress thì đặt thêm edge phía trước Kong, ví dụ Cloudflare/Tunnel. Đây là lớp tùy chọn bên ngoài; repo hiện vẫn giả định single-node và trusted proxy được khai báo đúng.

### 4. Tài khoản demo phát triển

Khi Compose chạy ở chế độ development hiện tại, job seed sẽ tạo 2 tài khoản demo:

- User: `demo.user@simpagent.test`
- Admin: `demo.admin@simpagent.test`

Mật khẩu mẫu nằm trong `.env.example` và chỉ dùng để demo cục bộ.

## Hồ sơ vận hành Phase 5 cho small-production

Hồ sơ `small-production` trong `compose.yaml` là mẫu cấu hình cho triển khai nhỏ, không phải cam kết production đầy đủ. Mục tiêu là giúp operator nhìn rõ các biến môi trường, secret file, origin công khai, cookie secure, OAuth redirect và trusted proxy khi chạy prototype khoảng 100 người dùng/tháng.

Ví dụ kiểm tra cấu hình:

```bash
docker compose --profile small-production config -q
```

Các nguyên tắc bắt buộc:

- `docker compose up --build` vẫn là đường local chính.
- `SIMPAGENT_APP_ENV=production` yêu cầu HTTPS origin chính xác, `SIMPAGENT_COOKIE_SECURE=true`, `SIMPAGENT_DEMO_SEED_ENABLED=false`, file secret cho database/JWT/refresh/CSRF/Python capability, và `SIMPAGENT_TRUSTED_PROXY_CIDRS`.
- `SIMPAGENT_PUBLIC_APP_ORIGIN` là origin frontend người dùng mở trong trình duyệt; với local Compose qua Kong nên đặt `http://localhost:8000`, còn triển khai production dùng origin HTTPS public của app. `SIMPAGENT_PUBLIC_API_ORIGIN` là origin API/Kong public dùng cho OAuth callback.
- Local Compose hiện bật `SIMPAGENT_COOKIE_SECURE=true` để giữ contract `__Host-` cookie và cho browser chấp nhận refresh/CSRF cookie trên `localhost` qua cổng 8000. Nếu browser mục tiêu không chấp nhận Secure localhost cookies, cần chuyển sang local TLS thay vì tắt Secure.
- OAuth redirect nên trỏ về backend-owned callback: `/api/auth/oauth/google/callback` và `/api/auth/oauth/github/callback`.
- Kong chỉ là lớp ingress coarse-grained. FastAPI vẫn tự validate token, role, scope, ownership và tool policy.
- Kong Admin API, PostgreSQL, sandbox control plane và search worker không được expose ra host/public internet.

### Cloudflare tùy chọn

Nếu đặt Cloudflare phía trước Kong, đường đi mong muốn là:

```text
Client -> Cloudflare -> Kong -> FastAPI -> PostgreSQL/LLM/Tools
```

Khuyến nghị vận hành:

- Cloudflare Tunnel có thể đưa traffic từ hostname public về Kong proxy `:8000`; không expose Kong Admin API.
- DNS/TLS nên terminate ở Cloudflare và hop từ Tunnel tới Kong nằm trong mạng operator kiểm soát.
- `SIMPAGENT_TRUSTED_PROXY_CIDRS` chỉ nên chứa dải proxy thật sự được tin cậy. Header nguồn IP như `CF-Connecting-IP` chỉ đáng tin khi request đến từ Cloudflare/Tunnel đã kiểm soát.
- WAF managed rules, Bot Fight Mode và Turnstile là lớp giảm abuse tùy chọn; app vẫn phải tự có auth, CSRF, rate limit, gateway limit và authorization.
- Free-plan WAF/Bot features có giới hạn về rule, visibility và tuning. Tài liệu này không tuyên bố enterprise edge protection, HA, distributed rate limiting, hay sandbox production-grade.

### Các lớp an toàn bảo mật hiện có

- Xác thực và phiên: mật khẩu local được băm bằng `pwdlib`/Argon2; access token sống ngắn; refresh token nằm trong cookie `HttpOnly`, `Secure`, `SameSite`; refresh/logout kiểm tra cả `Origin` và CSRF token.
- Ủy quyền fail-closed: FastAPI tự resolve principal và chặn khi role, scope, hoặc trạng thái token không hợp lệ; quyền chat/admin/tool được kiểm tra ở backend kể cả khi request đi qua Kong.
- Biên công cụ tách rời: Google Search dùng capability token RS256 TTL ngắn; Python chỉ chạy qua sandbox supervisor riêng, không `exec` trực tiếp trong backend.
- Giảm rò rỉ dữ liệu: logging redact token/secret/cookie nhạy cảm; admin evidence bị redact trước khi serialize; nội dung chat được mã hóa khi lưu; Markdown UI escape raw HTML thay vì render thẳng.
- Giảm bề mặt mạng và thực thi: Kong Admin API, Postgres và sandbox control plane không expose public; sandbox chạy với timeout, giới hạn CPU/RAM/PID, rootfs read-only và `--network none`; grounding chỉ giữ lại URL web public hợp lệ.

### Migration, bootstrap admin, backup, restore, rollback

Các lệnh dưới đây là runbook operator. Thay biến/secret theo môi trường thật trước khi chạy.

```bash
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python -m app.cli.bootstrap_admin --email admin@example.com
docker compose exec postgres pg_dump -U postgres -d simpagent -Fc -f /tmp/simpagent.dump
docker compose cp postgres:/tmp/simpagent.dump ./backups/simpagent.dump
docker compose cp ./backups/simpagent.dump postgres:/tmp/simpagent.dump
docker compose exec postgres pg_restore -U postgres -d simpagent --clean --if-exists /tmp/simpagent.dump
```

Rollback thực tế của prototype là rollback theo Git commit/tag, khôi phục database từ backup gần nhất, chạy lại migration phù hợp, rồi kiểm tra smoke. Không tự ý sửa tay schema production nếu chưa có migration tương ứng.

## Smoke matrix Phase 5

Trước khi trình diễn hoặc nghiệm thu, chạy stack rồi kiểm tra các đường chính:

```bash
docker compose up --build --wait
docker compose run --rm -e SIMPAGENT_RUN_SMOKE=true backend python -m pytest -q tests/smoke/test_topology.py
docker compose run --rm -e SIMPAGENT_RUN_SMOKE=true backend python -m pytest -q tests/smoke/test_oauth_google_flow.py tests/smoke/test_oauth_github_flow.py
docker compose run --rm -e SIMPAGENT_RUN_SMOKE=true backend python -m pytest -q tests/smoke/test_admin_flow.py
docker compose run --rm -e SIMPAGENT_RUN_SMOKE=true backend python -m pytest -q tests/smoke/test_private_direct_chat.py
docker compose run --rm -e SIMPAGENT_RUN_SMOKE=true backend python -m pytest -q tests/smoke/test_google_search_flow.py
docker compose run --rm -e SIMPAGENT_RUN_SMOKE=true backend python -m pytest -q tests/smoke/test_python_tool_flow.py
docker compose run --rm -e SIMPAGENT_RUN_SMOKE=true backend python -m pytest -q tests/smoke/test_logging_flow.py tests/smoke/test_tracing_flow.py
docker compose run --rm backend python -m pytest -q tests/integration/gateway/test_production_profile.py tests/integration/cli/test_provisioning.py
```

Các smoke trên bao phủ local login, Google OAuth start/readiness, GitHub OAuth start/readiness, auth-shell CTA theo provider readiness, gateway routing, admin evidence, chat, Search, Python, và observability log-to-trace correlation. OAuth provider thật chỉ hoàn tất end-to-end khi operator đã cấu hình client ID/secret và redirect URI hợp lệ ở Google/GitHub.

## Giới hạn prototype

- Quy mô mục tiêu: khoảng 100 người dùng/tháng, single-node Compose, DB-less Kong với rate limit local.
- Không có HA, rolling deploy, distributed rate limiting, multi-region, hoặc quản lý secret production hoàn chỉnh.
- Cloudflare là edge tùy chọn để minh họa Tunnel/WAF/Turnstile/Bot Fight Mode/TLS/source-IP assumptions; nó không thay thế kiểm soát backend.
- Python sandbox đã tách container và có giới hạn tài nguyên, nhưng chưa phải sandbox production-grade cho mã độc đa tenant trên internet.
- LLM/OpenAI-compatible, Google Search, Google OAuth và GitHub OAuth phụ thuộc credential/provider bên ngoài; khi thiếu credential, readiness có thể degraded/unconfigured thay vì giả lập thành công.

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
- Health check Grafana: `http://localhost:3001/api/health`
- Datasource Loki và Tempo đã được provision sẵn
- Dashboard folder `SimpAgent` có sẵn dashboard `SimpAgent Observability Overview` và `SimpAgent Request Journey`
- Tracing local mặc định bật qua các biến `OTEL_*` trong `.env.example`

Luồng observability hiện tại:

- `backend` xuất JSON logs có `correlation_id`, `trace_id`, `span_id`, `method`, `path`, `status_code`, `duration_ms`
- `backend` export request spans trực tiếp sang Tempo qua OTLP HTTP với `service.name=simpagent-backend`
- Grafana/Loki dùng `trace_id` làm derived field để mở `View trace` sang Tempo ngay từ log backend
- Grafana dashboard mặc định tổng hợp request volume, status code, latency theo path, log volume theo service, và recent request logs
- Dashboard `SimpAgent Request Journey` dùng textbox filter cho `correlation_id` và `path`, rồi drill down sang Tempo từ panel log request
- `backend` ghi thêm các event `security_event` và `tool_execution`
- `kong` ghi access/error log vào volume chung để Promtail scrape

Smoke observability:

```bash
docker compose run --rm -e SIMPAGENT_RUN_SMOKE=true backend python -m pytest -q tests/smoke/test_logging_flow.py tests/smoke/test_tracing_flow.py
```

Trạng thái và tự phục hồi stack local:

- Grafana hiện đi cùng Loki + Tempo đã provision sẵn, có dashboard mặc định và health endpoint để kiểm tra nhanh từ host.
- Các service chạy dài hạn (`postgres`, `backend`, `backend-small-production`, `frontend`, `kong`, `loki`, `tempo`, `promtail`, `grafana`, `sandbox`) đã được đặt `restart: unless-stopped` để stack local tự lên lại sau các gián đoạn runtime phổ biến của Docker Desktop/engine.
- Các job một lần như migration/init/seed vẫn không auto-restart để tránh lặp tác vụ ngoài ý muốn.

### Migration drift check

```bash
docker compose run --rm backend alembic check
```

## Trạng thái hiện tại

### Đã có trong repo

- Nền Phase 1: register, login, `/me`, refresh/logout, demo seed, readiness, Kong + PostgreSQL.
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
- Phase 5:
  - Google/GitHub OAuth start/callback dùng cùng refresh-cookie session model với local login
  - Kong hardening cho CORS, correlation ID, request-size và rate-limit evidence
  - admin surfaces cho overview, users, security events, tool executions, gateway evidence và orchestration
  - auth shell hiển thị provider readiness cho Google/GitHub
  - small-production profile, trusted-proxy assumptions và smoke matrix
  - observability local với Grafana dashboards, log-to-trace correlation qua Loki/Tempo, và auto-restart cho các service chạy dài hạn
- Test:
  - backend integration/security cho search, admin, token boundary, guardrails
  - regression test khóa contract `restart: unless-stopped` cho các service Compose chạy dài hạn
  - unit test cho logging và attack detection
  - smoke test cho topology, search, admin, và logging flow
  - rerun đầy đủ ngày 2026-06-13: backend `79 passed, 5 skipped`, frontend search `9 passed`, `typecheck` pass, smoke `5 passed`

## Ghi chú cho AI Agent viết UI chọn công cụ

UI chat nên dùng chính các endpoint chat hiện có và truyền thêm trường tùy chọn `tool_mode` trong message request. Không cần tạo endpoint riêng cho hai nút chọn.

Giá trị hợp lệ:

- `auto` hoặc bỏ trống: backend tự route như hiện tại.
- `google_search`: ép lượt này gọi Web Search Agent nếu tài khoản có `tool:websearch`.
- `python`: ép lượt này gọi Python Sandbox Agent nếu tài khoản có `tool:python`.

Tạo hội thoại kèm message đầu tiên:

```http
POST /api/conversations
{
  "initial_message": {
    "client_message_id": "client-generated-id",
    "content": "Tra cứu thông tin mới nhất cho tôi.",
    "tool_mode": "google_search"
  }
}
```

Gửi message vào hội thoại đã có:

```http
POST /api/conversations/{conversation_id}/messages
{
  "client_message_id": "client-generated-id",
  "content": "Dùng sandbox tính kết quả này.",
  "tool_mode": "python"
}
```

Gợi ý UI:

- Hiển thị hai checkbox/toggle: `Web Search` và `Python Sandbox`, nhưng xử lý như lựa chọn loại trừ nhau vì mỗi lượt chỉ được gọi một tool.
- Nếu không chọn nút nào, gửi `tool_mode: "auto"` hoặc bỏ trường này.
- Nếu chọn `Web Search`, gửi `tool_mode: "google_search"` và tự bỏ chọn `Python Sandbox`.
- Nếu chọn `Python Sandbox`, gửi `tool_mode: "python"` và tự bỏ chọn `Web Search`.
- Có thể đọc `/api/auth/me.scopes` để disable nút thiếu quyền, nhưng backend vẫn là nguồn kiểm tra quyền cuối cùng.
- Response vẫn là `ConversationDetail`; message assistant mới nhất có `metadata.tool_name`, `metadata.tool_status`, và chi tiết trong `metadata.search` hoặc `metadata.python_result`.
- Khi backend trả `metadata.tool_status: "denied"`, UI nên hiển thị trạng thái bị từ chối thay vì retry tự động.

### Đang còn mở

- Phase 3 planning artifacts vẫn cần được reconcile trong `.planning`.
- Phase 6 sẽ bổ sung adversarial verification và tài liệu bàn giao tiếng Việt đầy đủ hơn.

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

- Sau khi Phase 5 đóng, chạy verification/UAT rồi lập **Phase 6: Adversarial Verification and Vietnamese Delivery**.
