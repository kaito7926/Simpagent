from __future__ import annotations

import json
import logging

from app.core.logging import JsonFormatter, reset_correlation_id, set_correlation_id


def test_json_formatter_includes_correlation_and_redacts_sensitive_fields() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="simpagent.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="structured test log",
        args=(),
        exc_info=None,
    )
    record.event = "test_event"
    record.user_id = "user-1"
    record.authorization = "Bearer top-secret-token"
    record.database_url = "postgresql+psycopg://postgres:postgres@postgres:5432/simpagent"

    token = set_correlation_id("corr-log-1")
    try:
        payload = json.loads(formatter.format(record))
    finally:
        reset_correlation_id(token)

    assert payload["correlation_id"] == "corr-log-1"
    assert payload["event"] == "test_event"
    assert payload["user_id"] == "user-1"
    assert payload["authorization"] == "[REDACTED]"
    assert payload["database_url"] == "[REDACTED]"
