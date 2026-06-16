from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.authorization.policy import PolicyResult
from app.authorization.principal import AuthenticatedPrincipal
from app.db.repositories.admin import (
    AdminMetricsRecord,
    AdminUserRecord,
    SecurityEventRecord,
    ToolExecutionRecord,
)
from app.schemas.auth import ADMIN_SCOPES, STANDARD_USER_SCOPES
from app.security.access_tokens import AccessTokenClaims
from app.services.admin_evidence import (
    AdminAccessDenied,
    AdminEvidenceService,
    AdminWriteRejected,
)
from app.services.gateway_evidence import GatewayEvidenceService


@dataclass
class FakeAdminRepository:
    users: list[AdminUserRecord] = field(default_factory=list)
    security_events: list[SecurityEventRecord] = field(default_factory=list)
    tool_executions: list[ToolExecutionRecord] = field(default_factory=list)
    metrics: AdminMetricsRecord = field(
        default_factory=lambda: AdminMetricsRecord(
            users_total=0,
            users_active=0,
            security_events_total=0,
            security_events_last_24h=0,
            tool_executions_total=0,
            tool_executions_last_24h=0,
            correlation_references_total=0,
            rate_limit_events_total=0,
        )
    )

    async def list_users(self, *, limit: int, offset: int):
        window = self.users[offset : offset + limit + 1]
        return window[:limit], len(window) > limit

    async def list_security_events(self, *, limit: int, offset: int):
        window = self.security_events[offset : offset + limit + 1]
        return window[:limit], len(window) > limit

    async def list_tool_executions(self, *, limit: int, offset: int):
        window = self.tool_executions[offset : offset + limit + 1]
        return window[:limit], len(window) > limit

    async def get_metrics(self, *, since: datetime):
        return self.metrics


@dataclass
class FakeSecurityEventSink:
    calls: list[dict] = field(default_factory=list)

    async def add_security_event(self, **kwargs):
        self.calls.append(kwargs)
        return kwargs


@dataclass
class FakeScopeRow:
    scope: str


@dataclass
class FakeUser:
    id: object
    email: str
    role: str
    is_active: bool
    is_demo: bool
    created_at: datetime
    updated_at: datetime


@dataclass
class FakeUserBundle:
    user: FakeUser
    scopes: list[FakeScopeRow]
    identities: list = field(default_factory=list)
    local_credential: object | None = None


@dataclass
class FakeAccountsRepository:
    bundles: dict = field(default_factory=dict)

    async def get_user_bundle_by_id(self, user_id):
        return self.bundles.get(user_id)

    async def replace_user_scopes(self, user_id, scopes: list[str]) -> None:
        bundle = self.bundles[user_id]
        await self.replace_bundle_scopes(bundle, scopes)

    async def replace_bundle_scopes(self, bundle, scopes: list[str]) -> None:
        bundle.scopes = [FakeScopeRow(scope=scope) for scope in scopes]


@dataclass
class FakeAsyncSession:
    flush_calls: int = 0
    commit_calls: int = 0
    rollback_calls: int = 0
    transaction_open: bool = False

    async def flush(self) -> None:
        self.flush_calls += 1
        self.transaction_open = True

    async def commit(self) -> None:
        self.commit_calls += 1
        self.transaction_open = False

    async def rollback(self) -> None:
        self.rollback_calls += 1
        self.transaction_open = False

    def in_transaction(self) -> bool:
        return self.transaction_open

    def expire_all(self) -> None:
        return None


@dataclass
class FakeAgentSettingsRepository:
    guardrail_enabled: bool | None = True
    trusted_supervisor_enabled: bool | None = False
    writes: list[dict] = field(default_factory=list)

    async def is_guardrail_enabled(self, *, default: bool) -> bool:
        return self.guardrail_enabled if self.guardrail_enabled is not None else default

    async def is_trusted_supervisor_enabled(self, *, default: bool) -> bool:
        return (
            self.trusted_supervisor_enabled
            if self.trusted_supervisor_enabled is not None
            else default
        )

    async def set_guardrail_enabled(self, *, enabled: bool, updated_by_user_id):
        self.guardrail_enabled = enabled
        self.writes.append(
            {
                "setting": "guardrail",
                "enabled": enabled,
                "updated_by_user_id": updated_by_user_id,
            }
        )
        return type("Setting", (), {"enabled": enabled})()

    async def set_trusted_supervisor_enabled(self, *, enabled: bool, updated_by_user_id):
        self.trusted_supervisor_enabled = enabled
        self.writes.append(
            {
                "setting": "trusted_supervisor",
                "enabled": enabled,
                "updated_by_user_id": updated_by_user_id,
            }
        )
        return type("Setting", (), {"enabled": enabled})()


