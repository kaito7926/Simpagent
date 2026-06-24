# Brief slide: SimpAgent - Kiến trúc AI Agent an toàn

## 1. Mục tiêu bàn giao

Tạo bộ slide **13 trang, thời lượng 12-14 phút**, phục vụ bảo vệ đồ án đại học. Bài trình bày cần chứng minh ba ý:

1. SimpAgent giải quyết một bài toán thật: chatbot có agent tools nhưng vẫn giữ ranh giới tenant, quyền hạn, mạng và thực thi mã.
2. Kiến trúc dùng nhiều lớp phòng thủ; Kong và lớp edge chỉ là tuyến đầu, FastAPI mới là nơi quyết định quyền cuối cùng.
3. Nhóm hiểu rõ giới hạn của prototype, không tuyên bố quá mức về Cloudflare, rate limiting hay sandbox.

**Thông điệp trung tâm:** “Không tin prompt, không tin gateway tuyệt đối, không chạy mã người dùng trong backend.”

## 2. Storyline và nội dung từng slide

### Slide 1 - SimpAgent: Secure Chatbot với Lightweight Agent

**Subtitle:** Từ chatbot thông thường đến AI Agent có kiểm soát

**Nội dung trên slide:**

- Chat, Google Search và Python tool trong một trải nghiệm thống nhất
- Security-by-design: identity, policy, gateway, sandbox, observability
- Demo: `https://chat.kaitovu.site`

**Visual:** Một đường request phát sáng đi qua 5 lớp: User → Edge → Kong → FastAPI Policy → AI/Tools.

**Lời nói:** “Mục tiêu của nhóm không chỉ là làm chatbot trả lời được, mà là bảo đảm chatbot không thể tự mở rộng quyền khi bắt đầu sử dụng công cụ.”

---

### Slide 2 - Bài toán và phạm vi bảo vệ

**Headline:** Khi chatbot có tool, prompt trở thành một nguồn dữ liệu không đáng tin cậy.

**Nội dung:**

- Tài sản: tài khoản, phiên đăng nhập, hội thoại riêng tư, API key, dữ liệu tool và hạ tầng host
- Tác nhân: người dùng hợp lệ, tài khoản bị chiếm, bot phân tán, prompt độc hại, provider bên ngoài
- Ranh giới: tenant/owner, role/scope, backend/tool, private network/public internet

**Visual:** Threat map gồm ba vòng đồng tâm: Data → Application → Edge/Internet.

**Lời nói:** “Threat model không dừng ở SQL injection. Với AI Agent, chúng tôi phải tính cả prompt injection, lạm dụng tool và code execution.”

---

### Slide 3 - Kiến trúc tổng thể đang triển khai

**Sơ đồ bắt buộc:**

```text
Browser
   |
HTTPS / Reverse proxy (nginx hiện quan sát được)
   |
Kong OSS 3.9.1 (DB-less)
   |--------------------|
Next.js             FastAPI
                        |---- PostgreSQL
                        |---- OpenAI-compatible LLM
                        |---- Gemini / Google Search
                        `---- Sandbox supervisor ---- isolated Python worker

FastAPI + Kong logs -> Promtail -> Loki -> Grafana
```

**Callout:** “Kong lọc coarse-grained; FastAPI thực thi authorization và policy cuối cùng.”

**Lời nói:** “Một request không được phép đi thẳng tới database, provider hay sandbox. Mỗi bước đều đi qua boundary có trách nhiệm rõ ràng.”

---

### Slide 4 - Luồng giao tiếp và xử lý an toàn giữa các container

**Trust boundaries bắt buộc phải thể hiện:**

```text
PUBLIC
Browser --HTTPS--> nginx/reverse proxy --HTTP nội bộ--> Kong :8000
                                                   |
PRIVATE network (internal: true)                   |
   Kong --------> Frontend :3000                   |
   Kong --------> FastAPI :8000 <------------------'
                       |----> PostgreSQL :5432
                       |----> Sandbox supervisor :8080
                       `----> Promtail/Loki (log đã redact)

EGRESS network
   FastAPI ----TLS----> OpenAI-compatible / Google APIs

ISOLATED RUNTIME
   Sandbox supervisor --signed capability--> Python worker
   Python worker: network=none, non-root, read-only rootfs,
                  cap_drop=ALL, no-new-privileges, CPU/RAM/PID/time limits
```

**Luồng logic xử lý an toàn:**

