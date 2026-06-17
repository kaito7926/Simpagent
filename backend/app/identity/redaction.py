from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from app.core.logging import sanitize_log_value


REDACTED = "[REDACTED]"
DEFAULT_SNIPPET_LIMIT = 240

_DROP_KEY_NAMES = {
    "container_id",
    "groundingmetadata",
    "host_path",
    "prompt",
    "raw_grounding_html",
    "raw_grounding_json",
    "raw_prompt",
    "renderedcontent",
    "searchentrypoint",
    "stderr",
    "stdout",
}
_DROP_KEY_PARTS = (
    "provider_payload",
    "sandbox_output",
)
_SENSITIVE_VALUE_MARKERS = (
    "/var/run/docker.sock",
    "bearer ",
    "container_id=",
    "__host-simpagent_csrf",
    "__host-simpagent_refresh",
    "postgresql+psycopg://",
)


@dataclass(frozen=True, slots=True)
class EvidenceSnippet:
    kind: str
    text: str
    truncated: bool

    def as_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "text": self.text, "truncated": self.truncated}


def sanitize_admin_evidence(value: Any, *, key: str | None = None) -> Any:
    if _should_drop_key(key):
        return None
    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for item_key, item_value in value.items():
            item_key_text = str(item_key)
            if _should_drop_key(item_key_text):
                continue
            sanitized_value = sanitize_admin_evidence(item_value, key=item_key_text)
            if sanitized_value is not None:
                sanitized[item_key_text] = sanitized_value
        return sanitized
    if isinstance(value, (str, bytes, Path, datetime, Exception)):
        return _sanitize_leaf(value, key=key)
    if _is_non_string_sequence(value):
        return [
            sanitized_item
            for item in value
            if (sanitized_item := sanitize_admin_evidence(item, key=key)) is not None
        ]
    return sanitize_log_value(value, key=key)


def summarize_admin_evidence(
    value: Any,
    *,
    kind: str = "metadata",
    limit: int = DEFAULT_SNIPPET_LIMIT,
) -> list[dict[str, Any]]:
    sanitized = sanitize_admin_evidence(value)
    text = _stringify_snippet_value(sanitized)
    if not text or text in {"{}", "[]"}:
        return []
    truncated = len(text) > limit
    snippet = EvidenceSnippet(
        kind=kind,
        text=text[:limit],
        truncated=truncated,
    )
    return [snippet.as_dict()]


def _sanitize_leaf(value: str | bytes | Path | datetime | Exception, *, key: str | None) -> Any:
    sanitized = sanitize_log_value(value, key=key)
    if isinstance(sanitized, str) and _looks_sensitive_string(sanitized):
        return REDACTED
    if isinstance(sanitized, Path):
        return str(sanitized)
    if isinstance(sanitized, datetime):
        return sanitized.astimezone(UTC).isoformat().replace("+00:00", "Z")
    return sanitized


def _should_drop_key(key: str | None) -> bool:
    if not key:
        return False
    normalized = key.casefold().replace("-", "_").replace(" ", "_")
    compact = normalized.replace("_", "")
    return compact in _DROP_KEY_NAMES or any(part in normalized for part in _DROP_KEY_PARTS)


def _looks_sensitive_string(value: str) -> bool:
    lowered = value.casefold()
    return any(marker in lowered for marker in _SENSITIVE_VALUE_MARKERS)


def _is_non_string_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _stringify_snippet_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
