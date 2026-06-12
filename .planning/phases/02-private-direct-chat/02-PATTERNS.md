# Phase 02: Private Direct Chat - Pattern Map

**Mapped:** 2026-06-11
**Files analyzed:** 21
**Analogs found:** 21 / 21

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `backend/app/api/routes/chat.py` | route/controller | request-response | `backend/app/api/routes/auth.py` | role-match |
| `backend/app/api/__init__.py` | config | request-response | `backend/app/api/__init__.py` | exact |
| `backend/app/main.py` | config | request-response | `backend/app/main.py` | exact |
| `backend/app/schemas/chat.py` | model/schema | transform | `backend/app/schemas/auth.py` | role-match |
| `backend/app/services/chat.py` | service | CRUD + request-response | `backend/app/services/authentication.py` | role-match |
| `backend/app/db/repositories/conversations.py` | repository/service | CRUD | `backend/app/db/repositories/accounts.py` | role-match |
| `backend/app/models/domain.py` | model | CRUD | `backend/app/models/domain.py` | exact |
| `backend/alembic/versions/0003_chat_turn_state.py` | migration | CRUD | `backend/alembic/versions/0002_platform_foundations.py` | exact |
| `backend/app/ai/chat_adapter.py` | service | request-response | `backend/app/core/provider_status.py` + `backend/app/core/config.py` | role-match |
| `backend/app/core/config.py` | config | transform | `backend/app/core/config.py` | exact |
| `frontend/lib/chat-api.ts` | utility | request-response | `frontend/lib/auth-session.ts` + `frontend/lib/api.ts` | role-match |
| `frontend/lib/chat-types.ts` | model/schema | transform | `frontend/lib/auth-session.ts` | role-match |
| `frontend/components/chat/ChatWorkspace.tsx` | component/provider | event-driven + request-response | `frontend/components/account-access/AccountAccessShell.tsx` | role-match |
| `frontend/components/chat/ConversationSidebar.tsx` | component | event-driven | `frontend/components/account-access/PlatformStatus.tsx` | role-match |
| `frontend/components/chat/MessageList.tsx` | component | transform | `frontend/components/account-access/AuthCard.tsx` | role-match |
| `frontend/components/chat/MessageRenderer.tsx` | component | transform | `frontend/components/account-access/InlineAlert.tsx` | partial |
| `frontend/components/chat/Composer.tsx` | component | event-driven + request-response | `frontend/components/account-access/FormField.tsx` + `PasswordField.tsx` | role-match |
| `frontend/app/page.tsx` | component/config | request-response | `frontend/app/page.tsx` | exact |
| `frontend/package.json` | config | batch | `frontend/package.json` | exact |
| `backend/tests/integration/chat/**`, `backend/tests/security/test_chat_*.py`, `backend/tests/unit/ai/test_chat_adapter.py` | test | request-response + CRUD | `backend/tests/integration/auth/test_login.py`, `test_me.py`, security tests | role-match |
| `frontend/tests/chat-*.test.ts` | test | event-driven + request-response | `frontend/tests/auth-session.test.ts` | role-match |

## Pattern Assignments

### `backend/app/api/routes/chat.py` (route/controller, request-response)

**Analog:** `backend/app/api/routes/auth.py`

**Imports and router pattern** (lines 6-20):
```python
from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.authorization.principal import AuthenticatedPrincipal, resolve_principal
from app.core.errors import ApiError
from app.db.session import get_session

router = APIRouter(prefix="/api/auth", tags=["auth"])
```

Use the same FastAPI dependency style for chat routes, but with `prefix="/api/conversations"` and `tags=["chat"]`.

**Authenticated route pattern** (lines 166-168):
```python
@router.get("/me", response_model=CurrentUserResponse)
async def me(principal: Annotated[AuthenticatedPrincipal, Depends(resolve_principal)]) -> CurrentUserResponse:
    return principal.to_current_user()
```

