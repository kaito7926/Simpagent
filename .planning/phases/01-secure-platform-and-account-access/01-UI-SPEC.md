---
phase: 1
slug: secure-platform-and-account-access
status: approved
shadcn_initialized: false
preset: none
created: 2026-06-08
---

# Phase 1 - UI Design Contract

> Visual and interaction contract for the Secure Platform and Account Access walking skeleton. This is the canonical Phase 1 UI source of truth for planning and implementation.

---

## Contract Intent

Phase 1 delivers one complete user journey:

1. See whether account access is ready, degraded, or unavailable.
2. Register without learning whether an account already exists.
3. Log in through the local identity provider.
4. See the authenticated current-user state returned by `/api/auth/me`.
5. Log out of the current refresh-token family.
6. Return safely to login when the session expires, is revoked, or cannot be refreshed.

This phase is an account-access walking skeleton, not a reduced chatbot. It must not introduce a chat sidebar, conversation list, message composer, model selector, tool controls, admin console, or fake future functionality.

The visual direction is a restrained security product for a Vietnamese university demonstration: calm, legible, technical enough to explain the security boundary, and free of "cyber" decoration.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | Small local React component set |
| Preset | Not applicable; `components.json` does not exist |
| Component library | Local semantic components built with React and Tailwind CSS |
| Optional upstream source | Official shadcn components only, if shadcn is initialized in a later implementation task |
| Third-party registry blocks | Forbidden |
| Icon library | Lucide React, outline icons only, `strokeWidth={1.75}` |
| Font | Be Vietnam Pro, self-hosted with `next/font/local`; fallback `system-ui, sans-serif` |
| Theme | Light theme only in Phase 1 |

### Component Strategy

Implement the smallest useful set. Components own semantics, focus behavior, and state styling; pages own data and copy.

| Component | Responsibility |
|-----------|----------------|
| `AccountAccessShell` | Full-height responsive page frame and two-column layout |
| `BrandLockup` | SimpAgent mark, product name, and phase descriptor |
| `PlatformStatus` | Aggregate readiness state and optional component details |
| `SecuritySummary` | Three concise statements explaining the session boundary |
| `AuthCard` | Login/register mode, inline alerts, and form content |
| `AuthModeSwitch` | Two-option accessible mode switch for login and registration |
| `FormField` | Label, input, hint, error, and `aria-describedby` wiring |
| `PasswordField` | Password input with text-only show/hide control |
| `ActionButton` | Primary, secondary, and quiet button variants |
| `InlineAlert` | Error, warning, information, and success messages |
| `DemoAccountPanel` | Development-only account-fill controls |
| `CurrentUserCard` | Safe current-user identity, role, status, and scopes |
| `StatusBadge` | Ready, degraded, unavailable, active, and role states |
| `ScopeList` | Human label plus exact scope code |

Do not create a generic application shell, sidebar, data table system, toast framework, modal framework, or dashboard abstraction in Phase 1.

### Visual Motif

Use a narrow "verification rail" as the distinctive motif:

- A 3px deep-teal vertical rule with small square nodes appears beside the desktop security summary.
- The same square node appears in readiness rows and the SimpAgent mark.
- Use the motif no more than three times on one viewport.
- Do not use shields, padlock hero illustrations, glowing effects, network maps, gradients, glassmorphism, or animated background grids.

---

## Spacing Scale

All layout spacing uses this scale:

| Token | Value | Usage |
|-------|-------|-------|
| `space-1` | 4px | Icon-to-label gap, validation offset |
| `space-2` | 8px | Compact inline gap, badge padding |
| `space-3` | 16px | Field spacing, mobile page padding |
| `space-4` | 24px | Card groups, tablet page padding |
| `space-5` | 32px | Card padding, section separation |
| `space-6` | 48px | Desktop column gap, large section break |
| `space-7` | 64px | Desktop page padding and top/bottom breathing room |

Exceptions:

