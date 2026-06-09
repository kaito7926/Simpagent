from __future__ import annotations

from app.core.provider_status import compute_provider_snapshot


def test_provider_snapshot_is_sanitized(settings) -> None:
    snapshot = compute_provider_snapshot(settings)
    assert snapshot.llm in {"ready", "unconfigured"}
    assert snapshot.search in {"ready", "unconfigured"}
    assert snapshot.sandbox == "foundation_ready"