1. **Ingress:** Kong nhận request, áp dụng route allowlist, CORS, giới hạn body/rate và gắn correlation ID.
2. **Authenticate/authorize:** FastAPI validate schema, JWT, trạng thái tài khoản, role, scope và ownership; dữ liệu sai hoặc thiếu quyền bị fail-closed.
3. **Business transaction:** SQLAlchemy thao tác PostgreSQL qua repository/transaction; chỉ backend có quyền truy cập dữ liệu nghiệp vụ.
4. **Agent decision:** Guardrail kiểm tra prompt; coordinator chỉ chọn `direct_chat`, `google_search` hoặc `python` trong allowlist.
5. **Tool invocation:** Backend cấp capability ngắn hạn, ký và ràng buộc với execution/profile/code hash; sandbox xác minh trước khi tạo worker.
6. **Safe output:** Kết quả bị giới hạn kích thước, normalize/redact trước khi lưu hoặc trả về; log không chứa token, cookie hay API key.

**Network controls hiện có:**

- `private` đặt `internal: true`; database, sandbox và observability không có public application port.
- Production bỏ host port trực tiếp của FastAPI; Kong Admin API chỉ listen `127.0.0.1:8001` trong container.
- Chỉ backend nối thêm mạng `egress` để gọi provider; Python worker dùng `network=none`.
- Service gọi nhau bằng Docker DNS và cổng nội bộ, không hardcode IP container.

**Giới hạn phải nói rõ:** Docker `private` tạo network segmentation, **không đồng nghĩa mã hóa traffic container-to-container**. Với multi-host hoặc môi trường ít tin cậy, cần mTLS/TLS nội bộ, network policy/firewall, credential riêng từng service và secret rotation.

**Visual:** Ba vùng màu `PUBLIC`, `PRIVATE`, `EGRESS` và một hộp `NETWORK=NONE`; animate request từ ingress tới kết quả, mỗi bước hiện control tương ứng.

**Lời nói:** “An toàn không chỉ nằm ở kết nối, mà ở cả chuỗi xử lý: request được lọc, xác thực, cấp quyền tối thiểu, thực thi trong boundary riêng và chỉ trả dữ liệu đã kiểm soát.”

---

### Slide 5 - Defense in Depth: ai chịu trách nhiệm gì?

| Lớp | Control chính | Không được thay thế |
|---|---|---|
| Edge / Cloudflare đề xuất | TLS, DDoS/bot filtering, WAF, global rate limiting | Authorization nghiệp vụ |
| Kong OSS | Route, CORS, request-size, rate limit theo route, correlation ID | RBAC, scope, ownership |
| FastAPI | JWT validation, account state, RBAC, scope, BOLA, CSRF, tool policy | Container isolation |
| Agent coordinator | Guardrail, route allowlist, chuẩn hóa tool request | Quyền do backend cấp |
| Sandbox | No-network, resource limits, import/process policy | Bảo mật host cấp production |

**Visual:** 5 lá chắn xếp lớp; tuyệt đối không dùng hình “một ổ khóa bảo vệ tất cả”.

**Lời nói:** “Đây là kiến trúc fail-closed: model có thể đề xuất hành động, nhưng không có quyền tự cấp scope hoặc capability.”

---

### Slide 6 - Risk 1: Relay và Replay Attack

**Phân biệt rõ thuật ngữ:**

- **Relay attack:** kẻ tấn công làm proxy thời gian thực để chuyển tiếp login/session; Origin/CSRF không thể thay thế xác thực chống phishing.
- **Replay attack:** refresh token cũ bị gửi lại sau khi đã rotate.

**Control hiện có:**

- Access JWT sống ngắn; refresh token opaque chỉ lưu dạng hash
- Refresh token family, rotation nguyên tử, phát hiện reuse và revoke cả family
- Cookie `Secure`, `HttpOnly`, `SameSite`, prefix `__Host-`
- Refresh/logout yêu cầu Origin hợp lệ và `X-CSRF-Token`

**Residual risk:** Chưa có MFA/WebAuthn và chưa có giao diện quản lý phiên; relay thời gian thực vẫn có thể dẫn đến account takeover.

**Visual:** Timeline token `R1 → R2`; khi `R1` xuất hiện lần hai, toàn bộ family chuyển đỏ và bị revoke.

---

### Slide 7 - Risk 2: Account Takeover và XSS

**Attack paths:** Credential stuffing, password reuse, phishing/relay, đánh cắp session, OAuth misconfiguration và XSS chạy mã trong origin của ứng dụng.

**Control hiện có:**

- Argon2 password hashing; invite code hạn chế đăng ký công khai
- JWT kiểm tra issuer, audience, expiry và token type
- Refresh replay detection; logout revoke session family
- Google/GitHub OAuth fail-closed khi thiếu cấu hình
- Security events, correlation ID và admin evidence đã redact