- Interactive controls have a minimum target size of 44x44px.
- Text inputs and primary buttons are 48px high.
- The icon inside a control is 18px.
- Borders are 1px; the verification rail is 3px.
- Card radius is 16px, input/button radius is 10px, and badge radius is 999px.

Do not introduce arbitrary Tailwind spacing values outside this scale.

---

## Typography

Use exactly four text sizes and two weights.

| Role | Size | Weight | Line Height | Usage |
|------|------|--------|-------------|-------|
| Label / Meta | 14px | 400 or 600 | 1.45 | Labels, hints, status, badges, technical codes |
| Body | 16px | 400 or 600 | 1.55 | Paragraphs, inputs, buttons, alerts |
| Section Heading | 20px | 600 | 1.3 | Card and status headings |
| Page Heading | 28px | 600 | 1.2 | Main unauthenticated and authenticated headings |

Rules:

- Use weight 600 only for headings, labels, buttons, and the emphasized phrase within an alert.
- Never use all caps for sentences. The small product eyebrow may use uppercase with `letter-spacing: 0.08em`.
- Scope codes and account IDs use the normal font, not a separate monospace size. Apply `font-variant-numeric: tabular-nums` where useful.
- Text remains left-aligned. Do not center paragraphs or forms.
- Maximum prose line length is 62 characters on desktop.

---

## Color

### Core Palette

| Role | Value | Usage |
|------|-------|-------|
| Dominant 60% | `#F4F6F2` | Page canvas and quiet background |
| Secondary 30% | `#FFFFFF` | Auth card, identity card, status surfaces |
| Accent 10% | `#0B6B5D` | Primary CTA, focus ring, verification rail, active mode |
| Ink | `#16211D` | Primary text |
| Muted ink | `#53615B` | Supporting copy and metadata |
| Surface border | `#CAD4CE` | Card and separator border |
| Control border | `#7A857F` | Input and inactive control border; 3.83:1 contrast against `#FFFFFF` |
| Accent hover | `#085447` | Primary CTA hover |
| Accent soft | `#DCEFEA` | Active mode background and selected status treatment |
| Destructive | `#B42318` | Error text and destructive status only |
| Destructive soft | `#FFF1F0` | Error alert background |
| Warning | `#8A5A00` | Degraded status text |
| Warning soft | `#FFF6D8` | Degraded alert background |
| Success | `#166534` | Ready and successful completion text |
| Success soft | `#ECFDF3` | Ready and success alert background |

### Color Distribution

- 60% dominant canvas: full viewport background and the desktop context column.
- 30% secondary white: form card, authenticated identity card, and status detail surface.
- 10% accent: primary CTA, keyboard focus, active auth mode, verification rail, brand node, and selected demo-account button state.

Accent is reserved for those elements only. Links use ink with an accent underline on hover/focus. Do not color every icon, badge, border, or heading teal.

### Contrast and Focus

- Body and label text must meet WCAG 2.2 AA contrast.
- Focus uses a 2px `#0B6B5D` outline plus 2px offset. Never remove the native focus indication without replacing it.
- Status meaning must use icon, label, and copy in addition to color.
- Disabled controls use `#E7ECE8` background, `#7A857F` text, and retain readable contrast.

---

## Layout Contract

### Desktop: 1024px and Wider

- `min-height: 100dvh`.
- Content wrapper max width: 1184px.
- Page padding: 64px horizontal and 48px vertical.
- Two columns: 5fr context/status and 4fr auth/current-user content.
- Column gap: 64px.
- Auth card max width: 456px, aligned to the right column.
- The context column vertically centers the brand, heading, security summary, and platform state.
- The card has a 1px border and restrained shadow: `0 18px 48px rgb(22 33 29 / 0.08)`.

### Tablet: 640px to 1023px

- Single column, max width 640px.
- Page padding: 32px.
- Brand and aggregate status appear above the card.
- Security summary becomes a horizontal three-item row when space permits.
- Component status details follow the card, not between heading and form.

