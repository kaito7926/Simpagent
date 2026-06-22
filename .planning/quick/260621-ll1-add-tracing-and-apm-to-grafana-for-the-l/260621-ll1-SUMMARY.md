---
status: complete
date: 2026-06-21
commit: uncommitted
---

# Quick Task 260621-ll1 Summary

## Completed

- Added guarded OpenTelemetry tracing to the FastAPI backend and exported request/database/client spans directly to Tempo over OTLP HTTP.
- Enriched backend JSON logs with `trace_id` and `span_id`, and attached `simpagent.correlation_id` to the active span for log-trace pivoting.
- Extended the local observability topology with Tempo plus Grafana Loki/Tempo datasource provisioning and `trace_id`-based navigation.
- Added coverage for tracing profile/configuration and a smoke test that proves Kong request -> Loki log -> Tempo trace correlation.
- Documented local tracing/APM usage for Grafana in `README.md`.

## Verification

- `python -m pytest -q backend/tests/unit/test_logging.py backend/tests/unit/test_config.py backend/tests/integration/gateway/test_observability_tracing_profile.py` passed (`18 passed`).
- `docker compose config -q` passed.
- `docker compose -f compose.test.yaml build backend-test` completed successfully.
- `docker compose build backend` completed successfully.
- `docker compose up --wait` passed with backend, Kong, Loki, Tempo, Grafana, Promtail, and sandbox healthy.
- `docker compose run --rm -e SIMPAGENT_RUN_SMOKE=true backend python -m pytest -q tests/smoke/test_tracing_flow.py` passed (`1 passed`).
- `curl.exe -i -H "X-Correlation-Id: trace-smoke-260621-01" http://localhost:8000/health` returned `200 OK` and echoed the correlation header through Kong.
- `docker compose exec -T backend curl -fsS http://tempo:3200/api/traces/b3e0478ae3e79501eb9cb14998abb891` returned the exported FastAPI trace containing `simpagent.correlation_id=trace-smoke-260621-01`.

## Notes

- Grafana startup logs confirmed datasource provisioning for Tempo with `uid=tempo`.
- Direct Grafana API auth may depend on the persisted `grafana-data` volume state; datasource provisioning was verified from mounted provisioning files and Grafana logs.