**Ứng dụng chống XSS như thế nào:**

- React escape text theo mặc định; model/user content không được render thành raw HTML.
- Markdown chủ động escape HTML tag, không dùng `rehype-raw` hoặc `dangerouslySetInnerHTML`.
- Link chỉ cho phép `http:`, `https:`, `mailto:`; chặn `javascript:`, `data:` và relative link không duyệt.
- Link ngoài mở với `rel="noopener noreferrer"`; code block chỉ hiển thị text, không thực thi.
- Access token chỉ giữ trong memory, không ghi `localStorage`/`sessionStorage`; refresh token nằm trong cookie `HttpOnly`.
- CSP, HSTS, `nosniff`, `frame-ancestors 'none'` và `X-Frame-Options: DENY` giảm injection/clickjacking impact.

**Điểm yếu cần nói thẳng:**

- Chưa có MFA/WebAuthn, email verification, password reset, session/device management
- Phát hiện bất thường chủ yếu dựa vào log/evidence, chưa có risk engine
- CSP hiện còn `script-src 'unsafe-inline'`; cần nonce/hash hoặc strict CSP và Trusted Types để tăng khả năng chặn XSS.
- `HttpOnly` ngăn JavaScript đọc refresh cookie nhưng XSS cùng origin vẫn có thể gửi request như nạn nhân và đọc access token trong memory. Vì vậy output encoding và không render raw HTML là control chính.

**Roadmap:** strict CSP nonce/hash + Trusted Types → WebAuthn/MFA → session dashboard + revoke-all → dependency scanning/anomaly alerting.

---

### Slide 8 - Risk 3: Bypass Rate Limit

**Cách bypass có thể xảy ra:**

- Botnet/proxy rotation hoặc dải IPv6 làm thay đổi IP liên tục
- Tin nhầm `X-Forwarded-For` từ nguồn không thuộc trusted proxy
- Nhiều Kong node dùng `policy: local` tạo các bộ đếm độc lập
- Chỉ giới hạn theo IP không đủ cho tài khoản hoặc API cost abuse

**Control hiện có:**

- Kong rate limit riêng cho login/register, refresh, chat và Python tool
- FastAPI chỉ dùng forwarded IP khi peer thuộc `TRUSTED_PROXY_CIDRS`
- Request-size limit, correlation ID và gateway evidence hỗ trợ điều tra

**Kiến trúc đề xuất:**

- Cloudflare edge: WAF/Bot Management/Turnstile và rate limit trước origin
- Kong: giới hạn theo route; chuyển sang counter dùng chung khi scale nhiều node
- Backend: quota theo `user_id`, token family, tool cost và hành vi
- Origin firewall: chỉ nhận traffic từ edge/reverse proxy được phép

**Lời nói:** “Rate limit theo IP là control giảm tải, không phải cơ chế chống account takeover hoàn chỉnh.”

---

### Slide 9 - AI Agent và Tool Isolation

**Flow:** Guardrail → Coordinator allowlist → scope check → capability token ngắn hạn → tool boundary → normalized result.

**Search:**

- Chỉ scope `tool:websearch` mới được gọi
- Gemini/Google Search trả grounding metadata; unsafe/internal source bị loại
- Không trộn HTML từ model vào Markdown người dùng

**Python:**

- Không dùng `exec`, `eval` hoặc host subprocess trong FastAPI
- Chạy qua sandbox container; network mặc định bị chặn
- Giới hạn timeout, CPU, memory, PID, file size và output
- Chặn import/process nguy hiểm như `socket`, `subprocess`, `os.system`

**Residual risk:** Docker sandbox và Docker socket của supervisor phù hợp prototype, chưa tương đương gVisor/Kata/Firecracker cho mã đa tenant thù địch.

---

### Slide 10 - Điểm mạnh và điểm yếu của dự án

**Điểm mạnh:**

- Authorization nhiều lớp: role + scope + ownership + tool capability
- Network segmentation rõ: public/private/egress; Python runtime không có network
- Refresh rotation/replay detection và CSRF/Origin protection có test âm
- Markdown/React rendering fail-safe, token không lưu trong browser storage bền vững
- Sandbox tách khỏi backend, no-network và có resource policy
- Gateway config theo route; log có correlation ID xuyên suốt
- Evidence có thể chạy lại: unit/integration/security/smoke + attack scripts
- Fail-closed khi provider hoặc OAuth chưa cấu hình

**Điểm yếu:**