### Mobile: Below 640px

- Single column with 16px horizontal and 24px vertical padding.
- Card is full width with 24px internal padding.
- Page heading remains 28px.
- The extended security summary is collapsed into one sentence:
  `Phiên được bảo vệ bằng mã truy cập ngắn hạn, cookie HttpOnly và kiểm tra quyền phía máy chủ.`
- Platform status shows aggregate state first; component details are behind a native `details` disclosure labeled `Xem trạng thái thành phần`.
- Auth mode options each occupy half the available width.
- Buttons are full width except the password visibility control.
- No horizontal scrolling at 320px viewport width.

### Authenticated State

- Preserve the same brand and platform-status context.
- Replace `AuthCard` with `CurrentUserCard`; do not navigate to a dashboard shell.
- The identity card max width is 640px.
- On desktop, scopes render in two columns. On mobile, render one column.
- Keep logout below identity details and visually separate it with a border-top and 24px spacing.

---

## Information Architecture

Phase 1 uses one public frontend route, `/`, with explicit UI states:

| State | Main content |
|-------|--------------|
| `checking_session` | Session restoration card |
| `anonymous_login` | Login form |
| `anonymous_register` | Registration form |
| `registration_accepted` | Generic acceptance message plus return-to-login action |
| `authenticated` | Current-user identity and logout |
| `session_expired` | Login form with session-expired alert |
| `core_not_ready` | Disabled account controls plus retry action |

Login is the default anonymous mode. Registration is selected with `?mode=register`; switching modes uses history replacement, retains the email value, and clears all password values and field errors.

The page title values are:

- Login: `Đăng nhập | SimpAgent`
- Registration: `Đăng ký | SimpAgent`
- Authenticated: `Tài khoản của bạn | SimpAgent`
- Not ready: `Hệ thống chưa sẵn sàng | SimpAgent`

---

## Platform Readiness Contract

Fetch `/ready` on initial load. Refresh it every 60 seconds only while the document is visible, and immediately when the user activates `Kiểm tra lại`.

### Aggregate Mapping

| API result | UI state | Forms |
|------------|----------|-------|
| `200`, `status=ready` | Ready | Enabled |
| `200`, `status=degraded` | Degraded | Enabled |
| `503`, `status=not_ready` | Not ready | Disabled |
| Network error or malformed unknown state | Cannot connect | Disabled, fail closed |

### Exact Aggregate Copy

| State | Label | Body |
|-------|-------|------|
| Loading | `Đang kiểm tra hệ thống` | `Vui lòng chờ trong giây lát.` |
| Ready | `Sẵn sàng` | `Đăng ký và đăng nhập đang hoạt động.` |
| Degraded | `Hoạt động giới hạn` | `Tài khoản vẫn hoạt động; một số dịch vụ AI chưa được cấu hình hoặc đang tạm gián đoạn.` |
| Not ready | `Chưa sẵn sàng` | `Đăng nhập tạm thời không khả dụng. Hãy đợi hệ thống hoàn tất khởi động rồi thử lại.` |
| Cannot connect | `Không thể kết nối` | `Không đọc được trạng thái nền tảng. Kiểm tra hệ thống đang chạy rồi thử lại.` |

Degraded state must not block registration, login, current-user retrieval, refresh, or logout when core auth and storage are ready.

### Component Labels

Render only the sanitized state supplied by `/ready`.

| API component | Vietnamese label |
|---------------|------------------|
| `database` | `Cơ sở dữ liệu` |
| `migrations` | `Cấu trúc dữ liệu` |
| `llm` | `Dịch vụ trò chuyện AI` |
| `search` | `Tìm kiếm có căn cứ` |
| `sandbox` | `Nền tảng Python giới hạn` |