**Service and error mapping pattern** (lines 83-99):
```python
settings = get_settings(request)
service = AuthenticationService(session, settings)
try:
    outcome = await service.login(
        email=str(payload.email),
        password=payload.password,
        origin=request.headers.get("origin"),
        now=get_now(request),
    )
except CsrfValidationError as exc:
    raise ApiError(status_code=403, code="origin_rejected", message="The request origin is not allowed.") from exc
except AuthenticationFailed as exc:
    raise ApiError(
        status_code=401,
        code="invalid_credentials",
        message="Unable to sign in with the provided credentials. Check your email and password and try again.",
    ) from exc
```

For chat, map service exceptions to `ApiError` codes such as `conversation_not_found`, `missing_scope`, `turn_in_progress`, `provider_failed`, and include correlation IDs through the central handler.

### `backend/app/services/chat.py` (service, CRUD + request-response)

**Analog:** `backend/app/services/authentication.py`

**Constructor/dependency pattern** (lines 39-46):
```python
class AuthenticationService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.accounts = AccountsRepository(session)
        self.sessions = SessionsRepository(session)
        self.provider = LocalIdentityProvider(session)
```

Chat service should own `ConversationsRepository`, settings, and the provider adapter. Keep provider calls behind a local adapter rather than inside route functions.

**Transactional service pattern** (lines 47-82):
```python
async def login(self, *, email: str, password: str, origin: str | None, now: datetime) -> LoginOutcome:
    require_allowed_origin(origin, self.settings)
    async with self.session.begin():
        decision = await self.provider.check_credentials(LocalAuthRequest(email=email, password=password))
        if decision.verified_identity is None or decision.user_id is None:
            raise AuthenticationFailed("Invalid credentials")
```

Copy the `async with self.session.begin()` shape for owner-checked create/list/delete and the pre-provider portion of send/retry. Do not keep the transaction open during the LLM request.

### `backend/app/db/repositories/conversations.py` (repository/service, CRUD)

**Analog:** `backend/app/db/repositories/accounts.py`

**Repository structure and typed result bundle** (lines 16-36):
```python
@dataclass(slots=True)
class UserBundle:
    user: User
    scopes: list[UserScope]
    identities: list[Identity]
    local_credential: LocalCredential | None

class AccountsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
```

Create `ConversationBundle`/`TurnBundle` dataclasses where useful, and keep `AsyncSession` injected.

**Query pattern** (lines 55-69):
```python
stmt = (
    select(User)
    .options(
        selectinload(User.scopes),
        selectinload(User.identities),
        selectinload(User.local_credential),
    )
    .where(User.id == user_id)
)
result = await self.session.execute(stmt)
user = result.scalar_one_or_none()
if user is None:
    return None
```

For BOLA safety, replace this with owner-constrained chat predicates in the same SQL operation: `Conversation.id == conversation_id`, `Conversation.user_id == user_id`, and `Conversation.deleted_at.is_(None)`.

**Insert/flush pattern** (lines 71-84):
```python
user = User(id=uuid4(), email=normalized, email_key=email_key, role=role, is_active=True, is_demo=is_demo)
scope_rows = [UserScope(user_id=user.id, scope=scope) for scope in scopes]
self.session.add(user)
self.session.add_all(scope_rows)
try:
    await self.session.flush()
except IntegrityError as exc:
    raise DuplicateEmailError("Duplicate email") from exc
```

Use this pattern for conversation/message creation and map uniqueness conflicts on `(conversation_id, client_message_id)` to an idempotent replay path.

### `backend/app/models/domain.py` (model, CRUD)

**Analog:** `backend/app/models/domain.py`

