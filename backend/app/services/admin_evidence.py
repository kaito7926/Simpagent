from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.authorization.policy import PolicyResult, evaluate_admin_access
from app.authorization.principal import AuthenticatedPrincipal
from app.db.repositories.accounts import AccountsRepository, UserBundle
from app.db.repositories.admin import (
    AdminEvidenceRepository,
    AdminMetricsRecord,
    AdminUserRecord,
    SecurityEventRecord,
    ToolExecutionRecord,
)
from app.db.repositories.agent_settings import AgentRuntimeSettingsRepository
from app.db.repositories.sessions import SessionsRepository
from app.identity.redaction import REDACTED, sanitize_admin_evidence, summarize_admin_evidence
from app.core.provider_status import SEARCH_PROVIDER_ALLOWLIST
from app.schemas.admin import (
    AdminMetricsResponse,
    AdminPage,
    AdminUserItem,
    AdminUserUpdateResponse,
    AdminUsersPage,
    GatewayEvidencePage,
    OrchestrationSettingsResponse,
    SecurityEventItem,
    SecurityEventsPage,
    ToolExecutionItem,
    ToolExecutionsPage,
)
from app.schemas.auth import ADMIN_SCOPES, STANDARD_USER_SCOPES
from app.services.gateway_evidence import GatewayEvidenceService


class AdminEvidenceRepositoryProtocol(Protocol):
    async def list_users(self, *, limit: int, offset: int) -> tuple[list[AdminUserRecord], bool]: ...

    async def list_security_events(
        self,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[SecurityEventRecord], bool]: ...

    async def list_tool_executions(
        self,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[ToolExecutionRecord], bool]: ...

    async def get_metrics(self, *, since: datetime) -> AdminMetricsRecord: ...


class SecurityEventSinkProtocol(Protocol):
    async def add_security_event(
        self,
        *,
        event_type: str,
        severity: str,
        user_id,
        description: str,
        correlation_id: str | None,
        metadata: dict | None = None,
    ): ...


class AccountsRepositoryProtocol(Protocol):
    async def get_user_bundle_by_id(self, user_id) -> UserBundle | None: ...

    async def replace_user_scopes(self, user_id, scopes: list[str]) -> None: ...

    async def replace_bundle_scopes(self, bundle: UserBundle, scopes: list[str]) -> None: ...


@dataclass(frozen=True, slots=True)
class AdminAccessDenied(ValueError):
    decision: PolicyResult
    required_scope: str
    resource: str


@dataclass(frozen=True, slots=True)
class AdminWriteRejected(ValueError):
    reason: Literal["self_mutation_forbidden", "invalid_websearch_provider"]