| API state | Display label |
|-----------|---------------|
| `ready` | `Sẵn sàng` |
| `foundation_ready` | `Nền tảng sẵn sàng` |
| `unconfigured` | `Chưa cấu hình` |
| `model_unavailable` | `Mô hình không khả dụng` |
| `unavailable` | `Không khả dụng` |
| `out_of_date` | `Chưa cập nhật` |
| `unknown` or unrecognized | `Không xác định` |

Never display provider endpoints, model IDs, exception strings, stack traces, credential filenames, database addresses, secret names, or raw readiness JSON.

---

## Authentication Form Contract

### Shared Behavior

- Submit with a semantic `<form>` and Enter key.
- Use `noValidate`; render consistent client validation while retaining server authority.
- Place the first validation summary directly below the form heading.
- On failed submit, focus the alert summary; on field validation, focus the first invalid field.
- Disable submit only while submitting or while core readiness is unavailable.
- Do not disable inputs merely because they contain invalid values.
- Clear password values after any server error, registration acceptance, mode switch, session expiry, or logout.
- Never trim, log, persist, cache, replay, or place passwords in URLs.
- Keep the access token in memory only. Never use `localStorage`, `sessionStorage`, IndexedDB, URL parameters, or non-HttpOnly cookies for bearer tokens.
- Protected API fetches use one shared in-memory refresh promise and retry the original request at most once.
- All auth and current-user requests use `cache: "no-store"`.

### Login Form

Heading: `Đăng nhập vào SimpAgent`

Supporting copy:
`Sử dụng tài khoản cục bộ để mở một phiên được bảo vệ.`

Fields:

| Field | Label | Attributes | Error copy |
|-------|-------|------------|------------|
| Email | `Email` | `type=email`, `inputMode=email`, `autoComplete=email` | `Nhập địa chỉ email hợp lệ.` |
| Password | `Mật khẩu` | `type=password`, `autoComplete=current-password` | `Nhập mật khẩu.` |

Primary CTA: `Đăng nhập`

Submitting CTA: `Đang đăng nhập...`

Mode prompt: `Chưa có tài khoản?`

Mode action: `Đăng ký`

Generic authentication error for unknown email, wrong password, inactive account, or invalid local identity:

`Không thể đăng nhập bằng thông tin đã cung cấp. Kiểm tra lại email và mật khẩu rồi thử lại.`

Do not use different status text, field decoration, timing messages, or follow-up actions for those cases.

### Registration Form

Heading: `Tạo tài khoản`

Supporting copy:
`Tài khoản mới nhận quyền Người dùng tiêu chuẩn. Vai trò và quyền không thể chọn trong biểu mẫu này.`

Fields:

| Field | Label | Attributes | Error copy |
|-------|-------|------------|------------|
| Email | `Email` | `type=email`, `inputMode=email`, `autoComplete=email` | `Nhập địa chỉ email hợp lệ.` |
| Password | `Mật khẩu` | `type=password`, `autoComplete=new-password` | See password errors below |
| Confirmation | `Nhập lại mật khẩu` | `type=password`, `autoComplete=new-password` | `Mật khẩu nhập lại chưa khớp.` |

Password hint:

`Từ 15 đến 128 ký tự; cho phép khoảng trắng và tiếng Việt. Không bắt buộc chữ hoa, số hoặc ký hiệu.`

Password errors:

| Condition | Copy |
|-----------|------|
| Empty | `Nhập mật khẩu.` |
| Fewer than 15 Unicode code points after NFC normalization | `Mật khẩu cần ít nhất 15 ký tự.` |
| More than 128 Unicode code points | `Mật khẩu không được vượt quá 128 ký tự.` |
| Server blocklist rejection | `Mật khẩu này quá phổ biến hoặc dễ đoán. Hãy chọn mật khẩu khác.` |
| Other safe validation rejection | `Mật khẩu chưa đáp ứng yêu cầu. Hãy chọn mật khẩu khác.` |

The confirmation field is client-only and is never included in the API request.

