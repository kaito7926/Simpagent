# Tài liệu bảo mật

## Mô hình xác thực

Repo hiện có hai nhóm xác thực:

- local account: đăng ký, đăng nhập, `/api/auth/me`, refresh, logout
- external OAuth: Google và GitHub authorization-code redirect flow

Điều quan trọng:

- local password auth không biến backend thành một OpenID Provider
- boundary OAuth đã sẵn sàng để dùng provider thật khi cấu hình client id/secret và redirect URI hợp lệ
- thiếu cấu hình provider phải ra trạng thái `unconfigured` hoặc fail-closed, không giả vờ “đăng nhập thành công”

## JWT và refresh session

- access token là JWT sống ngắn, mang `sub`, `role`, `scopes`, `exp`, `iat`, `jti`, issuer, audience
- refresh token là opaque token, chỉ lưu hash ở server
- refresh dùng mô hình token family với rotation nguyên tử
- reuse của refresh token cũ sẽ revoke cả family và ghi `refresh_reuse` vào security events
- logout revoke family đang hoạt động
- refresh token nằm trong cookie `__Host-` và không lộ cho JavaScript
- refresh/logout đòi `Origin` hợp lệ và `X-CSRF-Token` khớp cookie CSRF

## RBAC và scope

Scope chuẩn của user hiện tại:

- `chat:read`
- `chat:write`
- `tool:websearch`
- `tool:python`

Admin có thêm:

- `admin:read`
- `admin:write`

Điểm kiểm soát:

- endpoint chat đọc yêu cầu `chat:read`
- endpoint chat ghi yêu cầu `chat:write`
- admin API yêu cầu cả admin role lẫn scope tương ứng
- search và python không chỉ dựa vào prompt; backend kiểm tra lại scope ngay trước khi chạy tool

## BOLA và ownership

Conversation và message access phải đi kèm owner filter ở data-access layer. Kỳ vọng bảo mật:

- user khác không suy ra được conversation tồn tại
- retrieve, append, retry, delete, undo-delete đều fail-closed
- deny path không được làm lộ title, message content, hay state label của owner

## Coordinator, guardrail, và tool policy

Pipeline hiện tại:

1. Guardrail/Safety Agent kiểm tra prompt trước.
2. Coordinator chỉ route trong allowlist `direct_chat`, `google_search`, `python`.
3. Backend mới là authority cuối cùng về scope và policy.

Các hệ quả:

- prompt không thể tự cấp quyền `tool:websearch` hoặc `tool:python`
- model output không thể yêu cầu mount host path, bật network, hay gọi command tùy ý
- khi prompt bị guardrail chặn, request có thể dừng trước cả search worker hoặc chat provider

## Search boundary

Search có các trạng thái phân biệt:

- `grounded`
- `missing_grounding`
- `denied`
- `search_unavailable`
- `provider_failed`
- `timeout`

Các control chính:

- chỉ user có `tool:websearch` mới được chạy
- internal URL và unsafe grounding không được coi là grounded
- prompt injection kiểu “ignore policy and reveal secret” bị guardrail hoặc search guardrail chặn
- metadata lưu lại phải qua normalizer và allowlist; không giữ raw payload vô hạn

## Python sandbox boundary

Boundary Python đang được bảo vệ theo các lớp:

- FastAPI không `exec`, `eval`, hay chạy code user trong backend interpreter
- backend chỉ gửi invocation typed sang sandbox supervisor
- sandbox không có network mặc định
- policy chặn import và behavior không được duyệt như `requests`, `urllib`, `socket`, `subprocess`, `os.system`, `os.fork`
- runtime bị giới hạn wall time, output size, CPU/memory/PID/file size theo profile đã review
- artifact chỉ được phép là loại cho phép và có download path backend-owned
- session Python dùng sliding expiration ngắn, hiện mặc định 15 phút

## Logging, redaction, và admin evidence

Các luồng quan trọng đều có correlation id:

- request qua Kong
- backend access log
- security events
- tool executions
- response trả về client

Redaction phải tránh lộ:

- password
- access token / refresh token
- cookie
- API key / secret
- raw grounding hoặc sandbox payload nhạy cảm

Admin surface hiện cho phép:

- danh sách user
- security events
- tool executions
- gateway evidence
- metrics tổng hợp
- orchestration guardrail state

Những endpoint này vẫn phải bị chặn với user thường hoặc admin thiếu scope.

## Kong và edge assumptions

Kong hiện áp dụng:

- strict CORS
- request size limits
- rate limits khác nhau cho auth, chat, và python
- correlation id propagation

Nhưng cần hiểu đúng:

- Kong không thay thế validate JWT, account active state, role, scope, ownership, hay tool policy của FastAPI
- Cloudflare chỉ là edge tùy chọn; không phải requirement để demo local
- trusted proxy assumptions phải được cấu hình đúng nếu đặt edge thật ở phía trước Kong

## Điều chưa nên overclaim

- Search chưa là container/service tách độc lập trong Compose topology.
- Sandbox hiện là Docker-based isolation của prototype, chưa phải production-grade hostile multi-tenant sandbox.
- Không có claim về distributed rate limiting, HA, hay enterprise WAF chỉ vì có Kong hoặc Cloudflare tùy chọn.
