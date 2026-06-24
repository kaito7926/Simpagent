# Giới hạn hiện tại

## Quy mô và vận hành

- Đây là prototype Compose single-node, mục tiêu khoảng 100 user/tháng.
- Không có HA, rolling deploy, multi-region, distributed rate limiting, hay managed secret rotation hoàn chỉnh.
- Kong đang dùng policy rate limit local; kết quả không nên overclaim như hệ thống production multi-instance.

## External dependency và data flow

- Direct chat phụ thuộc provider OpenAI-compatible nếu muốn có câu trả lời thật.
- Search phụ thuộc Google Search / Gemini-compatible capability khi có credential.
- Google OAuth và GitHub OAuth phụ thuộc provider thật và redirect URI hợp lệ.
- Thiếu credential thì behavior đúng phải là degraded hoặc unconfigured, không phải giả thành công.

## Search retention và claim discipline

- Repo cố ý chỉ giữ metadata grounding đã normalize/allowlist, không giữ raw payload vô hạn.
- Nếu provider trả về thiếu nguồn an toàn, trạng thái phải là `missing_grounding` thay vì giả làm `grounded`.
- Search planning/history của Phase 3 vẫn còn debt trong `.planning`; Phase 6 không xóa dấu vết đó.

## Sandbox Python

- Sandbox hiện dựa trên Docker isolation, không phải gVisor, Kata, microVM, hay hostile multi-tenant production sandbox.
- Mô hình này phù hợp để chứng minh boundary cho prototype, không đủ để overclaim “safe for arbitrary internet adversaries”.
- Trên Windows, runner Phase 6 phải tự `subst` drive tạm để tránh vấn đề Compose với đường dẫn Unicode của repo.
- Sandbox phụ thuộc Docker engine local; nếu Docker Desktop tắt, matrix/attack runner sẽ không xác minh được behavior thật.

## Những gì chưa có

- email verification
- password reset
- MFA / WebAuthn step-up; Phase 07 chỉ dùng DPoP-style proof trong browser, chưa phải phishing-resistant WebAuthn
- user-facing session management
- organization / shared workspace
- file upload, RAG, knowledge base, hay write-capable external tools
- public Swagger/OpenAPI surface qua Kong public route

## Search boundary thực tế

- Search hiện là service logic trong backend, chưa là container/service tách độc lập trong Compose.
- Vì vậy tài liệu không nên overclaim “separate search worker container”.
- Search capability đã được ký bất đối xứng và consume-once, nhưng scope này chỉ áp dụng cho boundary đã review trong Phase 07.

## Sender-constrained session limits

- Browser-held proof material sống trong memory của phiên frontend; mất key do reload hard, xóa site data, hoặc browser reset có thể buộc user re-auth.
- Hardening hiện feature-flagged qua backend/frontend rollout; không nên tuyên bố mọi endpoint tương lai tự động được bảo vệ nếu chưa đi qua `authorizedJson` hoặc route enforcement tương ứng.
- DPoP-style proof giảm replay của copied token/cookie, nhưng không thay thế XSS prevention, CSRF/Origin check, hay user education chống relay/phishing thời gian thực.
- WebAuthn step-up và quản lý nhiều thiết bị/session vẫn là việc deferred, không nằm trong MVP Phase 07.

## Cloudflare và edge

- Cloudflare chỉ là lựa chọn triển khai mô tả ở docs, không phải dependency để chạy local demo.
- Không nên coi việc có Cloudflare option là bằng chứng cho enterprise edge protection, anti-DDoS hoàn chỉnh, hay zero-trust production posture.