Primary CTA: `Gửi yêu cầu đăng ký`

Submitting CTA: `Đang gửi yêu cầu...`

Mode prompt: `Đã có tài khoản?`

Mode action: `Đăng nhập`

### Registration Acceptance

For both a newly inserted account and a normalized duplicate, show the same layout, status, and copy:

Heading: `Yêu cầu đã được tiếp nhận`

Body:
`Nếu địa chỉ này có thể đăng ký, bạn có thể tiếp tục đăng nhập.`

Primary CTA: `Chuyển sang đăng nhập`

Do not automatically log in, return a user ID, announce account creation, say the email already exists, or change the copy based on backend insertion outcome.

### Password Visibility

- Use a text button labeled `Hiện mật khẩu`; its active label is `Ẩn mật khẩu`.
- Include the current action in `aria-label`.
- Preserve cursor position and field focus when toggling.
- Do not use an unlabeled eye icon.
- Registration password and confirmation visibility controls operate independently.

---

## Session Lifecycle Contract

### Initial Restoration

On first render, show:

Heading: `Đang kiểm tra phiên`

Body: `SimpAgent đang xác nhận phiên được bảo vệ trên thiết bị này.`

The region uses `aria-busy=true` and a non-looping CSS spinner. Do not render the login form briefly before restoration completes.

An initial refresh `401` for a visitor is treated as anonymous and does not show an expired-session warning.

### Authenticated Current-User State

Heading: `Bạn đã đăng nhập`

Supporting copy:
`Đây là thông tin an toàn mà máy chủ cho phép hiển thị cho tài khoản hiện tại.`

Field labels:

| Field | Label |
|-------|-------|
| `email` | `Email` |
| `id` | `Mã tài khoản` |
| `role=user` | `Người dùng` |
| `role=admin` | `Quản trị viên` |
| `is_active=true` | `Đang hoạt động` |
| scopes | `Quyền được cấp` |

Scope labels:

| Scope | Human label |
|-------|-------------|
| `chat:read` | `Đọc hội thoại` |
| `chat:write` | `Tạo và cập nhật hội thoại` |
| `tool:websearch` | `Dùng tìm kiếm web` |
| `tool:python` | `Dùng Python giới hạn` |
| `admin:read` | `Xem dữ liệu quản trị` |
| `admin:write` | `Thay đổi dữ liệu quản trị` |

Show the human label and exact scope code together. Unknown role or scope must not be rendered as a permissive generic badge. Treat it as an invalid session, clear in-memory auth state, and return to login.

Phase boundary note:

Heading: `Nền tảng tài khoản đã sẵn sàng`

Body:
`Giao diện trò chuyện và các công cụ tác tử sẽ được bổ sung ở giai đoạn sau.`

Logout action: `Đăng xuất`

Logout submitting state: `Đang đăng xuất...`

Logout revokes only the current session family. It does not ask for confirmation because no user data is deleted.

### Logout Outcomes

Success alert on the login form:

`Bạn đã đăng xuất khỏi phiên hiện tại.`

Network/server failure while logging out:

`Không thể hoàn tất đăng xuất. Hãy kiểm tra kết nối và thử lại.`

On logout failure, keep the authenticated card visible, preserve the in-memory access token until it naturally expires or logout succeeds, and provide `Thử đăng xuất lại`. Do not claim the server session was revoked.

### Session Expiry, Revocation, or Replay

When an authenticated request returns `401`:

1. Enter the shared single-flight refresh flow.
2. Retry the original request exactly once after successful refresh.
3. If refresh fails for any reason, clear access token and protected client state.
4. Return to login and focus the alert.

Alert heading: `Phiên đã kết thúc`

Alert body:
`Phiên của bạn không còn hợp lệ. Vui lòng đăng nhập lại để tiếp tục.`

Primary action: `Đăng nhập lại`

Use the same copy for expiry, revocation, refresh replay, inactive account, and unknown authorization state. Do not tell an unauthenticated user that replay was detected or reveal the internal denial reason.