**Existing conversation model** (lines 17-25):
```python
class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

Keep this owner and soft-delete shape. Phase 2 should extend, not replace, this table.

**Existing message model** (lines 28-47):
```python
class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("conversation_id", "sequence_no", name="uq_messages_conversation_id_sequence_no"),
        CheckConstraint(MESSAGE_ROLE_CHECK, name="ck_messages_message_role_known"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        postgresql.JSONB(astext_type=Text()),
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
```

Add `client_message_id` and `status` with a check constraint, while preserving `sequence_no` uniqueness and JSONB metadata.

### `backend/alembic/versions/0003_chat_turn_state.py` (migration, CRUD)

**Analog:** `backend/alembic/versions/0002_platform_foundations.py`

**Alembic header and constants pattern** (lines 1-15):
```python
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_platform_foundations"
down_revision = "0001_account_access"
branch_labels = None
depends_on = None
```

**Table/constraint/index pattern** (lines 32-46):
```python
op.create_table(
    "messages",
    sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("sequence_no", sa.Integer(), nullable=False),
    sa.Column("role", sa.String(length=32), nullable=False),
    sa.Column("content", sa.Text(), nullable=False),
    sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    sa.CheckConstraint(MESSAGE_ROLE_CHECK, name=op.f("ck_messages_message_role_known")),
    sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], name=op.f("fk_messages_conversation_id_conversations"), ondelete="CASCADE"),
    sa.PrimaryKeyConstraint("id", name=op.f("pk_messages")),
    sa.UniqueConstraint("conversation_id", "sequence_no", name="uq_messages_conversation_id_sequence_no"),
)
op.create_index(op.f("ix_messages_conversation_id"), "messages", ["conversation_id"], unique=False)
```

For Phase 2 use `op.add_column`, `op.create_check_constraint`, `op.create_unique_constraint`, and matching downgrade calls.

### `backend/app/ai/chat_adapter.py` and `backend/app/core/config.py` (service/config, request-response)

**Analog:** `backend/app/core/config.py`

**Secret configuration pattern** (lines 70-78):
```python
llm_api_base: str | None = None
llm_api_key: SecretStr | None = None
llm_api_key_file: str | None = None
llm_model: str | None = None
google_api_key: SecretStr | None = None
google_api_key_file: str | None = None
search_model: str | None = None
provider_check_timeout_seconds: int = 2
```

**Secret file accessor pattern** (lines 155-159):
```python
@property
def llm_api_key_value(self) -> str | None:
    if self.llm_api_key:
        return self.llm_api_key.get_secret_value()
    return _read_secret_file(self.llm_api_key_file)
