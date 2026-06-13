from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import AgentRuntimeSetting


GUARDRAIL_SETTING_KEY = "guardrail_safety_agent"


class AgentRuntimeSettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def is_guardrail_enabled(self, *, default: bool) -> bool:
        setting = await self.session.scalar(
            select(AgentRuntimeSetting).where(AgentRuntimeSetting.key == GUARDRAIL_SETTING_KEY)
        )
        if setting is None:
            return default
        return bool(setting.enabled)

    async def set_guardrail_enabled(
        self,
        *,
        enabled: bool,
        updated_by_user_id: UUID,
    ) -> AgentRuntimeSetting:
        setting = await self.session.scalar(
            select(AgentRuntimeSetting)
            .where(AgentRuntimeSetting.key == GUARDRAIL_SETTING_KEY)
            .with_for_update()
        )
        if setting is None:
            setting = AgentRuntimeSetting(
                key=GUARDRAIL_SETTING_KEY,
                enabled=enabled,
                updated_by_user_id=updated_by_user_id,
            )
            self.session.add(setting)
        else:
            setting.enabled = enabled
            setting.updated_by_user_id = updated_by_user_id
        await self.session.flush()
        return setting
