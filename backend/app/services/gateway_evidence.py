from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Literal

from app.identity.redaction import sanitize_admin_evidence, summarize_admin_evidence
from app.schemas.admin import (
    AdminPage,
    GatewayEvidenceItem,
    GatewayEvidencePage,
    GatewayEvidenceSummary,
)


GatewayEvidenceKind = Literal["rate_limit", "request_size", "correlation_id", "route_protection"]


@dataclass(frozen=True, slots=True)
class GatewayEvidenceSummaryCard:
    title: str
    value: int | bool
    description: str


@dataclass(frozen=True, slots=True)
class GatewayEvidenceRecord:
    id: str
    evidence_type: GatewayEvidenceKind
    source: Literal["kong_config", "kong_log"]
    route: str | None
    plugin: str
    status_codes: list[int]
    summary: str
    metadata: dict

    def to_item(self) -> GatewayEvidenceItem:
        safe_metadata = sanitize_admin_evidence(self.metadata)
        return GatewayEvidenceItem(
            id=self.id,
            evidence_type=self.evidence_type,
            source=self.source,
            route=self.route,
            plugin=self.plugin,
            status_codes=self.status_codes,
            summary=self.summary,
            metadata=safe_metadata,
            snippets=summarize_admin_evidence(safe_metadata, kind="gateway_evidence"),
        )


class GatewayEvidenceService:
    def __init__(self, *, records: list[GatewayEvidenceRecord]) -> None:
        self._records = records

    @classmethod
    def from_kong_config(cls, config_path: str | Path) -> "GatewayEvidenceService":
        path = Path(config_path)
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        return cls(records=_records_from_kong_text(text, config_path=str(path), config_available=path.exists()))

    def list_evidence(self, *, limit: int = 25, offset: int = 0) -> GatewayEvidencePage:
        limit = max(1, min(limit, 100))
        offset = max(0, offset)
        window = self._records[offset : offset + limit + 1]
        has_more = len(window) > limit
        items = [record.to_item() for record in window[:limit]]
        return GatewayEvidencePage(
            items=items,
            page=AdminPage(
                limit=limit,
                offset=offset,
                has_more=has_more,
                next_offset=offset + limit if has_more else None,
            ),
            summary=self.summary(),
        )

    def summary(self) -> GatewayEvidenceSummary:
        return GatewayEvidenceSummary(
            rate_limit_routes=sum(1 for record in self._records if record.evidence_type == "rate_limit"),
            request_size_routes=sum(1 for record in self._records if record.evidence_type == "request_size"),
            correlation_id_enabled=any(
                record.evidence_type == "correlation_id" for record in self._records
            ),
            route_protection_routes=sum(
                1 for record in self._records if record.evidence_type == "route_protection"
            ),
        )

    def summary_cards(self) -> list[GatewayEvidenceSummaryCard]:
        summary = self.summary()
        return [
            GatewayEvidenceSummaryCard(
                title="Rate limit routes",
                value=summary.rate_limit_routes,
                description="Kong routes protected by local rate limiting.",
            ),
            GatewayEvidenceSummaryCard(
                title="Request size routes",
                value=summary.request_size_routes,
                description="Kong routes protected by request-size limiting.",
            ),
            GatewayEvidenceSummaryCard(
                title="Correlation ID",
                value=summary.correlation_id_enabled,
                description="Kong injects or echoes X-Correlation-Id.",
            ),
        ]


def _records_from_kong_text(
    text: str,
    *,
    config_path: str,
    config_available: bool,
) -> list[GatewayEvidenceRecord]:
    records: list[GatewayEvidenceRecord] = []
    source_metadata = {"config_path": config_path, "config_available": config_available}
    if not text:
        return _fallback_records(source_metadata)

    if "name: correlation-id" in text and "X-Correlation-Id" in text:
        records.append(
            GatewayEvidenceRecord(
                id="kong-config-correlation-id",
                evidence_type="correlation_id",
                source="kong_config",
                route=None,
                plugin="correlation-id",
                status_codes=[],
                summary="Kong is configured to generate and echo X-Correlation-Id.",
                metadata={**source_metadata, "header_name": "X-Correlation-Id"},
            )
        )

    for route, minute in _plugin_routes(text, plugin_name="rate-limiting", config_key="minute"):
        records.append(
            GatewayEvidenceRecord(
                id=f"kong-config-rate-limit-{route}",
                evidence_type="rate_limit",
                source="kong_config",
                route=route,
                plugin="rate-limiting",
                status_codes=[429],
                summary=f"Kong local rate limiting protects route {route}.",
                metadata={**source_metadata, "route": route, "minute": minute, "policy": "local"},
            )
        )

    for route, allowed_payload_size in _plugin_routes(
        text,
        plugin_name="request-size-limiting",
        config_key="allowed_payload_size",
    ):
        records.append(
            GatewayEvidenceRecord(
                id=f"kong-config-request-size-{route}",
                evidence_type="request_size",
                source="kong_config",
                route=route,
                plugin="request-size-limiting",
                status_codes=[413],
                summary=f"Kong request-size limiting protects route {route}.",
                metadata={
                    **source_metadata,
                    "route": route,
                    "allowed_payload_size_mb": allowed_payload_size,
                },
            )
        )

    for route in _cors_routes(text):
        records.append(
            GatewayEvidenceRecord(
                id=f"kong-config-route-protection-{route}",
                evidence_type="route_protection",
                source="kong_config",
                route=route,
                plugin="cors",
                status_codes=[],
                summary=f"Kong CORS policy is attached to route {route}.",
                metadata={**source_metadata, "route": route, "strict_origins": True},
            )
        )
    return records


def _plugin_routes(text: str, *, plugin_name: str, config_key: str) -> list[tuple[str, int | None]]:
    pattern = re.compile(
        rf"- name: {re.escape(plugin_name)}\s+"
        rf"(?:instance_name: [^\n]+\s+)?"
        rf"route: (?P<route>[^\n]+)\s+"
        rf"config:(?P<config>.*?)(?=\n  - name:|\Z)",
        re.S,
    )
    routes: list[tuple[str, int | None]] = []
    for match in pattern.finditer(text):
        config = match.group("config")
        value_match = re.search(rf"{re.escape(config_key)}:\s*(?P<value>\d+)", config)
        routes.append(
            (
                match.group("route").strip(),
                int(value_match.group("value")) if value_match else None,
            )
        )
    return routes


def _cors_routes(text: str) -> list[str]:
    return [
        match.group("route").strip()
        for match in re.finditer(r"- name: cors\s+route: (?P<route>[^\n]+)", text)
    ]


def _fallback_records(metadata: dict) -> list[GatewayEvidenceRecord]:
    return [
        GatewayEvidenceRecord(
            id="kong-config-correlation-id",
            evidence_type="correlation_id",
            source="kong_config",
            route=None,
            plugin="correlation-id",
            status_codes=[],
            summary="Kong correlation evidence is expected from the declarative config.",
            metadata=metadata,
        ),
        GatewayEvidenceRecord(
            id="kong-config-rate-limit",
            evidence_type="rate_limit",
            source="kong_config",
            route=None,
            plugin="rate-limiting",
            status_codes=[429],
            summary="Kong rate-limit evidence is represented separately from FastAPI rows.",
            metadata=metadata,
        ),
        GatewayEvidenceRecord(
            id="kong-config-request-size",
            evidence_type="request_size",
            source="kong_config",
            route=None,
            plugin="request-size-limiting",
            status_codes=[413],
            summary="Kong request-size evidence is represented separately from FastAPI rows.",
            metadata=metadata,
        ),
    ]