class AdminEvidenceService:
    def __init__(
        self,
        session: AsyncSession | None,
        *,
        correlation_id: str | None,
        now: datetime | None = None,
        repository: AdminEvidenceRepositoryProtocol | None = None,
        security_events: SecurityEventSinkProtocol | None = None,
        accounts: AccountsRepositoryProtocol | None = None,
        agent_settings: AgentRuntimeSettingsRepository | None = None,
        gateway_evidence: GatewayEvidenceService | None = None,
    ) -> None:
        self.session = session
        self.now = now or datetime.now(UTC)
        self.correlation_id = correlation_id
        self.repository = repository or AdminEvidenceRepository(session)
        self.security_events = security_events or SessionsRepository(session)
        self.accounts = accounts or AccountsRepository(session)
        self.agent_settings = agent_settings or AgentRuntimeSettingsRepository(session)
        self.gateway_evidence = gateway_evidence or GatewayEvidenceService.from_kong_config("kong/kong.yml")

    async def list_users(
        self,
        *,
        principal: AuthenticatedPrincipal,
        limit: int = 25,
        offset: int = 0,
    ) -> AdminUsersPage:
        limit, offset = self._normalize_page(limit=limit, offset=offset)
        await self._require_admin_scope(principal=principal, required_scope="admin:read", resource="users")
        rows, has_more = await self.repository.list_users(limit=limit, offset=offset)
        return AdminUsersPage(
            items=[
                AdminUserItem(
                    id=row.id,
                    email=row.email,
                    role=row.role,
                    scopes=row.scopes,
                    is_active=row.is_active,
                    is_demo=row.is_demo,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
                for row in rows
            ],
            page=self._page(limit=limit, offset=offset, has_more=has_more),
        )

    async def list_security_events(
        self,
        *,
        principal: AuthenticatedPrincipal,
        limit: int = 25,
        offset: int = 0,
    ) -> SecurityEventsPage:
        limit, offset = self._normalize_page(limit=limit, offset=offset)
        await self._require_admin_scope(
            principal=principal,
            required_scope="admin:read",
            resource="security_events",
        )
        rows, has_more = await self.repository.list_security_events(limit=limit, offset=offset)
        return SecurityEventsPage(
            items=[
                SecurityEventItem(
                    id=row.id,
                    event_type=row.event_type,
                    severity=row.severity,
                    user_id=row.user_id,
                    description=row.description,
                    correlation_id=row.correlation_id,
                    metadata=sanitize_admin_evidence(row.metadata),
                    snippets=summarize_admin_evidence(row.metadata, kind="metadata"),
                    created_at=row.created_at,
                )
                for row in rows
            ],
            page=self._page(limit=limit, offset=offset, has_more=has_more),
        )

    async def list_tool_executions(
        self,
        *,
        principal: AuthenticatedPrincipal,
        limit: int = 25,
        offset: int = 0,
    ) -> ToolExecutionsPage:
        limit, offset = self._normalize_page(limit=limit, offset=offset)
        await self._require_admin_scope(
            principal=principal,
            required_scope="admin:read",
            resource="tool_executions",
        )
        rows, has_more = await self.repository.list_tool_executions(limit=limit, offset=offset)
        return ToolExecutionsPage(
            items=[
                self._tool_execution_item(row)
                for row in rows
            ],
            page=self._page(limit=limit, offset=offset, has_more=has_more),
        )

    async def get_metrics(self, *, principal: AuthenticatedPrincipal) -> AdminMetricsResponse:
        await self._require_admin_scope(principal=principal, required_scope="admin:read", resource="metrics")
        snapshot = await self.repository.get_metrics(since=self.now - timedelta(hours=24))
        return AdminMetricsResponse(
            generated_at=self.now,
            users_total=snapshot.users_total,
            users_active=snapshot.users_active,
            security_events_total=snapshot.security_events_total,
            security_events_last_24h=snapshot.security_events_last_24h,
            tool_executions_total=snapshot.tool_executions_total,
            tool_executions_last_24h=snapshot.tool_executions_last_24h,
            correlation_references_total=snapshot.correlation_references_total,
            rate_limit_events_total=snapshot.rate_limit_events_total,
        )

    async def list_gateway_evidence(
        self,
        *,
        principal: AuthenticatedPrincipal,
        limit: int = 25,
        offset: int = 0,
    ) -> GatewayEvidencePage:
        limit, offset = self._normalize_page(limit=limit, offset=offset)
        await self._require_admin_scope(
            principal=principal,
            required_scope="admin:read",
            resource="gateway_evidence",
        )
        return self.gateway_evidence.list_evidence(limit=limit, offset=offset)

    async def get_orchestration_settings(
        self,
        *,
        principal: AuthenticatedPrincipal,
        default_guardrail_enabled: bool = True,
        websearch_provider_default: str = "gemini",
        websearch_provider_readiness: str = "unconfigured",
    ) -> OrchestrationSettingsResponse:
        await self._require_admin_scope(
            principal=principal,
            required_scope="admin:read",
            resource="orchestration",
        )
        guardrail_enabled = await self.agent_settings.is_guardrail_enabled(default=default_guardrail_enabled)
        provider_override = await self.agent_settings.get_websearch_provider_override()
        effective_provider = provider_override or websearch_provider_default
        return OrchestrationSettingsResponse(
            guardrail_safety_enabled=guardrail_enabled,
            websearch_provider_default=websearch_provider_default,
            websearch_provider_override=provider_override,
            websearch_provider_effective=effective_provider,
            websearch_provider_readiness=websearch_provider_readiness,
        )

    async def set_guardrail_safety_enabled(
        self,
        *,
        principal: AuthenticatedPrincipal,
        enabled: bool,
        websearch_provider_default: str = "gemini",
        websearch_provider_readiness: str = "unconfigured",
    ) -> OrchestrationSettingsResponse:
        await self._require_admin_scope(
            principal=principal,
            required_scope="admin:write",
            resource="orchestration",
        )
        if self.session is None:
            raise RuntimeError("An active database session is required for orchestration writes.")

        try:
            setting = await self.agent_settings.set_guardrail_enabled(
                enabled=enabled,
                updated_by_user_id=principal.user_id,
            )
            await self.security_events.add_security_event(
                event_type="guardrail_safety_toggled",
                severity="info",
                user_id=principal.user_id,
                description="Admin updated guardrail safety agent state.",
                correlation_id=self.correlation_id,
                metadata={
                    "resource": "orchestration",
                    "guardrail_safety_enabled": setting.enabled,
                },
            )
            await self.session.commit()
        except Exception:
            if self.session.in_transaction():
                await self.session.rollback()
            raise
        provider_override = await self.agent_settings.get_websearch_provider_override()
        effective_provider = provider_override or websearch_provider_default
        return OrchestrationSettingsResponse(
            guardrail_safety_enabled=enabled,
            websearch_provider_default=websearch_provider_default,
            websearch_provider_override=provider_override,
            websearch_provider_effective=effective_provider,
            websearch_provider_readiness=websearch_provider_readiness,
        )

    async def set_websearch_provider_override(
        self,
        *,
        principal: AuthenticatedPrincipal,
        provider: str | None,
        websearch_provider_default: str = "gemini",
        websearch_provider_readiness: str = "unconfigured",
        default_guardrail_enabled: bool = True,
    ) -> OrchestrationSettingsResponse:
        await self._require_admin_scope(
            principal=principal,
            required_scope="admin:write",
            resource="orchestration",
        )
        if self.session is None:
            raise RuntimeError("An active database session is required for orchestration writes.")
        if provider is not None and provider not in SEARCH_PROVIDER_ALLOWLIST:
            await self._record_admin_write_denial(
                principal=principal,
                resource="orchestration",
                reason="invalid_websearch_provider",
            )
            raise AdminWriteRejected(reason="invalid_websearch_provider")

        try:
            setting = await self.agent_settings.set_websearch_provider_override(
                provider=provider,  # type: ignore[arg-type]
                updated_by_user_id=principal.user_id,
            )
            provider_override = setting.value if setting.value in SEARCH_PROVIDER_ALLOWLIST else None
            effective_provider = provider_override or websearch_provider_default
            await self.security_events.add_security_event(
                event_type="websearch_provider_override_set"
                if provider_override is not None
                else "websearch_provider_override_cleared",
                severity="info",
                user_id=principal.user_id,
                description="Admin updated websearch provider runtime override.",
                correlation_id=self.correlation_id,
                metadata={
                    "resource": "orchestration",
                    "websearch_provider_default": websearch_provider_default,
                    "websearch_provider_override": provider_override,
                    "websearch_provider_effective": effective_provider,
                    "websearch_provider_readiness": websearch_provider_readiness,
                },
            )
            await self.session.commit()
        except Exception:
            if self.session.in_transaction():
                await self.session.rollback()
            raise

        guardrail_enabled = await self.agent_settings.is_guardrail_enabled(default=default_guardrail_enabled)
        return OrchestrationSettingsResponse(
            guardrail_safety_enabled=guardrail_enabled,
            websearch_provider_default=websearch_provider_default,
            websearch_provider_override=provider_override,
            websearch_provider_effective=effective_provider,
            websearch_provider_readiness=websearch_provider_readiness,
        )

    async def update_user_access(
        self,
        *,
        principal: AuthenticatedPrincipal,
        target_user_id,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> AdminUserUpdateResponse:
        await self._require_admin_scope(principal=principal, required_scope="admin:write", resource="user_access")
        if self.session is None:
            raise RuntimeError("An active database session is required for admin write operations.")
        if principal.user_id == target_user_id:
            await self._record_admin_write_denial(
                principal=principal,
                resource="user_access",
                reason="self_mutation_forbidden",
            )
            raise AdminWriteRejected(reason="self_mutation_forbidden")

        changed_fields: list[str] = []
        try:
            bundle = await self.accounts.get_user_bundle_by_id(target_user_id)
            if bundle is None:
                raise LookupError("User not found")

            if role is not None:
                expected_scopes = list(ADMIN_SCOPES if role == "admin" else STANDARD_USER_SCOPES)
                current_scopes = sorted(scope.scope for scope in bundle.scopes)
                if bundle.user.role != role:
                    bundle.user.role = role
                    changed_fields.append("role")
                if current_scopes != expected_scopes:
                    await self.accounts.replace_bundle_scopes(bundle, expected_scopes)
                    changed_fields.append("scopes")

            if is_active is not None and bundle.user.is_active != is_active:
                bundle.user.is_active = is_active
                changed_fields.append("is_active")

            await self.session.flush()
            self.session.expire_all()
            updated_bundle = await self.accounts.get_user_bundle_by_id(target_user_id)
            if updated_bundle is None:
                raise LookupError("User not found")

            normalized_changed_fields = sorted(dict.fromkeys(changed_fields))
            if normalized_changed_fields:
                await self.security_events.add_security_event(
                    event_type="admin_user_access_updated",
                    severity="info",
                    user_id=principal.user_id,
                    description="Admin updated user access.",
                    correlation_id=self.correlation_id,
                    metadata={
                        "resource": "users",
                        "target_user_id": str(updated_bundle.user.id),
                        "changed_fields": normalized_changed_fields,
                        "role": updated_bundle.user.role,
                        "is_active": updated_bundle.user.is_active,
                        "scopes_count": len(updated_bundle.scopes),
                    },
                )
            await self.session.commit()
        except Exception:
            if self.session.in_transaction():
                await self.session.rollback()
            raise

        return AdminUserUpdateResponse(
            user=self._user_item_from_bundle(updated_bundle),
            changed_fields=sorted(dict.fromkeys(changed_fields)),
        )

    async def _require_admin_scope(
        self,
        *,
        principal: AuthenticatedPrincipal,
        required_scope: str,
        resource: str,
    ) -> None:
        decision = evaluate_admin_access(
            principal_role=principal.role,
            principal_scopes=set(principal.scopes),
            required_scope=required_scope,
        )
        if decision is PolicyResult.allow:
            return

        await self.security_events.add_security_event(
            event_type="admin_access_denied",
            severity="medium",
            user_id=principal.user_id,
            description="Admin evidence access denied.",
            correlation_id=self.correlation_id,
            metadata={
                "resource": resource,
                "required_scope": required_scope,
                "decision": decision.value,
            },
        )
        if self.session is not None:
            await self.session.commit()
        raise AdminAccessDenied(
            decision=decision,
            required_scope=required_scope,
            resource=resource,
        )

    async def _record_admin_write_denial(
        self,
        *,
        principal: AuthenticatedPrincipal,
        resource: str,
        reason: str,
    ) -> None:
        await self.security_events.add_security_event(
            event_type="admin_write_denied",
            severity="medium",
            user_id=principal.user_id,
            description="Admin write action denied.",
            correlation_id=self.correlation_id,
            metadata={
                "resource": resource,
                "reason": reason,
            },
        )
        if self.session is not None:
            await self.session.commit()

    def _normalize_page(self, *, limit: int, offset: int) -> tuple[int, int]:
        return max(1, min(limit, 100)), max(0, offset)

    def _page(self, *, limit: int, offset: int, has_more: bool) -> AdminPage:
        return AdminPage(
            limit=limit,
            offset=offset,
            has_more=has_more,
            next_offset=offset + limit if has_more else None,
        )

    def _tool_execution_item(self, row: ToolExecutionRecord) -> ToolExecutionItem:
        safe_input = sanitize_admin_evidence(row.input_summary, key="prompt") or REDACTED
        safe_output = (
            sanitize_admin_evidence(row.output_summary, key="sandbox_output")
            if row.output_summary is not None
            else None
        )
        snippet_payload = {
            "input_summary": safe_input,
            "output_summary": safe_output,
            "status": row.status,
            "duration_ms": row.duration_ms,
            "correlation_id": row.correlation_id,
        }
        return ToolExecutionItem(
            id=row.id,
            user_id=row.user_id,
            conversation_id=row.conversation_id,
            tool_name=row.tool_name,
            input_summary=safe_input,
            output_summary=safe_output,
            status=row.status,
            duration_ms=row.duration_ms,
            correlation_id=row.correlation_id,
            snippets=summarize_admin_evidence(snippet_payload, kind="tool_execution"),
            created_at=row.created_at,
        )

    def _user_item_from_bundle(self, bundle: UserBundle) -> AdminUserItem:
        return AdminUserItem(
            id=bundle.user.id,
            email=bundle.user.email,
            role=bundle.user.role,
            scopes=sorted(scope.scope for scope in bundle.scopes),
            is_active=bundle.user.is_active,
            is_demo=bundle.user.is_demo,
            created_at=bundle.user.created_at,
            updated_at=bundle.user.updated_at,
        )
