# Phase 5: gateway-administration-and-security-evidence - Pattern Map

**Mapped:** 2026-06-15
**Files analyzed:** 46
**Analogs found:** 46 / 46

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `backend/app/api/routes/auth_oauth.py` | route | request-response | `backend/app/api/routes/auth.py` | role-match |
| `backend/app/identity/oauth_service.py` | service | request-response | `backend/app/services/authentication.py` | partial |
| `backend/app/identity/providers/google.py` | provider | request-response | `backend/app/identity/local_provider.py` | role-match |
| `backend/app/identity/providers/github.py` | provider | request-response | `backend/app/identity/local_provider.py` | role-match |
| `backend/app/db/repositories/accounts.py` | repository | CRUD | `backend/app/db/repositories/accounts.py` | exact |
| `backend/app/core/config.py` | config | transform | `backend/app/core/config.py` | exact |
| `backend/app/core/provider_status.py` | utility | transform | `backend/app/core/provider_status.py` | exact |
| `backend/app/schemas/health.py` | model | request-response | `backend/app/schemas/health.py` | exact |
| `backend/app/api/routes/health.py` | route | request-response | `backend/app/api/routes/health.py` | exact |
| `backend/app/main.py` | middleware | request-response | `backend/app/main.py` | exact |
| `backend/app/identity/redaction.py` | utility | transform | `backend/app/core/logging.py` | partial |
| `backend/app/schemas/admin.py` | model | request-response | `backend/app/schemas/admin.py` | exact |
| `backend/app/db/repositories/admin.py` | repository | CRUD | `backend/app/db/repositories/admin.py` | exact |
| `backend/app/services/admin_evidence.py` | service | CRUD | `backend/app/services/admin_evidence.py` | exact |
| `backend/app/api/routes/admin.py` | route | request-response | `backend/app/api/routes/admin.py` | exact |
| `backend/alembic/versions/0005_phase5_oauth_gateway_admin.py` | migration | batch | `backend/alembic/versions/0001_account_access.py` | role-match |
| `kong/kong.yml` | config | request-response | `kong/kong.yml` | exact |
| `compose.yaml` | config | batch | `compose.yaml` | exact |
| `frontend/lib/admin-api.ts` | utility | request-response | `frontend/lib/admin-api.ts` | exact |
| `frontend/lib/auth-session.ts` | utility | request-response | `frontend/lib/auth-session.ts` | exact |
| `frontend/lib/readiness.ts` | utility | transform | `frontend/lib/readiness.ts` | exact |
| `frontend/components/account-access/AuthCard.tsx` | component | request-response | `frontend/components/account-access/AuthCard.tsx` | exact |
| `frontend/components/account-access/AccountAccessShell.tsx` | component | request-response | `frontend/components/account-access/AccountAccessShell.tsx` | exact |
| `frontend/components/chat/ChatWorkspace.tsx` | component | request-response | `frontend/components/chat/ChatWorkspace.tsx` | exact |
| `frontend/components/chat/ChatSidebar.tsx` | component | request-response | `frontend/components/chat/ChatSidebar.tsx` | exact |
| `frontend/components/settings/SettingsPage.tsx` | component | request-response | `frontend/components/settings/SettingsPage.tsx` | exact |
| `backend/tests/integration/auth/test_oauth_flows.py` | test | request-response | `backend/tests/integration/auth/test_login.py` | role-match |
| `backend/tests/integration/auth/test_google_oauth.py` | test | request-response | `backend/tests/integration/auth/test_login.py` | role-match |
| `backend/tests/integration/auth/test_github_oauth.py` | test | request-response | `backend/tests/integration/auth/test_login.py` | role-match |
| `backend/tests/integration/auth/test_oauth_account_linking.py` | test | CRUD | `backend/tests/integration/auth/test_login.py` | partial |
| `backend/tests/integration/gateway/test_cors.py` | test | request-response | `backend/tests/smoke/test_topology.py` | partial |
| `backend/tests/integration/gateway/test_rate_limits.py` | test | request-response | `backend/tests/smoke/test_logging_flow.py` | partial |
| `backend/tests/integration/gateway/test_request_size_and_correlation.py` | test | request-response | `backend/tests/smoke/test_logging_flow.py` | partial |
| `backend/tests/integration/gateway/test_production_profile.py` | test | request-response | `backend/tests/unit/test_config.py` | partial |
| `backend/tests/integration/admin/test_admin_evidence.py` | test | request-response | `backend/tests/integration/admin/test_admin_evidence.py` | exact |
| `backend/tests/unit/test_admin_evidence_service.py` | test | transform | `backend/tests/unit/test_admin_evidence_service.py` | exact |
| `backend/tests/unit/test_config.py` | test | transform | `backend/tests/unit/test_config.py` | exact |
| `backend/tests/unit/test_logging.py` | test | transform | `backend/tests/unit/test_logging.py` | exact |
| `backend/tests/security/test_secret_leakage.py` | test | request-response | `backend/tests/security/test_secret_leakage.py` | exact |
| `backend/tests/smoke/test_admin_flow.py` | test | request-response | `backend/tests/smoke/test_admin_flow.py` | exact |
| `backend/tests/smoke/test_oauth_google_flow.py` | test | request-response | `backend/tests/smoke/test_topology.py` | partial |
| `backend/tests/smoke/test_oauth_github_flow.py` | test | request-response | `backend/tests/smoke/test_topology.py` | partial |
| `frontend/tests/account-access-oauth.test.tsx` | test | request-response | `frontend/tests/auth-session.test.ts` | role-match |
| `frontend/tests/admin-evidence.test.tsx` | test | request-response | `frontend/tests/chat-workspace.test.ts` | role-match |
| `README.md` | config | file-I/O | `README.md` | exact |
| `.env.example` | config | file-I/O | `backend/app/core/config.py` | partial |

