# Runbook vận hành và phản ứng sự cố

## 1. Brute-force hoặc rate-limit abuse

Nhận biết:

- `429` từ Kong ở `/api/auth/login`
- admin hoặc operator thấy tăng bất thường ở gateway evidence / logs

Xử lý:

- xác nhận có phải local test hợp lệ hay không
- giữ nguyên rate-limit config hiện tại trong `kong/kong.yml` nếu behavior đúng
- nếu có false positive ảnh hưởng demo, kiểm tra lại thứ tự chạy attack suite và credential đang dùng

Xác minh lại:

```powershell
powershell -ExecutionPolicy Bypass -File security-tests/attacks/invoke-brute-force.ps1
```

## 2. Refresh replay

Nhận biết:

- `session_invalid` khi refresh
- security event `refresh_reuse`

Xử lý:

- coi toàn bộ refresh family tương ứng là không tin cậy
- buộc user đăng nhập lại
- kiểm tra xem replay đến từ test có chủ đích hay từ thao tác client bất thường

Xác minh lại:

```powershell
powershell -ExecutionPolicy Bypass -File security-tests/attacks/invoke-refresh-replay.ps1
```

## 2.1. DPoP / sender-constrained proof mismatch

Nhận biết:

- protected API trả `invalid_dpop_proof`
- refresh/logout trả `session_invalid` dù CSRF và refresh cookie còn tồn tại
- security event `dpop_proof_replay` hoặc `dpop_key_mismatch`

Xử lý:

- coi access token hoặc refresh cookie bị copy là không đủ để khôi phục session
- buộc user đăng nhập lại để tạo browser-held proof key mới
- kiểm tra correlation id, `family_id`, `expected_key_thumbprint`, và `presented_key_thumbprint`; không cần và không được log raw DPoP proof JWT
- nếu lỗi xảy ra hàng loạt sau deploy frontend, kiểm tra đường dẫn tạo proof, CORS header `DPoP`, và origin dùng trong `htu`

Khi mất khóa trình duyệt:

- user có thể thấy session expired sau reload, xóa site data, hoặc đổi browser profile
- đây là behavior đúng: không degrade về bearer-only
- hướng dẫn user đăng nhập lại; không copy cookie/access token thủ công để “sửa nhanh”

Xác minh lại:

```powershell
docker compose -f compose.test.yaml run --rm --build backend-test python -m pytest -q tests/integration/auth/test_session_flow.py tests/security/test_jwt_profile.py -x
```

## 3. Nghi ngờ BOLA hoặc ownership bypass

Nhận biết:

- user báo thấy conversation không phải của mình
- route `/api/conversations/*` trả dữ liệu không đúng owner

Xử lý:

- dừng demo chia sẻ account
- kiểm tra deny-path ở integration/security test
- review query ownership trong backend trước khi sửa UI hay Kong

Xác minh lại:

```powershell
powershell -ExecutionPolicy Bypass -File security-tests/attacks/invoke-bola.ps1
```

## 4. Prompt injection hoặc tool abuse

Nhận biết:

- prompt kiểu “ignore policy”, “reveal secret”, “disable guardrail”
- tool execution bất thường

Xử lý:

- kiểm tra guardrail đang bật
- xem `tool_executions` và `security_events` với correlation id tương ứng
- nếu prompt đi qua mà không bị chặn, ưu tiên vá guardrail/policy thay vì chỉnh response text

Xác minh lại:

```powershell
powershell -ExecutionPolicy Bypass -File security-tests/attacks/invoke-guardrail-abuse.ps1
```

## 5. Sandbox abuse hoặc escape probe

Nhận biết:

- python result `policy_error`
- tool execution status `policy_error` hoặc `limit_reached`
- operator nghi ngờ có network/process/file side effect bất thường

Xử lý:

- kiểm tra log sandbox và backend
- xác nhận container runtime không bị chạy với cấu hình ngoài reviewed profile
- nếu sửa `sandbox/runtime/`, rebuild image và rerun matrix trước khi tin kết quả

Xác minh lại:

```powershell
powershell -ExecutionPolicy Bypass -File security-tests/attacks/invoke-python-escape.ps1
```

## 6. SSRF hoặc internal reachability probe

Nhận biết:

- prompt hoặc code cố gọi `localhost`, `127.0.0.1`, private IP, metadata IP, hoặc service nội bộ

Xử lý:

- xác nhận deny-path ở python/search policy
- kiểm tra không có artifact hay response body lộ data nội bộ
- nếu probe đi qua, coi đó là blocker bảo mật cao

Xác minh lại:

```powershell
powershell -ExecutionPolicy Bypass -File security-tests/attacks/invoke-ssrf-probe.ps1
```

## 7. Provider outage hoặc credential thiếu

Nhận biết:

- readiness `degraded` hoặc provider `unconfigured`
- chat/search/OAuth không hoàn tất do thiếu credential

Xử lý:

- xác nhận `.env` hoặc secret file đã được mount đúng
- không giả lập thành công trong docs hay demo
- với local demo không cần provider thật, tập trung vào fail-closed behavior và route contract

## 7.1. OAuth PKCE / transaction replay

Nhận biết:

- OAuth callback trả lỗi `oauth_state_invalid`
- security event `oauth_transaction_replay` hoặc `oauth_transaction_invalid`

Xử lý:

- yêu cầu user bắt đầu lại flow Google/GitHub từ nút đăng nhập
- không tái sử dụng URL callback cũ hoặc code cũ
- kiểm tra clock, cookie state, và redirect URI nếu lỗi xuất hiện với mọi provider

## 8. Secret exposure

Nhận biết:

- log, admin evidence, API response, hoặc artifact chứa token / password / API key / canary

Xử lý:

- dừng chia sẻ log dump đó
- thay secret liên quan nếu là secret thật
- review redaction logic và evidence sanitizer
- rerun canary-secret tests trước khi tiếp tục demo

Xác minh lại:

```powershell
docker compose -f compose.test.yaml run --rm backend-test python -m pytest -q tests/security/test_secret_leakage.py tests/security/test_search_secret_leakage.py
```

## 9. Quan sát và log

- Grafana: `http://localhost:3001`
- Loki đã được provision sẵn qua Promtail
- Backend log JSON gồm `correlation_id`, `method`, `path`, `status_code`, `duration_ms`
- Kong access/error log được scrape vào cùng stack observability

Khi điều tra, luôn ghi lại correlation id trước rồi mới đối chiếu response, tool execution, và security events.
