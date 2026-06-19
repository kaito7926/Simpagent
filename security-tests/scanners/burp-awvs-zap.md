# Burp, AWVS, And ZAP

## Safe scope

- Scope mặc định: `http://localhost:8000`
- Không thêm domain thật, IP public, callback OAuth thật, hay metadata endpoint thật vào scope.
- Nếu stack chạy sau Cloudflare thật hoặc tunnel thật, Phase 6 vẫn chỉ scan local route do operator sở hữu.

## Auth strategy

Ứng dụng dùng:

- access token trả về trong body JSON của `/api/auth/login`
- refresh/CSRF cookie kiểu `__Host-`

Thực tế scan thuận tiện nhất là:

1. Tạo user scan riêng hoặc dùng demo account local.
2. Gọi `POST /api/auth/login`.
3. Lấy `access_token` từ body.
4. Gắn `Authorization: Bearer <token>` cho API scan.

Với browser/manual flow trong Burp:

- Dùng Repeater/Proxy để login trước.
- Tạo session handling rule hoặc macro nếu muốn refresh token tự động.
- Không bắt buộc scan OAuth Google/GitHub end-to-end nếu evaluator không có credential provider thật; chỉ cần xác nhận start/callback fail-closed và không lộ secret.

## Burp Suite

Checklist gợi ý:

- Spider hoặc crawl `http://localhost:8000`
- Manual test các route:
  - `/api/auth/login`
  - `/api/auth/refresh`
  - `/api/auth/me`
  - `/api/conversations`
  - `/api/conversations/{id}/messages`
  - `/api/conversations/{id}/turns`
  - `/api/python/artifacts/{id}`
  - `/api/admin/*`
- Active Scan chỉ trong local scope.
- Thử matrix input:
  - broken JWT / stale JWT
  - thiếu scope
  - cross-user conversation id
  - oversized body
  - correlation id sai format

## AWVS

- Chỉ scan target local stack.
- Tắt mọi profile hoặc plugin hướng ra internet.
- Đánh dấu authenticated scan bằng header bearer token.
- Đối với findings về CORS, cookie, rate limit, cần đối chiếu lại với `kong/kong.yml` và test matrix trước khi kết luận.

## ZAP

Baseline scan:

```powershell
docker run --rm -t -v "${PWD}:/zap/wrk" ghcr.io/zaproxy/zaproxy:stable zap-baseline.py -t http://host.docker.internal:8000 -r zap-baseline.html
```

API/authenticated scan cần header bearer token hoặc context file riêng của evaluator.

## Không được bỏ qua

- Scanner DAST có thể báo ít issue dù BOLA hoặc replay logic sai.
- Ngược lại, scanner cũng có thể báo noisy finding cho endpoint đã fail-closed bởi backend hoặc gateway.
- Mọi finding dùng để kết luận Phase 6 nên được đối chiếu với runner attack/matrix và ghi lại theo `finding-template.md`.