## Pattern Assignments

### `backend/app/api/routes/auth_oauth.py` (route, request-response)

**Primary analog:** `backend/app/api/routes/auth.py`

**Imports + router shape** (`backend/app/api/routes/auth.py:6-20`):
```python
from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import ApiError
from app.db.session import get_session

router = APIRouter(prefix="/api/auth", tags=["auth"])
```

**Cookie/session reuse pattern** (`backend/app/api/routes/auth.py:31-50`, `100-107`, `133-140`):
```python
def _set_auth_cookies(response: Response, *, settings: Settings, refresh_token: str, csrf_token: str, max_age: int) -> None:
    response.set_cookie(... httponly=True ...)
    response.set_cookie(... httponly=False ...)
```
Use the same helper shape after successful OAuth callback so OAuth lands in the same refresh-cookie + CSRF-cookie model as local login.

**Error envelope pattern** (`backend/app/core/errors.py:41-57`):
```python
async def api_error_handler(request: Request, exc: ApiError) -> ErrorEnvelope:
    return ErrorEnvelope(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        correlation_id=getattr(request.state, "correlation_id", None),
        extra=exc.extra,
    )
```
Raise `ApiError` for fail-closed OAuth states instead of returning ad-hoc JSON.

**Route inclusion pattern** (`backend/app/main.py:108-114`):
```python
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(chat.router)
```
Add the OAuth router in `main.py` the same way; do not inline route handlers there.

**Closest secondary analog:** `backend/app/api/routes/health.py:20-50`
- Use the same `request.app.state.*` access pattern for capability state and settings-derived response data.

---

### `backend/app/identity/providers/google.py` and `backend/app/identity/providers/github.py` (provider, request-response)

**Primary analog:** `backend/app/identity/local_provider.py`

**Contract shape** (`backend/app/identity/contracts.py:7-17`):
```python
@dataclass(frozen=True)
class VerifiedIdentity:
    issuer: str
    subject: str
    email: str | None
    email_verified: bool
    authentication_method: str
```
New provider adapters should return `VerifiedIdentity` and nothing route-specific.

**Provider class pattern** (`backend/app/identity/local_provider.py:29-39`):
```python
class LocalIdentityProvider(IdentityProvider):
    def __init__(self, session: AsyncSession) -> None:
        self._repository = AccountsRepository(session)

    async def authenticate(self, request: object) -> VerifiedIdentity:
        if not isinstance(request, LocalAuthRequest):
            raise TypeError(...)
```
Keep provider-specific request types and type-guard them up front.

