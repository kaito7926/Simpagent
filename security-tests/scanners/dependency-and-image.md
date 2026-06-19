# Dependency And Image Scans

## Python dependencies

Repo backend dùng `backend/pyproject.toml`. Có thể audit trực tiếp project path:

```powershell
pipx run pip-audit --path backend
```

Muốn xuất JSON:

```powershell
pipx run pip-audit --path backend --format json | Set-Content -Encoding utf8 security-tests/output/scanners/pip-audit/backend.json
```

## Frontend dependencies

```powershell
npm audit --prefix frontend --audit-level=high
```

Muốn lưu JSON:

```powershell
npm audit --prefix frontend --json | Set-Content -Encoding utf8 security-tests/output/scanners/npm-audit/frontend.json
```

## Trivy config scan

```powershell
trivy config --severity HIGH,CRITICAL compose.yaml backend/Dockerfile frontend/Dockerfile sandbox kong observability
```

## Trivy image scan

Sau khi build stack:

```powershell
docker compose build
trivy image --severity HIGH,CRITICAL postgres:18.4
trivy image --severity HIGH,CRITICAL kong:3.9.1
```

Nếu muốn scan image app nội bộ sau build, dùng tên image thực tế `docker images` vừa sinh ra trong máy evaluator.

## Ghi chú đánh giá

- `google-adk`, `openai`, `next`, `react`, `kong`, `postgres`, và image sandbox cần được đọc theo context của prototype local, không chỉ theo CVE count.
- Với finding ở image base hoặc transitive dependency, phải ghi rõ exploitability trong topology thật: có public exposure không, có chạm được route hay credential nào không, đã bị deny bởi runtime policy chưa.