---

## Demo Account Contract

The demo affordance exists only when both conditions are true:

- `APP_ENV=development`
- `DEMO_SEED_ENABLED=true`

It must be gated server-side or at build/runtime configuration before rendering. In production:

- Do not render the component.
- Do not leave account values in HTML, React Server Component payloads, source maps, hidden elements, comments, or client bundles.
- Do not reserve empty layout space for it.

Panel heading: `Tài khoản demo cục bộ`

Panel body:
`Chỉ dùng cho bản demo phát triển trên máy này. Không sử dụng các thông tin này ở môi trường thật.`

Actions:

- `Điền tài khoản Người dùng`
- `Điền tài khoản Quản trị viên`

Activating an action fills the login email and password from development-only configuration, moves focus to the login CTA, and announces:

- `Đã điền tài khoản demo Người dùng.`
- `Đã điền tài khoản demo Quản trị viên.`

The action must not submit automatically. Never hardcode demo passwords in the component source or this UI contract.

---

## Loading, Error, and Success States

Use inline state near the affected surface. Do not add a toast dependency in Phase 1.

| Condition | Exact copy | Recovery |
|-----------|------------|----------|
| Auth request network failure | `Không thể kết nối đến máy chủ. Kiểm tra hệ thống đang chạy rồi thử lại.` | `Thử lại` |
| Unexpected server failure | `Đã xảy ra lỗi phía máy chủ. Vui lòng thử lại.` | `Thử lại` |
| Safe correlation ID available | `Mã tham chiếu: {correlationId}` | Display below unexpected error only |
| Rate limited | `Bạn đã thử quá nhiều lần. Vui lòng đợi {retryAfter} giây rồi thử lại.` | Disable submit until countdown ends |
| Origin rejected | `Yêu cầu không được chấp nhận từ địa chỉ hiện tại. Hãy mở ứng dụng từ URL đã được cấu hình.` | No automatic retry |
| Current-user fetch pending | `Đang tải thông tin tài khoản...` | Keep card skeleton-free and stable |
| Readiness recovered | `Hệ thống đã sẵn sàng cho đăng ký và đăng nhập.` | Auto-dismiss after 6 seconds unless focused |
| Empty readiness details | `Chưa có dữ liệu trạng thái thành phần.` | `Kiểm tra lại` |

Rules:

- Error alerts use `role=alert`.
- Non-urgent loading and success text uses one `aria-live=polite` region.
- Never place secrets, request bodies, raw server messages, stack traces, or provider responses in UI errors.
- Do not show more than one global alert and one field error per field.
- Button labels change during submission; layout width must not shift.
- Use a 16px spinner beside loading button text, not in place of the text.

---

## Copywriting Contract

| Element | Exact copy |
|---------|------------|
| Product name | `SimpAgent` |
| Eyebrow | `TRUY CẬP AN TOÀN` |
| Desktop context heading | `Một điểm vào rõ ràng cho tài khoản và phiên.` |
| Desktop context body | `Giai đoạn này chứng minh đăng ký, đăng nhập, phiên làm mới được bảo vệ và trạng thái danh tính hiện tại.` |
| Primary login CTA | `Đăng nhập` |
| Primary registration CTA | `Gửi yêu cầu đăng ký` |
| Empty state heading | `Chưa có dữ liệu trạng thái` |
| Empty state body | `Hãy kiểm tra lại sau khi hệ thống hoàn tất khởi động.` |
| Generic error | `Đã xảy ra lỗi phía máy chủ. Vui lòng thử lại.` |
| Destructive confirmation | None; Phase 1 has no destructive data action |

Security summary:

| Heading | Body |
|---------|------|
| `Mã truy cập ngắn hạn` | `Mã truy cập chỉ được giữ trong bộ nhớ của giao diện.` |
| `Cookie được bảo vệ` | `Phiên làm mới không khả dụng cho JavaScript.` |
| `Máy chủ là nguồn quyết định` | `Vai trò, quyền và trạng thái tài khoản được kiểm tra lại phía máy chủ.` |