**Credential/result decision pattern** (`backend/app/identity/local_provider.py:41-66`):
```python
async def check_credentials(self, request: LocalAuthRequest) -> AuthenticationDecision:
    bundle = await self._repository.get_user_bundle_by_email(request.email)
    ...
    return AuthenticationDecision(
        verified_identity=VerifiedIdentity(...),
        user_id=bundle.user.id,
        ...
    )
```
Mirror this shape for OAuth adapters: build a provider-specific request/result object, then return `VerifiedIdentity` plus any provider metadata needed by `oauth_service`.

**Match note:** GitHub has no exact analog for "token exchange + email fetch" in the repo. Reuse the provider contract, not the local-auth internals.

---

### `backend/app/identity/oauth_service.py` (service, request-response)

**Primary analogs:**
- `backend/app/services/authentication.py`
- `backend/app/services/sessions.py`
- `backend/app/db/repositories/accounts.py`

**Session issuance pattern** (`backend/app/services/authentication.py:47-98`):
```python
async def login(self, *, email: str, password: str, origin: str | None, now: datetime) -> LoginOutcome:
    require_allowed_origin(origin, self.settings)
    async with self.session.begin():
        ...
        access_token = issue_access_token(...)
        family = await self.sessions.create_family(...)
        refresh_token = generate_refresh_token()
        await self.sessions.create_token(...)
```
OAuth success should end by calling the same token-family creation pattern instead of creating a second browser session model.

**Refresh-replay / family semantics** (`backend/app/services/sessions.py:63-88`):
```python
token = await self.sessions.get_token_by_hash_for_update(token_hash)
family = await self.sessions.get_family_for_update(token.family_id)
...
await self.sessions.revoke_family(family, now=now, reason="refresh_reuse")
await self.sessions.add_security_event(... metadata={"family_id": str(family.id)})
```
Any OAuth login path that creates sessions must stay compatible with the existing rotation/replay model.

**Email normalization + identity persistence** (`backend/app/db/repositories/accounts.py:28-30`, `86-96`):
```python
def normalize_email(email: str) -> tuple[str, str]:
    normalized = validate_email(...).normalized
    email_key = normalized.casefold()
    return normalized, email_key

async def create_identity(self, *, user_id: UUID, issuer: str, subject: str, email_at_provider: str | None, email_verified: bool) -> Identity:
```
Link/provision using normalized email only after verified-email checks; persist provider identity by `issuer` + `subject`.

**Identity storage constraint** (`backend/app/models/account.py:49-58`):
```python
class Identity(Base):
    __table_args__ = (UniqueConstraint("issuer", "subject", name="uq_identities_issuer_subject"),)
```
Do not invent a second provider-identity table unless the plan proves the existing table is insufficient.

**Existing local-link helper pattern** (`backend/app/identity/account_linker.py:17-35`):
```python
class AccountLinker:
    async def link_local_identity(...):
        identity = await self._repository.create_identity(...)
        return VerifiedIdentity(...)
```
OAuth linking should follow the same repository-first pattern.

---

### `backend/app/db/repositories/accounts.py` and `backend/alembic/versions/0005_phase5_oauth_gateway_admin.py` (repository + migration)

**Repository analog:** `backend/app/db/repositories/accounts.py`

**Bundle loading pattern** (`backend/app/db/repositories/accounts.py:38-69`):
```python
stmt = (
    select(User)
    .options(
        selectinload(User.scopes),
        selectinload(User.identities),
        selectinload(User.local_credential),
    )
    .where(User.email_key == email_key)
)
```
Add any provider-subject lookup with the same `UserBundle` loading shape so callers always get user + scopes + identities together.

**Scope replacement pattern** (`backend/app/db/repositories/accounts.py:111-127`):
```python
async def replace_bundle_scopes(self, bundle: UserBundle, scopes: list[str]) -> None:
    ...
    await self.session.flush()
```
If OAuth provisioning needs standard scopes, reuse this exact replacement logic instead of hand-editing rows.