def _principal(*, role: str, scopes: tuple[str, ...]) -> AuthenticatedPrincipal:
    user_id = uuid4()
    claims = AccessTokenClaims(
        sub=user_id,
        role=role,
        scopes=scopes,
        iss="simpagent.test",
        aud="simpagent-api",
        iat=1,
        nbf=1,
        exp=2,
        kid="test-kid",
        jti=uuid4(),
    )
    return AuthenticatedPrincipal(
        user_id=user_id,
        email="admin@example.test",
        role=role,
        scopes=scopes,
        is_active=True,
        claims=claims,
    )


@pytest.mark.asyncio
async def test_list_users_returns_bounded_page_for_authorized_admin() -> None:
    now = datetime.now(UTC)
    repository = FakeAdminRepository(
        users=[
            AdminUserRecord(
                id=uuid4(),
                email="one@example.test",
                role="user",
                scopes=["chat:read"],
                is_active=True,
                is_demo=False,
                created_at=now,
                updated_at=now,
            ),
            AdminUserRecord(
                id=uuid4(),
                email="two@example.test",
                role="admin",
                scopes=["admin:read"],
                is_active=True,
                is_demo=False,
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    service = AdminEvidenceService(
        None,
        correlation_id="corr-admin-users",
        now=now,
        repository=repository,
        security_events=FakeSecurityEventSink(),
    )

    result = await service.list_users(
        principal=_principal(role="admin", scopes=("admin:read",)),
        limit=1,
        offset=0,
    )

    assert len(result.items) == 1
    assert result.items[0].email == "one@example.test"
    assert result.page.has_more is True
    assert result.page.next_offset == 1


@pytest.mark.asyncio
async def test_admin_denial_records_redacted_security_event() -> None:
    sink = FakeSecurityEventSink()
    service = AdminEvidenceService(
        None,
        correlation_id="corr-admin-denied",
        now=datetime.now(UTC),
        repository=FakeAdminRepository(),
        security_events=sink,
    )

    with pytest.raises(AdminAccessDenied) as exc_info:
        await service.list_security_events(
            principal=_principal(role="user", scopes=("chat:read",)),
            limit=25,
            offset=0,
        )

    assert exc_info.value.decision is PolicyResult.deny_role
    assert sink.calls[0]["event_type"] == "admin_access_denied"
    assert sink.calls[0]["correlation_id"] == "corr-admin-denied"
    assert sink.calls[0]["metadata"] == {
        "resource": "security_events",
        "required_scope": "admin:read",
        "decision": PolicyResult.deny_role.value,
    }


@pytest.mark.asyncio
async def test_metrics_uses_repository_snapshot() -> None:
    service = AdminEvidenceService(
        None,
        correlation_id="corr-admin-metrics",
        now=datetime(2026, 6, 11, tzinfo=UTC),
        repository=FakeAdminRepository(
            metrics=AdminMetricsRecord(
                users_total=5,
                users_active=4,
                security_events_total=9,
                security_events_last_24h=3,
                tool_executions_total=7,
                tool_executions_last_24h=2,
                correlation_references_total=6,
                rate_limit_events_total=1,
            )
        ),
        security_events=FakeSecurityEventSink(),
    )

    result = await service.get_metrics(principal=_principal(role="admin", scopes=("admin:read",)))

    assert result.users_total == 5
    assert result.users_active == 4
    assert result.security_events_last_24h == 3
    assert result.tool_executions_last_24h == 2
    assert result.correlation_references_total == 6
    assert result.rate_limit_events_total == 1


@pytest.mark.asyncio
async def test_admin_write_requires_admin_write_scope() -> None:
    sink = FakeSecurityEventSink()
    service = AdminEvidenceService(
        None,
        correlation_id="corr-admin-write-scope",
        now=datetime.now(UTC),
        repository=FakeAdminRepository(),
        security_events=sink,
        accounts=FakeAccountsRepository(),
    )

    with pytest.raises(AdminAccessDenied) as exc_info:
        await service.update_user_access(
            principal=_principal(role="admin", scopes=("admin:read",)),
            target_user_id=uuid4(),
            is_active=False,
        )

    assert exc_info.value.decision is PolicyResult.deny_scope
    assert sink.calls[0]["metadata"] == {
        "resource": "user_access",
        "required_scope": "admin:write",
        "decision": PolicyResult.deny_scope.value,
    }


@pytest.mark.asyncio
async def test_admin_read_can_view_orchestration_settings() -> None:
    service = AdminEvidenceService(
        None,
        correlation_id="corr-admin-orch-read",
        now=datetime.now(UTC),
        repository=FakeAdminRepository(),
        security_events=FakeSecurityEventSink(),
        agent_settings=FakeAgentSettingsRepository(
            guardrail_enabled=False,
            trusted_supervisor_enabled=True,
        ),
    )

    result = await service.get_orchestration_settings(
        principal=_principal(role="admin", scopes=("admin:read",)),
        default_guardrail_enabled=True,
        default_trusted_supervisor_enabled=False,
    )

    assert result.guardrail_safety_enabled is False
    assert result.trusted_supervisor_enabled is True


@pytest.mark.asyncio
async def test_admin_write_can_toggle_guardrail_safety_agent() -> None:
    session = FakeAsyncSession()
    sink = FakeSecurityEventSink()
    agent_settings = FakeAgentSettingsRepository(
        guardrail_enabled=True,
        trusted_supervisor_enabled=False,
    )
    principal = _principal(role="admin", scopes=("admin:write",))
    service = AdminEvidenceService(
        session,
        correlation_id="corr-admin-guardrail-toggle",
        now=datetime.now(UTC),
        repository=FakeAdminRepository(),
        security_events=sink,
        agent_settings=agent_settings,
    )

    result = await service.set_guardrail_safety_enabled(
        principal=principal,
        enabled=False,
    )

    assert result.guardrail_safety_enabled is False
    assert result.trusted_supervisor_enabled is False
    assert agent_settings.writes == [
        {
            "setting": "guardrail",
            "enabled": False,
            "updated_by_user_id": principal.user_id,
        }
    ]
    assert sink.calls[0]["event_type"] == "guardrail_safety_toggled"
    assert sink.calls[0]["metadata"] == {
        "resource": "orchestration",
        "guardrail_safety_enabled": False,
    }
    assert session.commit_calls == 1


@pytest.mark.asyncio
async def test_admin_write_can_toggle_trusted_supervisor_agent() -> None:
    session = FakeAsyncSession()
    sink = FakeSecurityEventSink()
    agent_settings = FakeAgentSettingsRepository(
        guardrail_enabled=True,
        trusted_supervisor_enabled=False,
    )
    principal = _principal(role="admin", scopes=("admin:write",))
    service = AdminEvidenceService(
        session,
        correlation_id="corr-admin-trusted-supervisor-toggle",
        now=datetime.now(UTC),
        repository=FakeAdminRepository(),
        security_events=sink,
        agent_settings=agent_settings,
    )

    result = await service.set_trusted_supervisor_enabled(
        principal=principal,
        enabled=True,
        default_guardrail_enabled=True,
    )

    assert result.guardrail_safety_enabled is True
    assert result.trusted_supervisor_enabled is True
    assert agent_settings.writes == [
        {
            "setting": "trusted_supervisor",
            "enabled": True,
            "updated_by_user_id": principal.user_id,
        }
    ]
    assert sink.calls[0]["event_type"] == "trusted_supervisor_toggled"
    assert sink.calls[0]["metadata"] == {
        "resource": "orchestration",
        "trusted_supervisor_enabled": True,
    }
    assert session.commit_calls == 1


@pytest.mark.asyncio
async def test_admin_write_updates_role_bundle_and_records_event() -> None:
    now = datetime.now(UTC)
    target_id = uuid4()
    session = FakeAsyncSession()
    sink = FakeSecurityEventSink()
    accounts = FakeAccountsRepository(
        bundles={
            target_id: FakeUserBundle(
                user=FakeUser(
                    id=target_id,
                    email="target@example.test",
                    role="user",
                    is_active=True,
                    is_demo=False,
                    created_at=now,
                    updated_at=now,
                ),
                scopes=[FakeScopeRow(scope=scope) for scope in STANDARD_USER_SCOPES],
            )
        }
    )
    service = AdminEvidenceService(
        session,
        correlation_id="corr-admin-write-update",
        now=now,
        repository=FakeAdminRepository(),
        security_events=sink,
        accounts=accounts,
    )

    result = await service.update_user_access(
        principal=_principal(role="admin", scopes=("admin:write",)),
        target_user_id=target_id,
        role="admin",
        is_active=False,
    )

    assert result.changed_fields == ["is_active", "role", "scopes"]
    assert result.user.role == "admin"
    assert result.user.is_active is False
    assert result.user.scopes == sorted(ADMIN_SCOPES)
    assert sink.calls[0]["event_type"] == "admin_user_access_updated"
    assert sink.calls[0]["metadata"]["changed_fields"] == ["is_active", "role", "scopes"]
    assert session.flush_calls == 1
    assert session.commit_calls == 1


@pytest.mark.asyncio
async def test_admin_write_blocks_self_mutation_and_records_event() -> None:
    sink = FakeSecurityEventSink()
    session = FakeAsyncSession()
    principal = _principal(role="admin", scopes=("admin:write",))
    service = AdminEvidenceService(
        session,
        correlation_id="corr-admin-self-write",
        now=datetime.now(UTC),
        repository=FakeAdminRepository(),
        security_events=sink,
        accounts=FakeAccountsRepository(),
    )

    with pytest.raises(AdminWriteRejected) as exc_info:
        await service.update_user_access(
            principal=principal,
            target_user_id=principal.user_id,
            is_active=False,
        )

    assert exc_info.value.reason == "self_mutation_forbidden"
    assert sink.calls[0]["event_type"] == "admin_write_denied"
    assert sink.calls[0]["metadata"] == {
        "resource": "user_access",
        "reason": "self_mutation_forbidden",
    }
    assert session.commit_calls == 1


@pytest.mark.asyncio
async def test_security_event_metadata_is_recursively_redacted_before_serialization() -> None:
    now = datetime.now(UTC)
    repository = FakeAdminRepository(
        security_events=[
            SecurityEventRecord(
                id=uuid4(),
                event_type="provider_error",
                severity="medium",
                user_id=None,
                description="Provider request failed.",
                correlation_id="corr-sensitive-event",
                metadata={
                    "authorization": "Bearer should-not-leak",
                    "cookie": "__Host-simpagent_refresh=should-not-leak",
                    "prompt": "raw user prompt should not leave backend",
                    "provider_payload": {
                        "raw_grounding_json": {"secret": "canary-secret-value"},
                        "searchEntryPoint": {"renderedContent": "<div>raw html</div>"},
                    },
                    "nested": [{"api_key": "key-123"}, {"safe_count": 2}],
                    "safe": {"decision": "denied"},
                },
                created_at=now,
            )
        ]
    )
    service = AdminEvidenceService(
        None,
        correlation_id="corr-sensitive-event",
        now=now,
        repository=repository,
        security_events=FakeSecurityEventSink(),
    )

    result = await service.list_security_events(
        principal=_principal(role="admin", scopes=("admin:read",)),
        limit=10,
        offset=0,
    )

    item = result.items[0]
    dumped = item.model_dump_json()
    assert "should-not-leak" not in dumped
    assert "raw user prompt" not in dumped
    assert "raw_grounding_json" not in dumped
    assert "renderedContent" not in dumped
    assert "canary-secret-value" not in dumped
    assert item.metadata["authorization"] == "[REDACTED]"
    assert item.metadata["safe"] == {"decision": "denied"}
    assert item.snippets
    assert item.snippets[0].text
    assert len(item.snippets[0].text) <= 240


@pytest.mark.asyncio
async def test_tool_execution_evidence_keeps_correlation_but_redacts_prompt_and_full_output() -> None:
    now = datetime.now(UTC)
    user_id = uuid4()
    conversation_id = uuid4()
    repository = FakeAdminRepository(
        tool_executions=[
            ToolExecutionRecord(
                id=uuid4(),
                user_id=user_id,
                conversation_id=conversation_id,
                tool_name="python",
                input_summary="raw prompt: print secret token",
                output_summary=(
                    "container_id=abcdef123456 host_path=/var/run/docker.sock "
                    "full output with bearer token"
                ),
                status="denied",
                duration_ms=321,
                correlation_id="corr-tool-safe",
                created_at=now,
            )
        ]
    )
    service = AdminEvidenceService(
        None,
        correlation_id="corr-tool-safe",
        now=now,
        repository=repository,
        security_events=FakeSecurityEventSink(),
    )

    result = await service.list_tool_executions(
        principal=_principal(role="admin", scopes=("admin:read",)),
        limit=10,
        offset=0,
    )

    item = result.items[0]
    dumped = item.model_dump_json()
    assert str(user_id) in dumped
    assert str(conversation_id) in dumped
    assert item.tool_name == "python"
    assert item.status == "denied"
    assert item.duration_ms == 321
    assert item.correlation_id == "corr-tool-safe"
    assert "raw prompt" not in dumped
    assert "abcdef123456" not in dumped
    assert "/var/run/docker.sock" not in dumped
    assert "bearer token" not in dumped
    assert item.snippets
    assert all(len(snippet.text) <= 240 for snippet in item.snippets)


def test_gateway_evidence_service_reads_kong_contract_without_security_event_rows() -> None:
    service = GatewayEvidenceService.from_kong_config("kong/kong.yml")

    page = service.list_evidence(limit=10, offset=0)
    dumped = page.model_dump_json()

    assert page.items
    assert any(item.evidence_type == "rate_limit" for item in page.items)
    assert any(item.evidence_type == "request_size" for item in page.items)
    assert any(item.evidence_type == "correlation_id" for item in page.items)
    assert all(item.source == "kong_config" for item in page.items)
    assert "security_event" not in dumped
    assert "fabricated" not in dumped.casefold()


@pytest.mark.asyncio
async def test_admin_service_lists_gateway_evidence_for_authorized_admin() -> None:
    service = AdminEvidenceService(
        None,
        correlation_id="corr-gateway-admin",
        now=datetime.now(UTC),
        repository=FakeAdminRepository(),
        security_events=FakeSecurityEventSink(),
        gateway_evidence=GatewayEvidenceService.from_kong_config("kong/kong.yml"),
    )

    page = await service.list_gateway_evidence(
        principal=_principal(role="admin", scopes=("admin:read",)),
        limit=5,
        offset=0,
    )

    assert page.items
    assert page.page.limit == 5
    assert page.summary.correlation_id_enabled is True
    assert all(item.source == "kong_config" for item in page.items)


@pytest.mark.asyncio
async def test_admin_service_denies_gateway_evidence_without_admin_read() -> None:
    sink = FakeSecurityEventSink()
    service = AdminEvidenceService(
        None,
        correlation_id="corr-gateway-denied",
        now=datetime.now(UTC),
        repository=FakeAdminRepository(),
        security_events=sink,
        gateway_evidence=GatewayEvidenceService.from_kong_config("kong/kong.yml"),
    )

    with pytest.raises(AdminAccessDenied) as exc_info:
        await service.list_gateway_evidence(
            principal=_principal(role="user", scopes=("chat:read",)),
            limit=5,
            offset=0,
        )

    assert exc_info.value.decision is PolicyResult.deny_role
    assert sink.calls[0]["event_type"] == "admin_access_denied"
    assert sink.calls[0]["metadata"] == {
        "resource": "gateway_evidence",
        "required_scope": "admin:read",
        "decision": PolicyResult.deny_role.value,
    }
