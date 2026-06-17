---
status: awaiting_human_verify
trigger: "Khi tôi test oauth github thì bị: GET http://localhost:8000/api/auth/oauth/github/callback?code=8fe6728331b8298d782c&state=3JfsEEPYFDc3JN2dAoXg0cmf2zHYMb9u_356Fz3aC8k {\"error\":{\"code\":\"internal_error\",\"message\":\"A server error occurred. Please try again.\",\"correlation_id\":\"518d492a-ef1b-4f4d-bc57-f1f70b55a14c\"}}\n\nKhi tôi test oauth google thì bị: GET http://localhost:8000/api/auth/oauth/google/callback?state=k5jDDeKp37t3ewC07asEdxYjKTsz3AUPwez_2GpsEi4&iss=https%3A%2F%2Faccounts.google.com&code=4%2F0AdkVLPy5HhShadNzhRUiNTxexrc_ulw46vhSg0veOW4OILVvIJ-4D2fuNwjRRGIbqDb9Fw&scope=email+profile+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fuserinfo.profile+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fuserinfo.email+openid&authuser=0&prompt=consent {\"error\":{\"code\":\"internal_error\",\"message\":\"A server error occurred. Please try again.\",\"correlation_id\":\"f13e259c-73ae-4801-bd44-f02fe1b0847a\"}}"
created: 2026-06-16
updated: 2026-06-16T23:32:11+07:00
---

## Symptoms

- Expected behavior: GitHub và Google OAuth callback hoàn tất đăng nhập, tạo phiên refresh-cookie, rồi redirect về workspace đã xác thực.
- Actual behavior: Cả callback GitHub và Google đều trả JSON lỗi `internal_error` từ backend thay vì hoàn tất đăng nhập.
- Error messages: `correlation_id` GitHub = `518d492a-ef1b-4f4d-bc57-f1f70b55a14c`; `correlation_id` Google = `f13e259c-73ae-4801-bd44-f02fe1b0847a`.
- Timeline: Xảy ra khi test OAuth hiện tại sau khi đã cấu hình env.
- Reproduction: Bắt đầu OAuth qua provider, chấp nhận trên GitHub/Google, backend callback `/api/auth/oauth/{provider}/callback` trả `internal_error`.

## Current Focus

reasoning_checkpoint:
  hypothesis: "Google và GitHub OAuth callback fail vì provider code truyền `token=` vào `AsyncOAuth2Client.get()`, nhưng Authlib 1.7.2/httpx 0.28.1 không hỗ trợ tham số này; exception `TypeError` thoát khỏi callback và bị generic error handler đổi thành `internal_error`."
  confirming_evidence:
    - "Backend logs cho cả correlation_id GitHub và Google đều cho thấy token exchange POST thành công rồi cùng nổ `TypeError: AsyncClient.get() got an unexpected keyword argument 'token'` tại dòng `client.get(..., token=token)` trong hai provider."
    - "Inspection trong container xác nhận `AsyncOAuth2Client.get(...)` không có tham số `token`, trong khi `AsyncOAuth2Client.request(...)` tự dùng `self.token`/`self.token_auth` nếu token đã được lưu sau `fetch_token()`."
  falsification_test: "Nếu sau khi bỏ `token=` và gọi `client.get(url)` callback vẫn nổ cùng `TypeError` hoặc phát sinh `MissingTokenError` do `fetch_token()` không lưu token trên client, giả thuyết này sai hoặc chưa đầy đủ."
  fix_rationale: "Vì `fetch_token()` của Authlib lưu token trên client và `request()` tự gắn auth bearer từ `self.token`, nên bỏ đối số `token=` ở các lời gọi GET sẽ dùng đúng API tương thích hiện tại và loại bỏ điểm nổ gốc thay vì chỉ che lỗi 500."
  blind_spots: "Chưa có test integration đi qua HTTP client thật với provider live endpoints; cần regression test focused vào cách provider gọi `get()` để ngăn tái phát khi nâng version dependency."

