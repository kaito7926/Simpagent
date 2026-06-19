# Scanner Guidance

Các scanner trong thư mục này là lớp bằng chứng bổ sung cho Phase 6. Chúng không thay thế test business-logic, BOLA, replay, hay side-effect assertions trong `security-tests/run-phase6-matrix.ps1` và `security-tests/run-phase6-attacks.ps1`.

## Mục tiêu

- Dò thêm lỗi cấu hình, dependency, image, và bề mặt HTTP.
- Chuẩn hóa nơi evaluator lưu kết quả môi trường của riêng họ.
- Giữ claim trung thực: scanner chỉ giúp tìm tín hiệu, không tự chứng minh control logic đã đúng.

## Cấu trúc

- `semgrep.md` - SAST cho Python/TypeScript và rule packs gợi ý.
- `dependency-and-image.md` - `pip-audit`, `npm audit`, Trivy config/image scans.
- `burp-awvs-zap.md` - Burp Suite, AWVS, ZAP, và authenticated DAST scope.
- `../templates/finding-template.md` - mẫu ghi nhận phát hiện.
- `../templates/evidence-index-template.md` - mẫu index các output evaluator tự sinh.

## Nơi lưu output

Khuyến nghị lưu raw output ngoài Git, ví dụ:

```text
security-tests/output/scanners/
  semgrep/
  pip-audit/
  npm-audit/
  trivy/
  burp/
  awvs/
  zap/
```

Sau khi chạy, hãy tóm tắt phát hiện đáng chú ý bằng `security-tests/templates/finding-template.md` thay vì commit toàn bộ dump môi trường.