**Migration style analog 1** (`backend/alembic/versions/0001_account_access.py:18-120`):
- Create tables/constraints explicitly with `op.create_table`, named constraints, JSONB defaults, and indices.

**Migration style analog 2** (`backend/alembic/versions/0004_agent_runtime_settings.py:14-33`):
```python
op.create_table(
    "agent_runtime_settings",
    sa.Column("key", sa.String(length=64), nullable=False),
    ...
)
```
For small targeted Phase 5 schema additions, prefer the short explicit style from `0004`.

---

### `backend/app/core/config.py`, `backend/app/core/provider_status.py`, `backend/app/schemas/health.py`, `backend/app/api/routes/health.py`, `backend/app/main.py`, `.env.example` (config + readiness surface)

**Settings field pattern** (`backend/app/core/config.py:131-180`):
```python
llm_api_base: str | None = Field(... validation_alias=AliasChoices(...))
llm_api_key: SecretStr | None = Field(...)
...
search_model: str | None = None
provider_check_timeout_seconds: int = 2
```
Add OAuth/public-URL/trusted-proxy fields the same way: typed settings, alias support, and secret-file resolution where appropriate.

**Production validation pattern** (`backend/app/core/config.py:195-234`):
```python
if self.app_env == "production":
    if self.debug:
        raise ValueError(...)
    if not self.cookie_secure:
        raise ValueError(...)
    if "*" in self.allowed_origins:
        raise ValueError(...)
```
Put OAuth redirect URL, trusted proxy, secure-cookie, and public-origin hardening in the same validator block.

**Secret resolution pattern** (`backend/app/core/config.py:35-40`, `244-289`):
```python
def _resolve_secret_value(secret: SecretStr | None, file_path: str | None) -> str | None:
    ...
```
Environment template entries should mirror these names and `_FILE` fallbacks.

**Provider-status helper pattern** (`backend/app/core/provider_status.py:23-64`):
```python
def llm_status(...): ...
def search_status(...): ...
def compute_provider_snapshot(...):
    return ProviderSnapshot(...)
```
Add OAuth provider readiness as another computed capability, not as ad-hoc route logic.

**Readiness schema pattern** (`backend/app/schemas/health.py:8-25`):
```python
AggregateStatus = Literal["ready", "degraded", "not_ready"]
class ReadinessComponents(BaseModel):
    database: DatabaseStatus
    migrations: MigrationStatus
```
Extend the typed schema instead of returning untyped provider flags.

**Readiness route pattern** (`backend/app/api/routes/health.py:20-50`):
```python
providers = compute_provider_snapshot(settings, search_override=search_override)
components = ReadinessComponents(...)
if database_status != "ready":
    ... 503 ...
if providers.llm != "ready" or providers.search != "ready":
    ... degraded ...
```
Add OAuth capability data here so the frontend can hide/disable provider buttons from backend truth.

**Middleware/correlation pattern** (`backend/app/main.py:49-99`):
```python
@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-Id") or str(uuid4())
    ...
    response.headers["X-Correlation-Id"] = correlation_id
```
Any trusted-proxy or forwarded-header work belongs in middleware/app bootstrap, next to the existing request-wide context setup.

**Environment-template analog:** use `backend/app/core/config.py` field names plus `compose.yaml:82-118` service env names as the source of truth for `.env.example`.

---

### `backend/app/identity/redaction.py`, `backend/app/schemas/admin.py`, `backend/app/db/repositories/admin.py`, `backend/app/services/admin_evidence.py`, `backend/app/api/routes/admin.py` (admin evidence + redaction)

**Recursive sanitization analog** (`backend/app/core/logging.py:78-111`):
```python
def sanitize_log_value(value: Any, *, key: str | None = None) -> Any:
    if _is_sensitive_key(key):
        return _REDACTED
    if isinstance(value, dict):
        return { ... }
    if isinstance(value, (list, tuple, set)):
        return [ ... ]
```
Build admin-evidence redaction as a shared backend sanitizer before schema serialization.

**Structured JSON formatting analog** (`backend/app/core/logging.py:123-154`):
```python
payload.update(sanitize_log_value(extra_fields))
return json.dumps(sanitize_log_value(payload), ...)
```
Redact both summary rows and drawer/detail payloads before returning them.