- Single-node, không HA, không distributed rate limiting
- Chưa MFA/WebAuthn, email verification, password reset, session management
- Search logic chưa là service/container độc lập
- Sandbox Docker chưa đủ cho hostile multi-tenant production
- Phụ thuộc LLM/Google/OAuth provider, chi phí và availability bên ngoài
- Cloudflare là kiến trúc đề xuất, chưa có evidence runtime từ domain demo
- Internal Docker traffic chưa có mTLS; CSP vẫn còn `'unsafe-inline'`

**Visual:** Ma trận 2 cột “Đã chứng minh” và “Cần nâng cấp”, không dùng SWOT bốn ô quá nhiều chữ.

---

### Slide 11 - Kịch bản demonstration

**Demo happy path, 2-3 phút:**

1. Mở `https://chat.kaitovu.site`, đăng nhập bằng tài khoản demo đã chuẩn bị.
2. Tạo hội thoại và hỏi một câu chat thường.
3. Gọi Google Search để hiển thị nguồn/grounding.
4. Chạy Python phép tính an toàn, cho thấy result đến từ sandbox.
5. Mở admin evidence: correlation ID, security event hoặc tool execution đã redact.

**Demo security path, 60-90 giây:**

1. Thử truy cập conversation của user khác → fail-closed, không lộ object.
2. Replay refresh token cũ → revoke family + event `refresh_reuse`.
3. Gửi nhiều login request vào stack test/local → nhận `429` từ Kong.
4. Thử Python gọi network/process cấm → policy từ chối trước side effect.
5. Gửi Markdown chứa `<script>`, `onerror` hoặc link `javascript:` → UI chỉ hiển thị inert text, không thực thi.

**Fallback:** Chuẩn bị video 90 giây và ảnh chụp evidence; không chạy destructive test trên domain public.

---

### Slide 12 - Demonstration result và bằng chứng

**Kết quả có thể khẳng định:**

- Ngày kiểm tra: 20/06/2026
- Domain demo trả `HTTP 200`, title `SimpAgent`
- Security headers quan sát được: CSP, HSTS, `X-Content-Type-Options`, `X-Frame-Options`, Referrer/Permissions Policy
- Request đi qua Kong: `Via: 1.1 kong/3.9.1`, có `X-Correlation-Id` và Kong latency headers
- Repo có 102 test files, 232 test functions được phát hiện bằng kiểm kê tĩnh
- Attack suite có 6 scenario: refresh replay, BOLA, guardrail abuse, SSRF, Python escape, brute-force rate limit

**Lưu ý bắt buộc:**

- Không ghi “232 tests passed” nếu chưa chạy suite trong buổi chuẩn bị; chỉ ghi “232 test cases được định nghĩa”.
- Domain hiện resolve trực tiếp tới một IPv4 và trả `Server: nginx`; chưa có header/CDN evidence để khẳng định Cloudflare đang proxy request.

**Visual:** Evidence board gồm 3 thẻ: Live HTTP, Automated Tests, Attack Scenarios.

---

### Slide 13 - Kết luận và roadmap

**Kết luận:**

- Prototype đã chứng minh AI Agent có thể dùng tool qua policy boundary rõ ràng.
- Defense in depth giảm blast radius: edge/gateway lọc traffic, backend quyết định quyền, sandbox cô lập execution.
- Nhóm biết phần nào đã có evidence và phần nào vẫn là residual risk.

**Roadmap 3 bước:**

1. **Identity:** WebAuthn/MFA, session management, account recovery an toàn
2. **Edge & scale:** Cloudflare được cấu hình thật, origin lockdown, distributed/user-aware rate limiting
3. **Isolation:** sandbox host riêng hoặc gVisor/Kata/Firecracker, managed secrets và HA observability

**Closing line:** “Secure AI không phải một sản phẩm hay plugin; đó là chuỗi quyết định fail-closed từ edge đến tool runtime.”

## 3. Design direction cho AI làm slide

### Phong cách

- **Mood:** security operations hiện đại, học thuật nhưng không khô cứng
- **Tỷ lệ:** 16:9, nền tối `#08111F`, surface `#101C2C`
- **Màu chính:** cyan `#35D0FF`; safe green `#48D597`; risk amber `#FFB547`; critical coral `#FF667A`
- **Typography:** Be Vietnam Pro cho tiêu đề/nội dung; JetBrains Mono cho header HTTP, scope và code
- **Bố cục:** mỗi slide một luận điểm, tối đa 35-45 từ hiển thị chính; chi tiết chuyển vào speaker notes
- **Hình ảnh:** sơ đồ vector, trust boundary, request flow, evidence cards; tránh ảnh robot, não AI và ổ khóa stock