- hypothesis: Root cause đã xác nhận: cả Google và GitHub provider đang gọi `AsyncOAuth2Client.get(..., token=token)`, nhưng phiên bản Authlib/httpx hiện tại không chấp nhận keyword `token`, nên callback nổ `TypeError` sau khi token exchange thành công; fake-provider tests không lộ bug vì không đi qua code HTTP thật.
- hypothesis: Fix đã được áp dụng vào source và runtime backend container; cần self-verify bằng focused tests và xác nhận container đang chạy code đã vá.
- test: Kiểm tra source đang chạy trong container và chạy narrowed OAuth test set bao phủ regression mới cùng callback flows.
- expecting: Code trong container không còn `token=` ở provider GET requests, test set pass sạch, và điều này chứng minh nguyên nhân 500 cũ đã bị loại bỏ.
- next_action: Prepare human verification checkpoint with exact reproduction steps for real GitHub/Google login.

## Evidence

- timestamp: 2026-06-16T23:32:11+07:00
  checked: `.planning/debug/knowledge-base.md`
  found: File does not exist, nên không có known-pattern match để ưu tiên.
  implication: Cần điều tra từ đầu thay vì dựa trên ca lỗi đã lưu.

- timestamp: 2026-06-16T23:32:11+07:00
  checked: repo-wide search for `oauth`, `callback`, `internal_error`, `correlation_id`
  found: Code area liên quan tập trung ở `backend/app/api/routes/auth_oauth.py`, `backend/app/identity/oauth_service.py`, và các integration/smoke tests OAuth.
  implication: Lỗi nhiều khả năng nằm ở backend OAuth path dùng chung, không phải frontend route riêng lẻ.

- timestamp: 2026-06-16T23:32:50+07:00
  checked: `backend/app/api/routes/auth_oauth.py`
  found: Cả Google và GitHub callback có cấu trúc giống nhau: validate state/code, gọi `provider.authenticate(...)`, rồi gọi `OAuthService.complete_login(...)`; route chỉ catch `(OAuthAuthenticationError, ValueError)` và map chúng thành `oauth_login_failed` 401.
  implication: Nếu client nhận `internal_error` thay vì `oauth_login_failed`, đã có exception khác thoát khỏi callback path chung và bị global error handler biến thành lỗi 500.

- timestamp: 2026-06-16T23:32:50+07:00
  checked: `backend/app/identity/oauth_service.py`
  found: `complete_login` chạy transaction DB, link/provision user, tạo session family/token, issue access token, rồi tạo CSRF token sau transaction; chỉ `DuplicateEmailError` và `IntegrityError` được chuyển thành `OAuthAuthenticationError`, còn lỗi khác như DB/config/runtime sẽ thoát ra ngoài.
  implication: Có một số điểm fail dùng chung cho cả provider nằm trong service/session/config path và chúng phù hợp với triệu chứng `internal_error` chung.

- timestamp: 2026-06-16T23:33:49+07:00
  checked: `backend/app/identity/providers/google.py` and `backend/app/identity/providers/github.py`
  found: Cả hai provider dùng `authlib.integrations.httpx_client.AsyncOAuth2Client.fetch_token(...)` rồi gọi API userinfo/email; route callback chỉ catch `OAuthAuthenticationError` và `ValueError`, không catch lỗi HTTP/Authlib như network timeout, OAuth token exchange failure, hoặc `HTTPStatusError` từ `raise_for_status()`.
  implication: Sai cấu hình redirect/client secret hoặc lỗi trao đổi token ở provider có thể thành `internal_error` thay vì lỗi OAuth có kiểm soát.

- timestamp: 2026-06-16T23:33:49+07:00
  checked: `backend/app/core/config.py`, `backend/app/db/repositories/accounts.py`, `backend/app/db/repositories/sessions.py`
  found: Path chung sau authenticate phụ thuộc nhiều config/runtime như JWT keys, refresh/CSRF HMAC keys, email normalization, DB flush; các property này có thể ném `ValueError` hoặc runtime exception khi giá trị secret/file không hợp lệ.
  implication: Ngoài provider exchange, nhánh session/config chung cũng vẫn là ứng viên mạnh cho lỗi dùng chung hai provider.

