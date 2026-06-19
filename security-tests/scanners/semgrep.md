# Semgrep

## Khi nào dùng

- Rà nhanh Python backend, Next.js frontend, và policy code trước khi demo.
- Bổ sung cho test deny-path của search, admin, sandbox, và auth.

## Lệnh gợi ý

Nếu đã có `pipx`:

```powershell
pipx run semgrep --config p/owasp-top-ten --config p/python --config p/typescript backend frontend
```

Nếu muốn lưu JSON để tổng hợp:

```powershell
pipx run semgrep --config p/owasp-top-ten --config p/python --config p/typescript --json --output security-tests/output/scanners/semgrep/report.json backend frontend
```

## Cách đọc kết quả

- Ưu tiên các rule liên quan đến auth/session, token handling, SSRF, command execution, insecure deserialization, dangerous HTML rendering, và secret exposure.
- Với `security-tests/output/scanners/semgrep/report.json`, chỉ trích xuất finding còn giá trị sau khi so với test hiện có.
- Nếu Semgrep flag code đã được chặn bởi runtime policy hoặc deny-path test, ghi rõ là `defense-in-depth signal`, không tự động coi là bug phát hành.

## Không chứng minh được điều gì

- Không chứng minh BOLA đã fail-closed trên toàn route set.
- Không chứng minh refresh replay thật sự revoke cả family.
- Không chứng minh Python probe không tạo side effect ở DB/process/network.