### Quy tắc trực quan

- Luồng hợp lệ dùng cyan/green; traffic bị chặn dùng coral và kết thúc bằng biểu tượng `DENY`.
- Control hiện có dùng nhãn **IMPLEMENTED**; đề xuất tương lai dùng **ROADMAP**; residual risk dùng **LIMITATION**.
- Cloudflare phải có nhãn **OPTIONAL EDGE / PROPOSED**, không đặt như một thành phần đã xác minh.
- Với slide kiến trúc, đặt đường biên public/private/external rõ ràng; không nối Browser trực tiếp đến FastAPI, database hoặc sandbox.
- Dùng animation theo request flow, tối đa 2-3 bước mỗi slide; không dùng transition 3D.

## 4. Prompt copy-paste cho AI Agent tạo slide

```text
Hãy tạo một deck PowerPoint 13 slide, 16:9, bằng tiếng Việt dựa đúng vào brief này.

Đối tượng: giảng viên chấm đồ án CNTT/an toàn thông tin.
Thời lượng: 12-14 phút.
Mục tiêu: phân tích điểm mạnh, điểm yếu, ba rủi ro Relay/Replay Attack, Account Takeover/XSS, Bypass Rate Limit; giải thích kiến trúc Kong + FastAPI + sandbox, luồng giao tiếp an toàn giữa Docker containers; trình bày Cloudflare như lớp edge đề xuất; và hướng dẫn demo tại https://chat.kaitovu.site.

Yêu cầu nội dung:
- Giữ đúng tên SimpAgent và các claim kỹ thuật trong brief.
- Phân biệt relay attack với refresh-token replay.
- Nhấn mạnh Kong chỉ lọc coarse-grained; FastAPI là authorization authority cuối cùng.
- Thể hiện rõ bốn vùng PUBLIC, PRIVATE, EGRESS và NETWORK=NONE; không gọi Docker private network là mã hóa nội bộ.
- Giải thích XSS prevention bằng React escaping, safe Markdown URL, không raw HTML, memory-only access token và HttpOnly refresh cookie; nêu rõ giới hạn CSP `unsafe-inline`.
- Không tuyên bố Cloudflare đang hoạt động trên domain demo; dùng nhãn OPTIONAL EDGE / PROPOSED.
- Không tuyên bố 232 tests đã pass; chỉ nói repo định nghĩa 232 test functions nếu không có kết quả chạy mới.
- Nêu thẳng limitation: single-node, local rate-limit counter, chưa MFA/WebAuthn, Docker sandbox chưa production-grade hostile multi-tenant.
- Mỗi slide có speaker notes 40-70 từ và một câu chuyển sang slide kế tiếp.

Yêu cầu thiết kế:
- Dark security-operations aesthetic, nền #08111F, cyan #35D0FF, green #48D597, amber #FFB547, coral #FF667A.
- Font Be Vietnam Pro; code/evidence dùng JetBrains Mono.
- Không dùng ảnh robot, não AI, hacker áo hoodie hoặc ổ khóa stock.
- Ưu tiên sơ đồ vector, trust boundaries, flow arrows và evidence cards.
- Mỗi slide chỉ có một thông điệp chính, tối đa 35-45 từ trên canvas.
- Gắn nhãn IMPLEMENTED, ROADMAP, LIMITATION nhất quán.

Đầu ra:
1. File PPTX có thể chỉnh sửa.
2. PDF export.
3. Danh sách nguồn ở speaker notes của slide 12.
4. Tất cả sơ đồ là shape/vector, không raster hóa chữ.
```

## 5. Checklist trước khi thuyết trình

- Thay tài khoản demo bằng credential dùng riêng cho buổi bảo vệ; không đưa password/API key lên slide.
- Chạy attack suite trên local stack, không tấn công domain public.
- Chụp lại kết quả `HTTP 200`, health/ready và evidence ngay trước buổi trình bày.
- Nếu bật Cloudflare sau này, thu evidence DNS/proxy headers/WAF event và cập nhật slide 3, 7, 11.
- Chuẩn bị video fallback và ảnh chụp các deny-path quan trọng.
- Kiểm tra QR/link demo từ mạng ngoài trường và một thiết bị di động.

## 6. Nguồn nội bộ để AI không tự bịa

- `README.md`
- `docs/architecture.vi.md`
- `docs/security.vi.md`
- `docs/limitations.vi.md`
- `docs/deploy-production.vi.md`
- `docs/testing.vi.md`
- `kong/kong.prod.yml`
- `security-tests/README.md`