**Current admin schema shape** (`backend/app/schemas/admin.py:72-123`):
```python
class SecurityEventItem(BaseModel):
    ...
    metadata: dict[str, Any]
```
Phase 5 should narrow/sanitize this field rather than pass raw nested metadata through unchanged.

**Paged repository pattern** (`backend/app/db/repositories/admin.py:68-117`, `119-186`):
```python
.offset(offset)
.limit(limit + 1)
...
has_more = len(events) > limit
```
Keep bounded paging for users/events/tools/gateway evidence.

**Admin service page-building pattern** (`backend/app/services/admin_evidence.py:117-166`, `451-460`):
```python
limit, offset = self._normalize_page(...)
rows, has_more = await self.repository.list_security_events(...)
return SecurityEventsPage(items=[...], page=self._page(...))
```
Use the same `limit+offset+has_more+next_offset` shape for new gateway evidence endpoints and drawer details.

**Admin authz + denial recording pattern** (`backend/app/services/admin_evidence.py:395-449`):
```python
decision = evaluate_admin_access(...)
if decision is PolicyResult.allow:
    return
await self.security_events.add_security_event(
    event_type="admin_access_denied",
    ...
)
```
Every new admin read surface should reuse `_require_admin_scope`; do not fork custom scope checks.

**Route error-mapping pattern** (`backend/app/api/routes/admin.py:32-50`, `74-129`, `132-203`):
```python
def _admin_access_error(exc: AdminAccessDenied) -> ApiError: ...
...
try:
    return await service.list_security_events(...)
except AdminAccessDenied as exc:
    raise _admin_access_error(exc) from exc
```
Add gateway-evidence routes using the same thin-handler + service-delegation pattern.

---

### `kong/kong.yml` and `compose.yaml` (gateway + deployment config)

**Declarative Kong pattern** (`kong/kong.yml:1-43`):
```yaml
_format_version: "3.0"
_transform: true
services:
  - name: backend
    url: http://backend:8000
plugins:
  - name: cors
    config:
      origins:
        - http://localhost:8000
```
Keep all ingress policy in the declarative file; add route/plugin blocks there instead of inventing runtime admin mutations.

**Compose exposure pattern** (`compose.yaml:173-197`):
```yaml
kong:
  image: kong:3.9.1
  environment:
    KONG_DATABASE: off
    KONG_DECLARATIVE_CONFIG: /etc/kong/kong.yml
    KONG_ADMIN_LISTEN: 127.0.0.1:8001
  ports:
    - "8000:8000"
```
Preserve the pattern that only the public proxy port is exposed; do not publish Kong Admin, Postgres, worker, or sandbox control-plane ports.

**Backend env wiring pattern** (`compose.yaml:82-118`):
```yaml
environment:
  SIMPAGENT_ALLOWED_ORIGINS: http://localhost:3000,http://localhost:8000
  SIMPAGENT_COOKIE_SECURE: false
  SIMPAGENT_LLM_API_KEY_FILE: ${LLM_API_KEY_FILE:-/run/secrets/llm_api_key}
```
Add OAuth/trusted-proxy/public-URL env keys in the same explicit `SIMPAGENT_*` style.

**Operational bootstrap pattern** (`compose.yaml:18-68`, `45-68`):
- Reuse the existing `migrate`, `init-dev-secrets`, and `seed-demo` job style for any Phase 5 bootstrap additions.

---

### `frontend/lib/auth-session.ts`, `frontend/lib/readiness.ts`, `frontend/components/account-access/AuthCard.tsx`, `frontend/components/account-access/AccountAccessShell.tsx` (OAuth-aware account access)

**Refresh-on-401 client pattern** (`frontend/lib/auth-session.ts:304-430`):
```ts
async authorizedJson<T>(input: string, init: RequestInit = {}): Promise<T> {
  return this.requestWithRefresh<T>(input, init);
}
```
Keep protected admin/account calls on `authorizedJson`; OAuth start/callback UI should not invent localStorage tokens or a second auth client.

