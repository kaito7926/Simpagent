from __future__ import annotations

import contextvars
from datetime import UTC, datetime
import json
import logging
import logging.config
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.core.tracing import get_trace_context


_correlation_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "simpagent_correlation_id",
    default=None,
)
_configured_signature: tuple[str, str | None] | None = None

_STANDARD_RECORD_FIELDS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
    "correlation_id",
}
_REDACTED = "[REDACTED]"
_SENSITIVE_KEY_PARTS = (
    "authorization",
    "cookie",
    "csrf",
    "password",
    "refresh_token",
    "secret",
    "set_cookie",
    "token",
)
_SENSITIVE_VALUE_MARKERS = (
    "-----begin",
    "bearer ",
    "__host-simpagent_refresh",
    "__host-simpagent_csrf",
    "postgresql+psycopg://",
)


def set_correlation_id(correlation_id: str | None) -> contextvars.Token[str | None]:
    return _correlation_id_var.set(correlation_id)


def reset_correlation_id(token: contextvars.Token[str | None]) -> None:
    _correlation_id_var.reset(token)


def get_correlation_id() -> str | None:
    return _correlation_id_var.get()


def _is_sensitive_key(key: str | None) -> bool:
    if not key:
        return False
    normalized = key.casefold().replace("-", "_")
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS) or normalized.endswith("_key")


def _looks_sensitive_string(value: str) -> bool:
    lowered = value.casefold()
    return any(marker in lowered for marker in _SENSITIVE_VALUE_MARKERS)


def sanitize_log_value(value: Any, *, key: str | None = None) -> Any:
    if _is_sensitive_key(key):
        return _REDACTED

    if isinstance(value, dict):
        return {
            str(item_key): sanitize_log_value(item_value, key=str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [sanitize_log_value(item, key=key) for item in value]
    if isinstance(value, bytes):
        return _REDACTED
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, Exception):
        return value.__class__.__name__
    if isinstance(value, str) and _looks_sensitive_string(value):
        return _REDACTED
    return value


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not getattr(record, "correlation_id", None):
            record.correlation_id = get_correlation_id()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat().replace(
                "+00:00", "Z"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        correlation_id = getattr(record, "correlation_id", None) or get_correlation_id()
        if correlation_id:
            payload["correlation_id"] = correlation_id
        trace_id, span_id = get_trace_context()
        if trace_id:
            payload["trace_id"] = trace_id
        if span_id:
            payload["span_id"] = span_id

        extra_fields = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _STANDARD_RECORD_FIELDS and not key.startswith("_")
        }
        if extra_fields:
            payload.update(
                sanitize_log_value(extra_fields)
                if isinstance(extra_fields, dict)
                else {"fields": sanitize_log_value(extra_fields)}
            )

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)

        return json.dumps(sanitize_log_value(payload), ensure_ascii=False, separators=(",", ":"))


def configure_logging(settings: Settings) -> None:
    global _configured_signature

    signature = (settings.log_level, settings.log_file_path)
    if _configured_signature == signature:
        return

    handlers: dict[str, dict[str, Any]] = {
        "console": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "json",
            "filters": ["request_context"],
        }
    }
    root_handlers = ["console"]

    if settings.log_file_path:
        log_path = Path(settings.log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers["file"] = {
            "class": "logging.FileHandler",
            "filename": str(log_path),
            "encoding": "utf-8",
            "formatter": "json",
            "filters": ["request_context"],
        }
        root_handlers.append("file")

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "request_context": {
                    "()": "app.core.logging.RequestContextFilter",
                }
            },
            "formatters": {
                "json": {
                    "()": "app.core.logging.JsonFormatter",
                }
            },
            "handlers": handlers,
            "root": {
                "level": settings.log_level,
                "handlers": root_handlers,
            },
            "loggers": {
                "uvicorn.access": {
                    "level": settings.log_level,
                    "handlers": root_handlers,
                    "propagate": False,
                },
                "uvicorn.error": {
                    "level": settings.log_level,
                    "handlers": root_handlers,
                    "propagate": False,
                },
            },
        }
    )
    _configured_signature = signature
