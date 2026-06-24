# Hướng dẫn deploy internet nhỏ trên Rocky Linux

Tài liệu này dành cho topology single-node trong `compose.prod.yaml`, phù hợp demo/prototype khoảng 100 user/tháng. Mặc định production dùng **một HTTPS origin** cho cả frontend và API, ví dụ `https://simpagent.example.com`. Không tách `app.example.com` và `api.example.com` nếu chưa đổi lại chiến lược cookie/API base, vì frontend đang gọi `/api/...` relative và refresh cookie dùng prefix `__Host-*`.

## 1. Chuẩn bị host Rocky Linux

Cài Docker Engine và Compose plugin:

```bash
sudo dnf remove -y docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-engine
sudo dnf -y install dnf-plugins-core
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo dnf -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
newgrp docker
docker compose version
```

Nếu host public trực tiếp và dùng `firewalld`, chỉ mở `80/443` cho reverse proxy hoặc tunnel:

```bash
sudo firewall-cmd --permanent --zone=public --add-service=http
sudo firewall-cmd --permanent --zone=public --add-service=https
sudo firewall-cmd --reload
```

- Đặt reverse proxy, tunnel, hoặc load balancer public terminate HTTPS phía trước Kong.
- Chỉ expose public origin HTTPS; không expose PostgreSQL, backend direct port, Kong Admin API, sandbox, Loki, hoặc Grafana.
- Nếu dùng Cloudflare/Tunnel, ghi lại CIDR edge thật để đặt `TRUSTED_PROXY_CIDRS`.
- Rocky Linux thường bật SELinux `Enforcing`; nếu bind mount báo `Permission denied`, kiểm tra lại relabel bind mount kiểu `:z` hoặc `:Z` theo tài liệu Docker trước khi debug sâu hơn.

## 2. Tạo file môi trường production

```bash
cp .env.production.example .env.production
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

```bash
umask 077
mkdir -p secrets-prod

pg_password="$(openssl rand -hex 32)"
printf '%s' "$pg_password" > secrets-prod/postgres_password
printf 'postgresql+psycopg://simpagent:%s@postgres:5432/simpagent' "$pg_password" > secrets-prod/database_url

openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out secrets-prod/jwt_private_key
openssl rsa -pubout -in secrets-prod/jwt_private_key -out secrets-prod/jwt_public_key

openssl rand -hex 48 | tr -d '\n' > secrets-prod/refresh_hmac_key
openssl rand -hex 48 | tr -d '\n' > secrets-prod/csrf_hmac_key
openssl rand -hex 48 | tr -d '\n' > secrets-prod/python_capability_secret
openssl rand -hex 16 | tr -d '\n' > secrets-prod/registration_invite_code
```

Nếu dùng provider thật:

```bash
printf '%s' '<OPENAI_COMPATIBLE_KEY>' > secrets-prod/llm_api_key
printf '%s' '<GOOGLE_API_KEY>' > secrets-prod/google_api_key
```

Mã trong `secrets-prod/registration_invite_code` là mã mời để tạo tài khoản mới. Chỉ gửi mã này cho người được phép đăng ký.

## 4. Kiểm tra cấu hình trước khi chạy

```bash
docker compose --env-file .env.production -f compose.yaml -f compose.prod.yaml config -q
docker compose --env-file .env.production -f compose.yaml -f compose.prod.yaml config | grep -E "published|POSTGRES_PASSWORD|/var/run/docker.sock|https://"
```

Kỳ vọng:

- Chỉ Kong publish port public.
- Không còn `POSTGRES_PASSWORD: postgres`.
- Sandbox vẫn mount Docker socket trong prototype; nếu public lâu dài, chuyển sang Docker rootless/socket proxy hoặc host sandbox riêng.
- Origin trong Kong và backend khớp domain thật.

## 5. Build và chạy

```bash
docker compose --env-file .env.production -f compose.yaml -f compose.prod.yaml up -d --build
```

Theo dõi log:

```bash
docker compose --env-file .env.production -f compose.yaml -f compose.prod.yaml ps
docker compose --env-file .env.production -f compose.yaml -f compose.prod.yaml logs -f postgres migrate kong backend frontend
```

Repo này không có bước riêng tên `docker migrate deploy`. Production migration là service `migrate` và nó chạy `alembic upgrade head` khi bạn `up` stack. Nếu chỉ muốn chạy lại migration:

```bash
docker compose --env-file .env.production -f compose.yaml -f compose.prod.yaml up --build migrate
```

## 6. Bootstrap admin đầu tiên

```bash
docker compose --env-file .env.production -f compose.yaml -f compose.prod.yaml run --rm backend python -m app.cli.bootstrap_admin --email admin@ten-mien-that-cua-ban
```

Lưu password sinh ra ở nơi an toàn. Không gửi password qua chat, issue, log, hoặc tài liệu.

## 7. Kiểm tra sau deploy

Từ host:

```bash
curl -fsS https://ten-mien-that-cua-ban/health
curl -fsS https://ten-mien-that-cua-ban/ready
```

Kiểm tra CORS preflight:

```bash
curl -i -X OPTIONS https://ten-mien-that-cua-ban/api/auth/login \
  -H "Origin: https://ten-mien-that-cua-ban" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Authorization, Content-Type, X-CSRF-Token, X-Correlation-Id"