- timestamp: 2026-06-16T23:34:33+07:00
  checked: `backend/tests/integration/auth/test_google_oauth.py`, `backend/tests/integration/auth/test_github_oauth.py`, `backend/tests/integration/auth/test_oauth_flows.py`
  found: Integration tests với fake providers xác nhận cả hai callback route đều redirect thành công, set refresh/CSRF cookies, provision/link account đúng và fail closed cho identity không hợp lệ.
  implication: Logic callback/service nội bộ hoạt động trong môi trường test; lỗi production-like hiện tại nhiều khả năng nằm ở tương tác với provider thật hoặc exception class chưa được route map đúng.

- timestamp: 2026-06-16T23:34:33+07:00
  checked: `backend/app/main.py` and `backend/app/core/errors.py`
  found: Bất kỳ exception nào không phải `ApiError` sẽ bị generic handler trả `{"error":{"code":"internal_error",...}}` cùng correlation_id; middleware cũng log stack trace cho các exception uncaught.
  implication: Triệu chứng người dùng thấy phù hợp chính xác với một exception uncaught trong callback path, không phải nhánh lỗi OAuth đã được xử lý.

- timestamp: 2026-06-16T23:35:22+07:00
  checked: Docker runtime state
  found: Container `simpagent-backend-1` đang chạy và healthy, nên có thể dùng container logs để truy vết correlation_id thật từ lần lỗi người dùng gặp.
  implication: Có thể chuyển từ suy luận code sang quan sát trực tiếp stack trace để xác nhận nguyên nhân.

- timestamp: 2026-06-16T23:37:19+07:00
  checked: backend container logs for correlation_ids `518d492a-ef1b-4f4d-bc57-f1f70b55a14c` and `f13e259c-73ae-4801-bd44-f02fe1b0847a`
  found: Cả hai callback đều POST token exchange thành công (`HTTP/1.1 200 OK`), rồi nổ cùng một stack trace: `TypeError: AsyncClient.get() got an unexpected keyword argument 'token'` tại `backend/app/identity/providers/github.py:88` và `backend/app/identity/providers/google.py:88`.
  implication: Lỗi không nằm ở DB/session/config hay provider credentials; root cause là cách gọi `client.get(..., token=token)` không tương thích với Authlib/httpx API hiện tại sau khi đã lấy access token.

- timestamp: 2026-06-16T23:37:19+07:00
  checked: repo search for `token=` usage and existing OAuth tests
  found: Chỉ hai provider OAuth dùng pattern `client.get(..., token=token)`; không có test nào đi qua implementation HTTP thật của provider vì integration tests đều dùng fake providers và smoke tests chỉ kiểm tra `/start` endpoints.
  implication: Đây là một test gap giải thích vì sao bug lọt qua suite hiện tại.

- timestamp: 2026-06-16T23:39:52+07:00
  checked: backend dependency/runtime API inspection (`backend/pyproject.toml` and container introspection)
  found: Backend đang chạy `Authlib 1.7.2` với `httpx 0.28.1`; `AsyncOAuth2Client.get(...)` không có tham số `token`, còn `AsyncOAuth2Client.request(...)` tự dùng `self.token`/`self.token_auth` sau `fetch_token()`.
  implication: Fix đúng là bỏ `token=` ở các GET request sau `fetch_token()`, không phải thêm catch che lỗi.

- timestamp: 2026-06-16T23:42:31+07:00
  checked: first focused pytest attempt
  found: Lần chạy đầu fail do dùng sai đường dẫn bash-style (`/d/D:/...`), chưa thực thi được test logic nào.
  implication: Đây là lỗi thao tác môi trường, không phải tín hiệu phản bác giả thuyết; cần chạy lại với absolute path đúng kiểu Git Bash.

