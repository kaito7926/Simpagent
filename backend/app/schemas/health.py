from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


AggregateStatus = Literal["ready", "degraded", "not_ready"]
DatabaseStatus = Literal["ready", "unavailable"]
MigrationStatus = Literal["ready", "out_of_date", "unknown"]
ProviderStatus = Literal["ready", "unconfigured", "model_unavailable", "unavailable"]
SandboxStatus = Literal["foundation_ready", "unavailable"]


class ReadinessComponents(BaseModel):
    database: DatabaseStatus
    migrations: MigrationStatus
    llm: ProviderStatus
    search: ProviderStatus
    sandbox: SandboxStatus


class ReadinessResponse(BaseModel):
    status: AggregateStatus
    components: ReadinessComponents