```

Kiểm tra luồng người dùng:

- Đăng ký bằng invite code.
- Đăng nhập.
- Gửi chat thường.
- Gửi tool Python đơn giản.
- Nếu có `GOOGLE_API_KEY`, thử Google Search.
- Đăng xuất và refresh trang để xác nhận session không còn.

## 8. Vì sao `migrate` không thành công?

Hai lỗi hay gặp nhất:

1. Bạn chạy sai lệnh. Repo này dùng service `migrate` của Docker Compose, không dùng `prisma migrate deploy`, nên `docker migrate deploy` sẽ không chạy được.
2. Bạn reuse volume PostgreSQL cũ với credential mới.

Nếu `docker compose ... up ...` fail ở service `migrate`, kiểm tra:

```bash
docker compose --env-file .env.production -f compose.yaml -f compose.prod.yaml logs --tail=200 migrate postgres
docker compose --env-file .env.production -f compose.yaml -f compose.prod.yaml exec -T postgres psql -U postgres -d postgres -c '\du'
```

Nếu log chứa `password authentication failed for user "simpagent"` hoặc `role "simpagent" does not exist`, thường là:

- Host này đã từng chạy local/dev stack với volume `simpagent_postgres-data` cũ.
- Volume đó được bootstrap bằng user khác, hay gặp nhất là `postgres` từ `compose.yaml` gốc.
- `secrets-prod/database_url` hiện lại dùng user `simpagent`, nên Alembic không đăng nhập được.

Trên host disposable, cách sạch nhất là xóa volume cũ rồi bootstrap lại production từ đầu:

```bash
docker compose --env-file .env.production -f compose.yaml -f compose.prod.yaml down
docker volume rm simpagent_postgres-data
docker compose --env-file .env.production -f compose.yaml -f compose.prod.yaml up -d --build
```

Nếu cần giữ dữ liệu cũ, đừng xóa volume. Hãy đồng bộ lại credential trong `secrets-prod/database_url` với user/password đang tồn tại trong PostgreSQL, hoặc tạo role/password tương ứng trong DB cũ rồi mới chạy lại `migrate`.

Nếu cùng một host vừa chạy local vừa chạy production, tách project name ngay từ đầu để tránh dùng chung volume:

```bash
docker compose -p simpagent-prod --env-file .env.production -f compose.yaml -f compose.prod.yaml up -d --build
```

## 9. Kiểm thử bảo mật trước khi chia sẻ link

```bash
docker compose -f compose.test.yaml run --rm backend-test pytest -q
docker compose run --rm frontend npm run typecheck
docker compose run --rm frontend npm test --
pwsh -File security-tests/run-phase6-attacks.ps1
```

Nếu Rocky Linux chưa có `pwsh`, cài PowerShell trước hoặc chạy riêng suite `security-tests/*.ps1` từ máy có PowerShell.

## 10. Vận hành tối thiểu

- Giữ registration invite code bí mật; rotate nếu bị lộ.
- Không bật profile `observability` ra internet. Nếu cần Grafana, đặt sau VPN/SSO và đổi password mặc định.
- Theo dõi `429`, `provider_failed`, `python infra_failure`, và security events trong admin evidence.
- Đặt quota/cảnh báo chi phí ở LLM provider và Google API console.
- Sao lưu `postgres-data` và toàn bộ `secrets-prod/` vào kho bí mật riêng.

## 11. Rollback nhanh

```bash
docker compose --env-file .env.production -f compose.yaml -f compose.prod.yaml logs --tail=200 postgres migrate backend kong frontend
docker compose --env-file .env.production -f compose.yaml -f compose.prod.yaml down
```

Không xóa volume `postgres-data` khi rollback nếu chưa backup.