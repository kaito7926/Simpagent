from __future__ import annotations

import json
import re

import httpx
import pytest

from tests.smoke._helpers import (
    PUBLIC_BASE_URL,
    poll_loki_lines,
    poll_tempo_trace,
    require_smoke,
    unique_correlation_id,
)


TRACE_ID_PATTERN = re.compile(r'"trace_id":"([a-f0-9]{32})"')


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_tempo_tracing_exports_backend_request_and_preserves_log_trace_correlation() -> None:
    require_smoke()

    correlation_id = unique_correlation_id("corr-trace-health")

    async with httpx.AsyncClient(base_url=PUBLIC_BASE_URL, timeout=25.0, follow_redirects=True) as client:
        response = await client.get("/health", headers={"X-Correlation-Id": correlation_id})

    assert response.status_code == 200
    assert response.headers["x-correlation-id"] == correlation_id

    backend_access_lines = await poll_loki_lines(
        f'{{service="backend"}} |= "{correlation_id}" |= "\\"event\\":\\"http_request\\""'
    )
    trace_id = next(
        (
            match.group(1)
            for line in backend_access_lines
            if (match := TRACE_ID_PATTERN.search(line)) is not None
        ),
        None,
    )

    assert trace_id is not None

    trace_payload = await poll_tempo_trace(trace_id)

    assert trace_payload.get("batches")

    trace_dump = json.dumps(trace_payload)
    assert correlation_id in trace_dump
    assert "simpagent-backend" in trace_dump
    assert "/health" in trace_dump