**Readiness-load pattern** (`frontend/lib/auth-session.ts:163-194`):
```ts
const readiness = await requestJson<ReadinessResponse>("/ready", ...)
this.model = { ...this.model, readiness, ... }
```
Backend capability state for Google/GitHub buttons should flow through the same readiness/capability bootstrap path.

**UI-state mapping pattern** (`frontend/lib/readiness.ts:40-89`):
```ts
export function toAggregateUiState(readiness: ReadinessResponse | null): AggregateUiState { ... }
export function formsEnabled(readiness: ReadinessResponse | null): boolean { ... }
```
Extend these helpers for provider-availability labels instead of hard-coding button visibility in the JSX.

**Current provider-button structure** (`frontend/components/account-access/AuthCard.tsx:82-116`, `257-295`):
```tsx
function OAuthIcon({ provider }: { provider: "google" | "github" }) { ... }
...
<button type="button" disabled ...>
  <span ...><OAuthIcon provider="google" /></span>
  Continue with Google
</button>
```
Keep the button placement and icon pattern, but replace the placeholder-disabled behavior with capability-aware actions.

**Bootstrap/form orchestration pattern** (`frontend/components/account-access/AccountAccessShell.tsx:171-214`, `294-356`, `566-613`):
```tsx
const next = await controller.loadReadiness();
setViewModel(next);
...
try {
  const nextState = await controller.login(...)
  setViewModel(nextState)
} catch (error) { ... }
```
OAuth button clicks should hook into the same shell state/error announcement model.

---

### `frontend/lib/admin-api.ts`, `frontend/components/chat/ChatWorkspace.tsx`, `frontend/components/chat/ChatSidebar.tsx`, `frontend/components/settings/SettingsPage.tsx` (real admin surfaces)

**Admin API wrapper pattern** (`frontend/lib/admin-api.ts:8-31`):
```ts
return controller.authorizedJson<OrchestrationSettingsResponse>("/api/admin/orchestration", {
  method: "GET",
  cache: "no-store",
});
```
Add users/security-events/tool-executions/metrics/gateway-evidence endpoints in this exact wrapper style.

**Admin navigation pattern** (`frontend/components/chat/ChatSidebar.tsx:110-117`, `404-431`):
```tsx
const ADMIN_ITEMS = [ ... ]
...
{ADMIN_ITEMS.map((item) => (
  <button key={item.id} onClick={() => onSelectView?.(item.id)} ...>
```
Keep admin screens discoverable from the existing sidebar rather than inventing a second admin shell.

**Admin status panel pattern** (`frontend/components/chat/ChatSidebar.tsx:435-469`):
```tsx
{adminCanWrite && adminSettings ? (
  <div ...>
    <StatusBadge ...>
```
Use this summary-card style for compact admin status indicators; reserve drawers/tables for evidence pages.

**Workspace view-switch pattern** (`frontend/components/chat/ChatWorkspace.tsx:745-785`):
```tsx
switch (workspaceView) {
  case "overview":
    return <OverviewView ... />;
  ...
}
```
Real Phase 5 admin pages should plug into the existing `workspaceView` switch instead of bypassing it.

**Admin settings load/write pattern** (`frontend/components/chat/ChatWorkspace.tsx:428-463`, `689-709`):
```tsx
const response = await getOrchestrationSettings(controller)
...
const response = await setTrustedSupervisorEnabled(controller, enabled)
```
Mirror this for metrics/users/evidence paging and gateway evidence fetches.

**Settings page card pattern** (`frontend/components/settings/SettingsPage.tsx:33-61`, `168-236`):
```tsx
switch (activeSection) { ... }
...
<Card className="admin-card">
```
Keep the existing card/section navigation language when surfacing OAuth/provider readiness or operator guidance in settings.

---

### Backend test files (OAuth, gateway, admin evidence, redaction, smoke)

**Integration auth test pattern** (`backend/tests/integration/auth/test_login.py:7-14`):
```python
response = await client.post(
    "/api/auth/login",
    headers={"Origin": "http://localhost:3000"},
    json={...},
)
assert response.status_code == 401
```
Use the same async client + explicit origin/header assertions for OAuth start/callback tests.

