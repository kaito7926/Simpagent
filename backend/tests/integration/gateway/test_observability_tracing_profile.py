from __future__ import annotations

import json
import os
from pathlib import Path


REPO_ROOT = Path(os.getenv("SIMPAGENT_REPO_ROOT", "/workspace/repo"))
if not REPO_ROOT.exists():
    REPO_ROOT = Path(__file__).resolve().parents[4]

ENV_EXAMPLE = REPO_ROOT / ".env.example"
COMPOSE_FILE = REPO_ROOT / "compose.yaml"
TEMPO_CONFIG = REPO_ROOT / "observability" / "tempo-config.yaml"
LOKI_DATASOURCE = REPO_ROOT / "observability" / "grafana" / "provisioning" / "datasources" / "loki.yaml"
TEMPO_DATASOURCE = REPO_ROOT / "observability" / "grafana" / "provisioning" / "datasources" / "tempo.yaml"
DASHBOARD_PROVIDER = REPO_ROOT / "observability" / "grafana" / "provisioning" / "dashboards" / "default.yaml"
OVERVIEW_DASHBOARD = (
    REPO_ROOT
    / "observability"
    / "grafana"
    / "provisioning"
    / "dashboards"
    / "simpagent-observability-overview.json"
)
REQUEST_JOURNEY_DASHBOARD = (
    REPO_ROOT
    / "observability"
    / "grafana"
    / "provisioning"
    / "dashboards"
    / "simpagent-request-journey.json"
)


def test_env_example_documents_local_tracing_profile() -> None:
    contents = ENV_EXAMPLE.read_text(encoding="utf-8")

    for expected in (
        "OTEL_TRACING_ENABLED=true",
        "OTEL_SERVICE_NAME=simpagent-backend",
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://tempo:4318/v1/traces",
        "OTEL_EXPORTER_OTLP_TIMEOUT_SECONDS=5",
        "OTEL_SAMPLE_RATIO=1.0",
        "SIMPAGENT_OTEL_TRACING_ENABLED=false",
        "SIMPAGENT_OTEL_SERVICE_NAME=simpagent-backend",
        "SIMPAGENT_OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://tempo:4318/v1/traces",
    ):
        assert expected in contents


def test_compose_exposes_tempo_and_backend_otlp_export() -> None:
    contents = COMPOSE_FILE.read_text(encoding="utf-8")

    for expected in (
        "tempo:",
        "grafana/tempo:2.10.7",
        "SIMPAGENT_OTEL_TRACING_ENABLED",
        "SIMPAGENT_OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
        "http://tempo:4318/v1/traces",
        "tempo-data:",
    ):
        assert expected in contents


def test_grafana_provisions_loki_to_tempo_trace_links() -> None:
    loki_contents = LOKI_DATASOURCE.read_text(encoding="utf-8")
    tempo_contents = TEMPO_DATASOURCE.read_text(encoding="utf-8")

    assert "uid: loki" in loki_contents
    assert "derivedFields:" in loki_contents
    assert 'matcherRegex: \'"trace_id":"([a-f0-9]{32})"\'' in loki_contents
    assert "datasourceUid: tempo" in loki_contents

    assert "type: tempo" in tempo_contents
    assert "uid: tempo" in tempo_contents
    assert "url: http://tempo:3200" in tempo_contents
    assert 'trace_id="$${__trace.traceId}"' in tempo_contents


def test_tempo_config_accepts_otlp_and_local_trace_storage() -> None:
    contents = TEMPO_CONFIG.read_text(encoding="utf-8")

    for expected in (
        "otlp:",
        "endpoint: 0.0.0.0:4318",
        "endpoint: 0.0.0.0:4317",
        "backend: local",
        "path: /var/tempo/wal",
        "path: /var/tempo/blocks",
    ):
        assert expected in contents


def test_grafana_dashboard_provider_points_to_provisioned_dashboards() -> None:
    contents = DASHBOARD_PROVIDER.read_text(encoding="utf-8")

    for expected in (
        "name: SimpAgent Dashboards",
        "folder: SimpAgent",
        "type: file",
        "editable: false",
        "path: /etc/grafana/provisioning/dashboards",
    ):
        assert expected in contents
    assert OVERVIEW_DASHBOARD.exists()
    assert REQUEST_JOURNEY_DASHBOARD.exists()


def test_grafana_observability_dashboard_is_valid_and_uses_loki_uid() -> None:
    payload = json.loads(OVERVIEW_DASHBOARD.read_text(encoding="utf-8"))

    assert payload["uid"] == "simpagent-observability"
    assert payload["title"] == "SimpAgent Observability Overview"
    assert payload["refresh"] == "10s"
    assert payload["time"] == {"from": "now-6h", "to": "now"}

    panels = payload["panels"]
    assert len(panels) >= 8
    assert any(panel["type"] == "logs" for panel in panels)
    assert any(panel["type"] == "timeseries" for panel in panels)
    assert any(panel["type"] == "stat" for panel in panels)

    loki_targets = [
        target
        for panel in panels
        for target in panel.get("targets", [])
        if target.get("datasource", {}).get("uid") == "loki"
    ]
    assert loki_targets
    assert any("trace" in panel["title"].lower() for panel in panels)


def test_grafana_request_journey_dashboard_filters_by_correlation_id() -> None:
    payload = json.loads(REQUEST_JOURNEY_DASHBOARD.read_text(encoding="utf-8"))

    assert payload["uid"] == "simpagent-request-journey"
    assert payload["title"] == "SimpAgent Request Journey"
    assert payload["refresh"] == "10s"
    assert payload["time"] == {"from": "now-1h", "to": "now"}

    panels = payload["panels"]
    assert len(panels) >= 6
    assert any(panel["type"] == "text" for panel in panels)
    assert any(panel["type"] == "logs" for panel in panels)
    assert any(panel["type"] == "stat" for panel in panels)

    variables = {item["name"]: item for item in payload["templating"]["list"]}
    assert variables["journey_correlation_id"]["type"] == "textbox"
    assert variables["journey_correlation_id"]["query"] == ".*"
    assert variables["journey_path"]["type"] == "textbox"
    assert variables["journey_path"]["query"] == ".*"

    loki_targets = [
        target
        for panel in panels
        for target in panel.get("targets", [])
        if target.get("datasource", {}).get("uid") == "loki"
    ]
    assert loki_targets
    assert any('correlation_id=~"${journey_correlation_id}"' in target.get("expr", "") for target in loki_targets)
    assert any('path=~"${journey_path}"' in target.get("expr", "") for target in loki_targets)
    assert any("tool_execution" in target.get("expr", "") for target in loki_targets)
    assert any("View trace" in panel["title"] for panel in panels)