- timestamp: 2026-06-16T23:43:16+07:00
  checked: second focused pytest attempt from backend directory
  found: Shell dùng `C:\Program Files\Python312\python.exe` không có `pytest` module, nên chưa thể xác minh qua local interpreter hiện tại.
  implication: Cần tìm runtime test đúng của project (ví dụ backend container hoặc uv/venv) trước khi kết luận verification.

- timestamp: 2026-06-16T23:46:29+07:00
  checked: backend container runtime
  found: `simpagent-backend-1` có `pytest 9.1.0` và đúng dependency set của project, nên đây là runtime xác minh phù hợp hơn shell host hiện tại.
  implication: Verification nên thực hiện trong container backend thay vì Python host cục bộ.

- timestamp: 2026-06-16T23:47:37+07:00
  checked: focused OAuth tests inside backend container after copying patched files
  found: 11/12 tests pass; failure duy nhất là `test_github_start_rejects_unconfigured_provider_without_secret_leak` mong 503 nhưng container env hiện tại đã cấu hình GitHub OAuth nên `/start` trả 303. Hai regression tests mới pass, toàn bộ Google callback tests pass, và các GitHub callback tests pass.
  implication: Fix không làm vỡ callback flows; còn một test nhiễu do khác biệt env container, không mâu thuẫn với root cause hay fix.

- timestamp: 2026-06-16T23:49:04+07:00
  checked: narrowed OAuth verification in backend container
  found: `tests/unit/test_oauth_providers.py` + callback-focused Google/GitHub integration tests pass sạch (`11 passed, 1 deselected`). Sau đó backend container được restart và inspection xác nhận runtime code đã bỏ `token=` khỏi cả hai provider GET requests.
  implication: Fix đã được xác minh trên test set liên quan và đang chạy trong backend runtime hiện tại; bước còn lại là xác nhận end-to-end với provider thật trong workflow người dùng.

## Eliminated

- hypothesis: Lỗi dùng chung nằm ở `OAuthService.complete_login` hoặc DB/session/JWT/CSRF config sau khi đã lấy identity từ provider.
  evidence: Container logs cho cả hai correlation_id cho thấy exception xảy ra sớm hơn, ngay trong `provider.authenticate(...)` tại lời gọi `client.get(..., token=token)`, trước khi route đi vào `OAuthService.complete_login`.
  timestamp: 2026-06-16T23:37:19+07:00

- hypothesis: Lỗi do sai client secret / redirect URI / token exchange với Google hoặc GitHub.
  evidence: Log cho cả hai provider đều có `POST .../token "HTTP/1.1 200 OK"`; token exchange thành công rồi mới nổ `TypeError` khi gọi endpoint userinfo/email.
  timestamp: 2026-06-16T23:37:19+07:00

## Resolution
root_cause: "Google và GitHub OAuth providers gọi `AsyncOAuth2Client.get(..., token=token)` sau `fetch_token()`, nhưng Authlib 1.7.2/httpx 0.28.1 không hỗ trợ keyword `token`, nên callback nổ `TypeError` và bị generic handler đổi thành `internal_error`."
fix: "Bỏ đối số `token=` khỏi các GET request trong OAuth providers để dùng token đã được lưu trên Authlib client sau `fetch_token()`, đồng thời thêm unit tests khóa lại contract này."
verification: "Backend logs chứng minh lỗi cũ là `TypeError` tại `client.get(..., token=token)` cho cả Google và GitHub. Sau fix, unit regression tests mới cho provider request construction pass, callback-focused Google/GitHub integration tests pass trong backend container (`11 passed, 1 deselected`), và runtime container hiện tại đã được restart với code patched không còn dùng `token=`."
files_changed:
  - "D:\\ADMIN\\Documents\\matmahoc\\@DO_AN\\Simpagent\\backend\\app\\identity\\providers\\google.py"
  - "D:\\ADMIN\\Documents\\matmahoc\\@DO_AN\\Simpagent\\backend\\app\\identity\\providers\\github.py"
  - "D:\\ADMIN\\Documents\\matmahoc\\@DO_AN\\Simpagent\\backend\\tests\\unit\\test_oauth_providers.py"