**Admin evidence integration pattern** (`backend/tests/integration/admin/test_admin_evidence.py:9-37`, `39-88`):
```python
token = issue_token(...)
response = await client.get("/api/admin/users", headers={...})
assert response.status_code == 403
...
denial = (... select(SecurityEvent) ...).scalar_one()
assert denial.event_type == "admin_access_denied"
```
Gateway/admin evidence tests should assert both HTTP behavior and persisted evidence side effects.

**Admin write integration pattern** (`backend/tests/integration/admin/test_admin_write.py:47-99`, `189-312`):
- Follow the same matrix style for read/write scope splits and orchestration toggles.

**Unit service fake-repository pattern** (`backend/tests/unit/test_admin_evidence_service.py:26-191`, `194-504`):
```python
@dataclass
class FakeAdminRepository: ...
@dataclass
class FakeSecurityEventSink: ...
```
Use fake repositories/sinks for redaction and paging unit tests instead of booting the DB for every service branch.

**Config validation pattern** (`backend/tests/unit/test_config.py:12-37`, `44-95`, `153-166`):
- Add OAuth/trusted-proxy/public-URL negative tests alongside the existing production-validation style.

**Logging/redaction canary pattern** (`backend/tests/unit/test_logging.py:9-35`):
```python
record.authorization = "Bearer top-secret-token"
...
assert payload["authorization"] == "[REDACTED]"
```
Add Phase 5 redaction tests here first for the shared sanitizer.

**Security canary pattern** (`backend/tests/security/test_secret_leakage.py:8-27`):
```python
assert secret_canary not in repr_text
assert secret_canary not in response.text
```
Apply the same canary style to admin evidence snippets and OAuth failure payloads.

**Search redaction analog** (`backend/tests/security/test_search_secret_leakage.py:8-38`):
```python
assert secret_canary not in dumped
assert evidence.web_search_queries == ["truy van an toan"]
```
Use this as the closest existing snippet-sanitization assertion style for admin evidence drawers.

**Smoke topology/admin flow pattern** (`backend/tests/smoke/test_topology.py:15-54`, `backend/tests/smoke/test_admin_flow.py:23-152`):
- Keep full-stack smoke tests on `httpx.AsyncClient`, use helper login/register flows, and verify real endpoint behavior instead of mocked browser-only checks.

**Gateway/logging smoke pattern** (`backend/tests/smoke/test_logging_flow.py:75-94`):
```python
backend_access_lines = await poll_loki_lines(...)
kong_search_lines = await poll_loki_lines(...)
assert kong_search_lines
```
Use this as the analog for correlation, rate-limit, and Kong evidence verification smoke coverage.

---

### Frontend test files (`frontend/tests/account-access-oauth.test.tsx`, `frontend/tests/admin-evidence.test.tsx`)

**Auth controller test pattern** (`frontend/tests/auth-session.test.ts:23-91`, `93-178`):
```ts
const controller = new AuthSessionController("login", { fetchImpl, getCsrfToken: ... })
await controller.login(...)
const snapshot = controller.snapshot
assert.equal(snapshot.sessionState, "session_expired")
```
Provider-capability and OAuth button tests should follow this controller-driven pattern rather than DOM-only snapshots.

**Workspace/admin UI test pattern** (`frontend/tests/chat-workspace.test.ts:149-200`, `303-340`, `422-529`):
```ts
const html = renderToStaticMarkup(React.createElement(ChatSidebar, navigationProps()))
assert.match(html, /ADMIN/)
```
Use the same static-markup and helper-props style for admin evidence tables/drawers before moving to richer browser tests.

**Readiness helper test pattern** (`frontend/tests/readiness.test.ts:14-98`):
- Add provider-capability label and enable/disable-state tests next to the existing readiness mapping assertions.

---

### `README.md` and `.env.example` (operator docs / environment template)

**README run/test section analog** (`README.md:31-63`, `80-132`):
- Keep Phase 5 operator guidance in the same concrete format: prerequisites, env notes, startup command, public entrypoints, demo accounts, test commands.

**Current deployment-topology narrative analog** (`README.md:65-79`, `116-154`):
- Add OAuth redirect guidance, Kong/Cloudflare trust-boundary notes, and 100-users/month limitations in the same repo-specific tone.

