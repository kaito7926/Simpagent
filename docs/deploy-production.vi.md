# Hướng dẫn deploy internet nhỏ

Tài liệu này dành cho topology single-node trong `compose.prod.yaml`, phù hợp demo/prototype khoảng 100 user/tháng. Mặc định production dùng **một HTTPS origin** cho cả frontend và API, ví dụ `https://simpagent.example.com`. Không tách `app.example.com` và `api.example.com` nếu chưa đổi lại chiến lược cookie/API base, vì frontend đang gọi `/api/...` relative và refresh cookie dùng prefix `__Host-*`.

## 1. Chuẩn bị host

- Cài Docker Engine/Compose v2.
- Đặt reverse proxy, tunnel, hoặc load balancer public terminate HTTPS phía trước Kong.
- Chỉ expose public origin HTTPS; không expose PostgreSQL, backend direct port, Kong Admin API, sandbox, Loki, hoặc Grafana.
- Nếu dùng Cloudflare/Tunnel, ghi lại CIDR edge thật để đặt `TRUSTED_PROXY_CIDRS`.

## 2. Tạo file môi trường production

```powershell
Copy-Item .env.production.example .env.production
```

Sửa tối thiểu trong `.env.production`:

- `ALLOWED_ORIGINS=https://ten-mien-that-cua-ban`
- `PUBLIC_APP_ORIGIN=https://ten-mien-that-cua-ban`
- `PUBLIC_API_ORIGIN=https://ten-mien-that-cua-ban`
- `JWT_ISSUER=ten-mien-that-cua-ban`
- `TRUSTED_PROXY_CIDRS=<CIDR proxy/tunnel/load balancer thật>`
- `LLM_API_BASE`, `LLM_MODEL`
- OAuth redirect URI nếu bật Google/GitHub OAuth

Sửa `kong/kong.prod.yml` để CORS origin khớp chính xác với `ALLOWED_ORIGINS`.

## 3. Tạo secret production

Không commit thư mục này.

```powershell
New-Item -ItemType Directory -Force secrets-prod | Out-Null

$pgPassword = (openssl rand -hex 32)
Set-Content -NoNewline -Path secrets-prod/postgres_password -Value $pgPassword
Set-Content -NoNewline -Path secrets-prod/database_url -Value "postgresql+psycopg://simpagent:$pgPassword@postgres:5432/simpagent"

openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out secrets-prod/jwt_private_key
openssl rsa -pubout -in secrets-prod/jwt_private_key -out secrets-prod/jwt_public_key

Set-Content -NoNewline -Path secrets-prod/refresh_hmac_key -Value (openssl rand -hex 48)
Set-Content -NoNewline -Path secrets-prod/csrf_hmac_key -Value (openssl rand -hex 48)
Set-Content -NoNewline -Path secrets-prod/python_capability_secret -Value (openssl rand -hex 48)
Set-Content -NoNewline -Path secrets-prod/registration_invite_code -Value (openssl rand -hex 16)
```

Nếu dùng provider thật:

```powershell
Set-Content -NoNewline -Path secrets-prod/llm_api_key -Value "<OPENAI_COMPATIBLE_KEY>"
Set-Content -NoNewline -Path secrets-prod/google_api_key -Value "<GOOGLE_API_KEY>"
```

Mã trong `secrets-prod/registration_invite_code` là mã mời để tạo tài khoản mới. Chỉ gửi mã này cho người được phép đăng ký.

## 4. Kiểm tra cấu hình trước khi chạy

```powershell
docker compose --env-file .env.production -f compose.yaml -f compose.prod.yaml config -q
docker compose --env-file .env.production -f compose.yaml -f compose.prod.yaml config | Select-String "published|POSTGRES_PASSWORD|/var/run/docker.sock|https://"
```

Kỳ vọng:

- Chỉ Kong publish port public.
- Không còn `POSTGRES_PASSWORD: postgres`.
- Sandbox vẫn mount Docker socket trong prototype; nếu public lâu dài, chuyển sang Docker rootless/socket proxy hoặc host sandbox riêng.
- Origin trong Kong và backend khớp domain thật.

## 5. Build và chạy

```powershell
docker compose --env-file .env.production -f compose.yaml -f compose.prod.yaml up -d --build
```

Theo dõi log:

```powershell
docker compose --env-file .env.production -f compose.yaml -f compose.prod.yaml ps
docker compose --env-file .env.production -f compose.yaml -f compose.prod.yaml logs -f kong backend frontend
```

## 6. Bootstrap admin đầu tiên

```powershell
docker compose --env-file .env.production -f compose.yaml -f compose.prod.yaml run --rm backend python -m app.cli.bootstrap_admin --email admin@ten-mien-that-cua-ban
```

Lưu password sinh ra ở nơi an toàn. Không gửi password qua chat, issue, log, hoặc tài liệu.

## 7. Kiểm tra sau deploy

Từ host:

```powershell
curl.exe -fsS https://ten-mien-that-cua-ban/health
curl.exe -fsS https://ten-mien-that-cua-ban/ready
```

Kiểm tra CORS preflight:

```powershell
curl.exe -i -X OPTIONS https://ten-mien-that-cua-ban/api/auth/login `
  -H "Origin: https://ten-mien-that-cua-ban" `
  -H "Access-Control-Request-Method: POST" `
  -H "Access-Control-Request-Headers: Authorization, Content-Type, X-CSRF-Token, X-Correlation-Id"
```

Kiểm tra luồng người dùng:

- Đăng ký bằng invite code.
- Đăng nhập.
- Gửi chat thường.
- Gửi tool Python đơn giản.
- Nếu có `GOOGLE_API_KEY`, thử Google Search.
- Đăng xuất và refresh trang để xác nhận session không còn.

## 8. Kiểm thử bảo mật trước khi chia sẻ link

```powershell
docker compose -f compose.test.yaml run --rm backend-test pytest -q
docker compose run --rm frontend npm run typecheck
docker compose run --rm frontend npm test --
powershell -ExecutionPolicy Bypass -File security-tests/run-phase6-attacks.ps1
```

Nếu chạy trên host Windows không có Python 3.13/pytest, ưu tiên chạy bằng container test thay vì host Python.

## 9. Vận hành tối thiểu

- Giữ registration invite code bí mật; rotate nếu bị lộ.
- Không bật profile `observability` ra internet. Nếu cần Grafana, đặt sau VPN/SSO và đổi password mặc định.
- Theo dõi `429`, `provider_failed`, `python infra_failure`, và security events trong admin evidence.
- Đặt quota/cảnh báo chi phí ở LLM provider và Google API console.
- Sao lưu `postgres-data` và toàn bộ `secrets-prod/` vào kho bí mật riêng.

## 10. Rollback nhanh

```powershell
docker compose --env-file .env.production -f compose.yaml -f compose.prod.yaml logs --tail=200 backend kong frontend
docker compose --env-file .env.production -f compose.yaml -f compose.prod.yaml down
```

Không xóa volume `postgres-data` khi rollback nếu chưa backup.
