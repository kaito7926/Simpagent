from __future__ import annotations

from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import AgentRuntimeSetting


GUARDRAIL_SETTING_KEY = "guardrail_safety_agent"
WEBSEARCH_PROVIDER_OVERRIDE_KEY = "websearch_provider_override"
WebsearchProviderOverride = Literal["gemini", "firecrawl"]
WEBSEARCH_PROVIDER_OVERRIDE_VALUES = frozenset({"gemini", "firecrawl"})


class AgentRuntimeSettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def is_guardrail_enabled(self, *, default: bool) -> bool:
        return await self._is_enabled(key=GUARDRAIL_SETTING_KEY, default=default)

    async def set_guardrail_enabled(
        self,
        *,
        enabled: bool,
        updated_by_user_id: UUID,
    ) -> AgentRuntimeSetting:
        return await self._set_enabled(
            key=GUARDRAIL_SETTING_KEY,
            enabled=enabled,
            updated_by_user_id=updated_by_user_id,
        )

    async def get_websearch_provider_override(self) -> WebsearchProviderOverride | None:
        setting = await self.session.scalar(
            select(AgentRuntimeSetting).where(AgentRuntimeSetting.key == WEBSEARCH_PROVIDER_OVERRIDE_KEY)
        )
        if setting is None or setting.value is None:
            return None
        if setting.value not in WEBSEARCH_PROVIDER_OVERRIDE_VALUES:
            return None
        return setting.value  # type: ignore[return-value]

    async def set_websearch_provider_override(
        self,
        *,
        provider: WebsearchProviderOverride | None,
        updated_by_user_id: UUID,
    ) -> AgentRuntimeSetting:
        if provider is not None and provider not in WEBSEARCH_PROVIDER_OVERRIDE_VALUES:
            raise ValueError("Unsupported websearch provider override.")
        setting = await self.session.scalar(
            select(AgentRuntimeSetting)
            .where(AgentRuntimeSetting.key == WEBSEARCH_PROVIDER_OVERRIDE_KEY)
            .with_for_update()
        )
        if setting is None:
            setting = AgentRuntimeSetting(
                key=WEBSEARCH_PROVIDER_OVERRIDE_KEY,
                enabled=True,
                value=provider,
                updated_by_user_id=updated_by_user_id,
            )
            self.session.add(setting)
        else:
            setting.value = provider
            setting.updated_by_user_id = updated_by_user_id
        await self.session.flush()
        return setting

    async def _is_enabled(self, *, key: str, default: bool) -> bool:
        setting = await self.session.scalar(
            select(AgentRuntimeSetting).where(AgentRuntimeSetting.key == key)
        )
        if setting is None:
            return default
        return bool(setting.enabled)

    async def _set_enabled(
        self,
        *,
        key: str,
        enabled: bool,
        updated_by_user_id: UUID,
    ) -> AgentRuntimeSetting:
        setting = await self.session.scalar(
            select(AgentRuntimeSetting)
            .where(AgentRuntimeSetting.key == key)
            .with_for_update()
        )
        if setting is None:
            setting = AgentRuntimeSetting(
                key=key,
                enabled=enabled,
                updated_by_user_id=updated_by_user_id,
            )
            self.session.add(setting)
        else:
            setting.enabled = enabled
            setting.updated_by_user_id = updated_by_user_id
        await self.session.flush()
        return setting