Do not claim that the local password login is OAuth2 login, an OpenID Provider, or a complete OIDC implementation. The UI may say `Kiến trúc danh tính sẵn sàng để thay thế bằng nhà cung cấp OIDC trong tương lai.` only in an educational information disclosure, never as an active login option.

---

## Accessibility Contract

- Target WCAG 2.2 AA.
- Use semantic `main`, `section`, `form`, `fieldset`, `label`, `button`, and `details` elements before ARIA. For non-urgent status updates, use `<div role="status" aria-live="polite">`; reserve `role="alert"` or `aria-live="assertive"` for urgent errors requiring immediate attention.
- Include a visible-on-focus skip link: `Bỏ qua đến nội dung tài khoản`.
- Heading order is one `h1`, then `h2`; do not skip levels.
- Auth mode switch uses buttons with `aria-pressed`, not clickable `div` elements.
- Every input has a persistent visible label. Placeholder text is optional and never replaces the label.
- Required fields use text `Bắt buộc` in the accessible description; do not rely on an asterisk alone.
- Validation associates input, hint, and error through stable IDs.
- Keyboard order follows visual order.
- Status icons use `aria-hidden=true`; the text carries meaning.
- Motion duration is 150ms for controls and 200ms for card transitions. Under `prefers-reduced-motion: reduce`, remove translation and spinner rotation; retain a textual loading state.
- Do not auto-focus on initial page load. Focus only after a user action, failed submission, or forced session transition.
- Browser zoom to 200% must not hide actions or create horizontal scrolling at 1280px CSS viewport.
- Touch targets are at least 44x44px with 8px separation where adjacent.

---

## Interaction Details

### Auth Mode Switch

- Two equal buttons: `Đăng nhập` and `Đăng ký`.
- Active mode uses accent-soft background, accent text, and a 2px bottom inset indicator.
- Switching mode retains email, clears passwords, errors, and success messages, and updates the document title.
- Browser Back restores the previous mode without resubmitting.

### Form Submission

- Prevent duplicate submit while a request is pending.
- Preserve email after generic login failure.
- Clear password after generic login failure.
- Do not show a success animation after login; transition directly to current-user state after `/me` succeeds.
- If login succeeds but `/me` fails, run the session-invalid flow rather than rendering partial claims from the access token.
- Never derive displayed role or scopes by decoding an unverified JWT in the browser. Render only `/api/auth/me`.

### Readiness Disclosure

- Aggregate status is always visible.
- Component details are expanded by default on desktop only when degraded or not ready.
- On mobile, details are always collapsed initially.
- Opening the disclosure does not trigger additional provider calls.
- `Kiểm tra lại` is a secondary button with a refresh icon and textual label.

---

## Responsive State Matrix

| Element | Mobile | Tablet | Desktop |
|---------|--------|--------|---------|
| Brand lockup | Above card | Above card | Context column |
| Security summary | One sentence | Three compact items | Vertical verification rail |
| Aggregate readiness | Above card | Above card | Context column |
| Component readiness | Collapsed disclosure | Below card | Expanded when degraded |
| Auth card | Full width | Max 560px | Max 456px |
| Demo account actions | Stacked | Two columns | Stacked inside card |
| Current-user scopes | One column | Two columns | Two columns |
| Logout action | Full width | Right aligned, min 160px | Right aligned, min 160px |

---

## What Must Not Be Shown

The Phase 1 UI must not display or expose:

- Access tokens, refresh tokens, CSRF values, JWT headers, JWT `jti`, signing key IDs, or decoded token payloads.
- Password hashes, identity-provider subjects, refresh family IDs, refresh token IDs, or replay evidence.
- Database URLs, hostnames, container IPs, private service ports, provider API endpoints, API keys, model response bodies, secret filenames, or environment dumps.
- Raw backend exceptions, stack traces, SQL errors, validation internals, unknown policy values, or raw readiness JSON.
- Whether a registration email already exists.
- Whether login failed because of unknown email, wrong password, inactive account, role mismatch, or refresh replay.
- Role or scope selectors during registration.
- "Remember me", password reset, email verification, social login, OIDC login, MFA, session/device management, or logout-all controls.
- Chat messages, conversation navigation, prompt input, model selector, search toggle, Python toggle, tool logs, citations, or fake placeholder controls for later phases.
- Admin navigation, user lists, audit logs, security-event screens, gateway metrics, or rate-limit dashboards.
- A production demo-account panel or production default administrator credential.
- Raw HTML from any API response.

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| Local project components | Components listed in this contract | Source is authored and reviewed in-repository |
| shadcn official | None required by this contract | Allowed only from the official shadcn registry after initialization |
| Third-party registries | None | Prohibited by user decision on 2026-06-08 |

If implementation later initializes shadcn, it may use only official primitive components equivalent to Button, Input, Label, Card, Alert, Badge, Separator, Tabs, and Collapsible. Do not import full auth blocks, dashboard blocks, or any third-party registry package.

---

## Acceptance Checklist

### Visual

- [ ] Uses the declared Be Vietnam Pro typography, four sizes, and two weights only.
- [ ] Uses the declared 60/30/10 palette and reserved accent list.
- [ ] Uses the verification rail motif without decorative security clichés.
- [ ] Matches mobile, tablet, desktop, and authenticated layouts.

### Interaction

- [ ] Registration and login work as one real Phase 1 interaction.
- [ ] Duplicate registration remains indistinguishable in status, copy, and layout.
- [ ] Current-user UI is rendered only from `/api/auth/me`.
- [ ] Readiness clearly distinguishes ready, degraded, not ready, and disconnected.
- [ ] Degraded AI providers do not block account access.
- [ ] Session restoration prevents login-form flash.
- [ ] Refresh uses a single-flight promise and one retry.
- [ ] Session failure returns to login with generic exact copy.
- [ ] Logout revokes only the current family and reports failure honestly.
- [ ] Demo controls exist only in explicitly enabled development mode.

### Security

- [ ] No token is written to browser persistence.
- [ ] No secret or raw diagnostic appears in copy, HTML, payloads, or hidden UI.
- [ ] Registration has no role/scope input.
- [ ] Unknown current-user roles/scopes fail closed.
- [ ] No Phase 2 or later product surface is implied to work.

### Accessibility

- [ ] Full keyboard operation and visible focus.
- [ ] Labels, hints, and errors are programmatically associated.
- [ ] Status never relies on color alone.
- [ ] Loading and alert announcements use appropriate live regions.
- [ ] 44px minimum targets, 200% zoom support, and reduced-motion support pass.

---

## Source Traceability

| Source | Decisions Applied |
|--------|-------------------|
| `01-CONTEXT.md` | Fixed User scopes, active default accounts, development-only demo User/Admin, no production default Admin |
| `01-RESEARCH.md` | Ten-minute in-memory access token, protected refresh cookie, single-flight refresh, generic registration/login/session failures, `/me` safe fields, readiness/degraded mapping |
| `REQUIREMENTS.md` | Registration, login, refresh, logout, current-user identity, inactive/unknown-state fail-closed behavior |
| `ROADMAP.md` | Phase 1 walking-skeleton boundary and exclusion of chat/tools/admin UI |
| `AGENTS.md` | Next.js/TypeScript/Tailwind stack, Vietnamese user-facing content, no secret exposure, no browser token persistence |
| `prompt.md` | University-demo context and final product direction without pulling later-phase features into Phase 1 |

---

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: PASS
- [x] Dimension 4 Typography: PASS
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS

**Approval:** approved 2026-06-08
