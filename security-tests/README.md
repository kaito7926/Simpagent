# Phase 6 Security Tests

`security-tests/` là bộ attack-suite và evidence tooling dành cho evaluator của Phase 6. Mục tiêu của thư mục này là chứng minh các control cuối cùng bằng runner có thể chạy lại từ repo root trên Windows, thay vì buộc người đọc tự đoán từng lệnh rời rạc trong `.planning/`.

## Phạm vi an toàn

- Chỉ nhắm vào stack Docker Compose cục bộ do repo này sở hữu.
- Không nhắm tới bên thứ ba, IP public thật, provider OAuth thật, hay bất kỳ tài sản ngoài `localhost`.
- Các probe Python chỉ cố tình thử đường bị cấm như localhost, replay token, prompt abuse, và os/system; chúng không chạy payload phá hoại.

## Prerequisites

- Docker Desktop đang chạy và có Linux engine.
- PowerShell trên Windows.
- Chạy từ repo root hoặc bất kỳ đâu miễn là giữ nguyên cấu trúc repo; runner sẽ tự `subst` một drive tạm để tránh lỗi Compose trên đường dẫn Unicode.

## Entry points

### Automated evidence matrix

```powershell
powershell -ExecutionPolicy Bypass -File security-tests/run-phase6-matrix.ps1
```

Runner này gom các subset backend/frontend hiện có thành một matrix lặp lại được cho `TEST-01`, `TEST-02`, `TEST-03`, `TEST-04`, `TEST-05`, `TEST-06`, `TEST-09`, và `TEST-10`.

### Black-box attack suite

```powershell
powershell -ExecutionPolicy Bypass -File security-tests/run-phase6-attacks.ps1
```

Runner này khởi động stack local rồi chạy các probe:

- refresh replay
- BOLA hai người dùng
- prompt/tool abuse bị guardrail chặn
- SSRF/internal reachability bị sandbox chặn
- sandbox escape probe bị policy chặn
- brute-force login bị Kong rate limit

## Output

Cả hai runner sẽ ghi summary JSON vào `security-tests/output/`. Thư mục đó đã được ignore khỏi Git để evaluator có thể chạy lại nhiều lần mà không làm bẩn worktree.

## Focused attack scripts

- `security-tests/attacks/invoke-refresh-replay.ps1`
- `security-tests/attacks/invoke-bola.ps1`
- `security-tests/attacks/invoke-guardrail-abuse.ps1`
- `security-tests/attacks/invoke-ssrf-probe.ps1`
- `security-tests/attacks/invoke-python-escape.ps1`
- `security-tests/attacks/invoke-brute-force.ps1`

Mỗi script đều dùng chung helper trong `security-tests/lib/phase6-common.ps1`, có thể gọi riêng khi cần debug từng control.