**Environment template analogs:**
- `backend/app/core/config.py:89-311` for variable names and validation semantics.
- `compose.yaml:82-118` for example development values and `_FILE` secret patterns.

## Shared Patterns

### Authentication/session issuance
**Sources:**
- `backend/app/api/routes/auth.py:31-54, 100-107, 133-140`
- `backend/app/services/authentication.py:47-98`
- `backend/app/services/sessions.py:63-132`

**Apply to:** `backend/app/api/routes/auth_oauth.py`, `backend/app/identity/oauth_service.py`

Use the existing access-JWT + refresh-family + CSRF-cookie model unchanged. OAuth should only replace identity proofing, not session format.

### Provider identity contract
**Sources:**
- `backend/app/identity/contracts.py:7-17`
- `backend/app/identity/local_provider.py:29-66`
- `backend/app/models/account.py:49-58`

**Apply to:** `backend/app/identity/providers/google.py`, `backend/app/identity/providers/github.py`, `backend/app/identity/oauth_service.py`, `backend/app/db/repositories/accounts.py`

Always key external identities by `issuer` + `subject`; treat provider email as mutable linking data only.

### Admin authorization + denial evidence
**Sources:**
- `backend/app/authorization/policy.py:43-52`
- `backend/app/services/admin_evidence.py:395-449`
- `backend/app/api/routes/admin.py:32-50`

**Apply to:** all new admin evidence endpoints and service methods.

### Recursive redaction
**Sources:**
- `backend/app/core/logging.py:78-111, 123-154`
- `backend/tests/unit/test_logging.py:9-35`
- `backend/tests/security/test_secret_leakage.py:8-27`

**Apply to:** `backend/app/identity/redaction.py`, `backend/app/services/admin_evidence.py`, `backend/app/schemas/admin.py`, admin/security tests.

### Correlation propagation
**Sources:**
- `backend/app/main.py:58-98`
- `backend/app/db/repositories/sessions.py:56-79`
- `backend/tests/smoke/test_logging_flow.py:75-94`

**Apply to:** OAuth callback errors, gateway evidence, admin evidence rows, provider-call evidence, smoke tests.

### Frontend protected-request flow
**Sources:**
- `frontend/lib/auth-session.ts:304-430`
- `frontend/lib/admin-api.ts:8-31`
- `frontend/lib/chat-api.ts:13-103`

**Apply to:** all new frontend admin/OAuth capability fetches.

### Bounded paging
**Sources:**
- `backend/app/db/repositories/admin.py:68-145`
- `backend/app/services/admin_evidence.py:117-166, 451-460`

**Apply to:** users, security events, tool executions, gateway evidence.

## No Analog Found

No files are completely without analogs, but these need partial-copy treatment instead of direct cloning:

| File | Closest Reuse | Why partial |
|---|---|---|
| `backend/app/api/routes/auth_oauth.py` | `backend/app/api/routes/auth.py` | Existing route pattern is correct, but there is no current redirect/callback flow. |
| `backend/app/identity/providers/github.py` | `backend/app/identity/local_provider.py` | Provider contract exists, but there is no in-repo example of follow-up email retrieval. |
| `backend/tests/integration/gateway/test_*` | `backend/tests/smoke/test_topology.py`, `backend/tests/smoke/test_logging_flow.py` | Repo has Kong smoke verification, but not a dedicated gateway integration suite yet. |
| `frontend/tests/admin-evidence.test.tsx` | `frontend/tests/chat-workspace.test.ts` | Existing UI tests cover sidebar/workspace shells, not paged admin evidence drawers. |
| `.env.example` | `backend/app/core/config.py`, `compose.yaml` | Pattern source is available, but current file was not pattern-read in this pass due workspace permission limits. |

## Metadata

**Analog search scope:** `backend/app`, `backend/alembic/versions`, `backend/tests`, `frontend/components`, `frontend/lib`, `frontend/tests`, `kong`, repo root config/docs.

**Files scanned:** 62 unique repo files read, plus glob/grep scan across backend, frontend, tests, and gateway config.

**Pattern extraction date:** 2026-06-15