```

Do not log `llm_api_key_value`; adapter errors should be app-owned codes with safe metadata.

### `frontend/lib/chat-api.ts` and `frontend/lib/chat-types.ts` (utility/model, request-response)

**Analog:** `frontend/lib/auth-session.ts` and `frontend/lib/api.ts`

**Typed API error pattern** (`frontend/lib/api.ts`, lines 1-25):
```typescript
export type ApiErrorBody = {
  error?: {
    code?: string;
    message?: string;
    correlation_id?: string;
  };
};

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly correlationId?: string;
```

**Authorized JSON reuse pattern** (`frontend/lib/auth-session.ts`, lines 304-306):
```typescript
async authorizedJson<T>(input: string, init: RequestInit = {}): Promise<T> {
  return this.requestWithRefresh<T>(input, init);
}
```

Chat API helpers should accept an `AuthSessionController` and call `authorizedJson`, preserving memory-only access tokens and refresh-on-401.

**Bearer retry implementation to preserve** (`frontend/lib/auth-session.ts`, lines 346-385):
```typescript
private async requestWithRefresh<T>(input: string, init: RequestInit): Promise<T> {
  const firstAttemptToken = this.model.accessToken;
  try {
    return await requestJson<T>(
      input,
      {
        ...init,
        cache: "no-store",
        credentials: "include",
        headers: {
          ...defaultHeaders(firstAttemptToken),
          ...(init.headers ?? {}),
        },
      },
      this.fetchImpl,
    );
```

### `frontend/components/chat/ChatWorkspace.tsx` (component/provider, event-driven + request-response)

**Analog:** `frontend/components/account-access/AccountAccessShell.tsx`

**Client shell and imports pattern** (lines 1-19):
```tsx
"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  AuthSessionController,
  type SessionState,
  type ShellViewModel,
} from "@/lib/auth-session";
```

**Controller ownership pattern** (lines 131-153):
```tsx
export function AccountAccessShell({ initialMode, demoConfig }: AccountAccessShellProps) {
  const controller = useMemo(
    () => new AuthSessionController(initialMode, { getCsrfToken: readCsrfToken }),
    [initialMode],
  );

  const [viewModel, setViewModel] = useState<ShellViewModel>(controller.snapshot);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
```

Use this for top-level state. Phase 2 authenticated view should become chat-first while preserving login/register/session restoration.

**Async submit/error/correlation pattern** (lines 294-325):
```tsx
async function handleLoginSubmit(event: FormEvent<HTMLFormElement>) {
  event.preventDefault();
  clearFormState();
  setAnnouncement(null);
  if (!validateLogin()) {
    return;
  }

  setIsSubmitting(true);
  try {
    const nextState = await controller.login({
      email: formFields.email,
      password: formFields.password,
    });
    setViewModel(nextState);
  } catch (error) {
    if (error instanceof Error) {
      setErrorMessage(error.message);
    }
  } finally {
    setIsSubmitting(false);
  }
}
```

Copy the `try/catch/finally` shape for send, retry, delete, and pagination actions. Surface `correlationId` on failed assistant rows.

### `frontend/components/chat/*` presentational components (component, event-driven/transform)

**Analog:** `frontend/components/account-access/ActionButton.tsx`

**Reusable button component pattern** (lines 1-35):
```tsx
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { forwardRef } from "react";

type ActionButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "quiet";
  icon?: ReactNode;
  fullWidth?: boolean;
};

export const ActionButton = forwardRef<HTMLButtonElement, ActionButtonProps>(function ActionButton(
```

Use typed props, native button attributes, and `forwardRef` for composer submit and copy buttons.

**Accessible inline status pattern** (`frontend/components/account-access/InlineAlert.tsx`, lines 11-18):
```tsx
export function InlineAlert({ tone, title, message, detail, urgent = false }: InlineAlertProps) {
  return (
    <div className={`inline-alert inline-alert-${tone}`} role={urgent ? "alert" : "status"} aria-live={urgent ? "assertive" : "polite"}>
      {title ? <p className="inline-alert-title">{title}</p> : null}
      <div className="inline-alert-body">{message}</div>
      {detail ? <p className="inline-alert-detail">{detail}</p> : null}
    </div>
  );
}
```

Use the same `role`/`aria-live` model for pending, failed, retryable, and delete-undo feedback.

### Backend tests (test, request-response + CRUD)

**Analog:** `backend/tests/conftest.py`, `backend/tests/integration/auth/test_login.py`, `backend/tests/integration/auth/test_me.py`

**ASGI client fixture pattern** (`backend/tests/conftest.py`, lines 57-65):
```python
@pytest.fixture
def app(settings: Settings, session_factory):
    return create_app(settings=settings, session_factory=session_factory)

@pytest.fixture
async def client(app) -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as http_client:
        yield http_client
```

**HTTP assertion pattern** (`backend/tests/integration/auth/test_login.py`, lines 6-14):
```python
@pytest.mark.asyncio
async def test_login_unknown_user_fails_generically(client) -> None:
    response = await client.post(
        "/api/auth/login",
        headers={"Origin": "http://localhost:3000"},
        json={"email": "missing@example.com", "password": "matkhau-bao-mat-123"},
    )
    assert response.status_code == 401
```

**Auth-required negative pattern** (`backend/tests/integration/auth/test_me.py`, lines 6-9):
```python
@pytest.mark.asyncio
async def test_me_requires_principal(client) -> None:
    response = await client.get("/api/auth/me")
    assert response.status_code == 401
```

Apply this to chat negative tests: missing token, missing `chat:read`, missing `chat:write`, cross-user get/delete/send/retry, stale token, duplicate submit, in-flight conflict, and provider failure.

### Frontend tests (test, event-driven + request-response)

**Analog:** `frontend/tests/auth-session.test.ts`

**Node test + fake fetch pattern** (lines 1-21):
```typescript
import test from "node:test";
import assert from "node:assert/strict";

function jsonResponse({ status, body, headers = {} }: FetchResponse): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json",
      ...headers,
    },
  });
}
```

**Concurrent request assertion pattern** (lines 23-91):
```typescript
void test("simultaneous protected requests share one refresh attempt", async () => {
  let refreshCalls = 0;
  const fetchImpl: typeof fetch = async (input, init) => {
    const url = String(input);
    if (url === "/api/auth/refresh") {
      refreshCalls += 1;
      return jsonResponse({
        status: 200,
        body: { access_token: "token-2", token_type: "bearer", expires_in: 600 },
      });
    }
```

Use the same fake-fetch structure for chat API tests covering `client_message_id`, pending conflict, retry after failure, correlation ID display data, and unsafe Markdown rendering helpers.

## Shared Patterns

### Authentication and Principal Resolution

**Source:** `backend/app/authorization/principal.py`
**Apply to:** all chat route handlers

```python
if credentials is None or credentials.scheme.lower() != "bearer":
    raise ApiError(status_code=401, code="missing_principal", message="Authenticated principal is required.")
...
if claims.role != current_role or claims.scopes != current_scopes:
    raise ApiError(status_code=401, code="stale_token", message="The access token is no longer valid for the current account state.")
return AuthenticatedPrincipal(
    user_id=bundle.user.id,
    email=bundle.user.email,
    role=current_role,
    scopes=current_scopes,
    is_active=bundle.user.is_active,
    claims=claims,
)
```

### Scope Evaluation

**Source:** `backend/app/authorization/policy.py`
**Apply to:** chat read/write dependencies or service guards

```python
class Scope(str, Enum):
    chat_read = "chat:read"
    chat_write = "chat:write"

def evaluate_required_scopes(*, principal_scopes: set[str], required: set[str]) -> PolicyResult:
    if not required.issubset(principal_scopes):
        return PolicyResult.deny_scope
    return PolicyResult.allow
```

### Error Envelope and Correlation IDs

**Source:** `backend/app/core/errors.py`, `backend/app/main.py`
**Apply to:** all backend chat routes/services

```python
content: dict[str, Any] = {
    "error": {
        "code": code,
        "message": message,
    }
}
if correlation_id:
    content["error"]["correlation_id"] = correlation_id
```

```python
@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-Id") or str(uuid4())
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["X-Correlation-Id"] = correlation_id
    return response
```

### Router Registration

**Source:** `backend/app/api/__init__.py`, `backend/app/main.py`
**Apply to:** new `chat` route module

```python
from .routes import auth, health

__all__ = ["auth", "health"]
```

```python
from app.api.routes import auth, health
...
app.include_router(auth.router)
app.include_router(health.router)
```

Add `chat` in both locations and include `chat.router`.

### Frontend Session and Token Boundary

**Source:** `frontend/lib/auth-session.ts`
**Apply to:** all chat API calls

```typescript
headers: {
  ...defaultHeaders(firstAttemptToken),
  ...(init.headers ?? {}),
},
```

Do not store access tokens in `localStorage`; keep chat calls behind `AuthSessionController.authorizedJson`.

### Safe Markdown Rendering Constraints

**Source:** `02-RESEARCH.md` plus existing absence of Markdown renderer
**Apply to:** `MessageRenderer.tsx`, `frontend/package.json`, `frontend/tests/chat-markdown.test.ts`

No direct code analog exists for Markdown. Planner should use the research pattern: `react-markdown` + `remark-gfm`, no `rehype-raw`, explicit URL allowlist (`http`, `https`, `mailto`), external links with `target="_blank"` and `rel="noopener noreferrer"`, and no `dangerouslySetInnerHTML`.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `frontend/components/chat/MessageRenderer.tsx` Markdown pipeline | component | transform | Existing frontend has alerts/forms but no Markdown, sanitizer, syntax highlighter, or copy-code renderer. Use RESEARCH.md Pattern 6. |
| `backend/app/ai/chat_adapter.py` OpenAI SDK call body | service | request-response | Existing provider status/config patterns exist, but no current OpenAI-compatible completion adapter. Use RESEARCH.md Pattern 4 plus `Settings` secret handling. |

## Metadata

**Analog search scope:** `backend/app/**`, `backend/tests/**`, `frontend/lib/**`, `frontend/components/**`, `frontend/tests/**`, `frontend/app/**`, `backend/alembic/versions/**`
**Files scanned:** 70+
**Pattern extraction date:** 2026-06-11
