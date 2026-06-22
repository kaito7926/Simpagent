from __future__ import annotations

import logging
from typing import Final

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Settings


logger = logging.getLogger("simpagent.tracing")
TRACE_CORRELATION_ATTRIBUTE: Final[str] = "simpagent.correlation_id"
_configured_signature: tuple[bool, str | None, str, int, float] | None = None
_httpx_instrumented = False
_instrumented_app_ids: set[int] = set()
_instrumented_engine_ids: set[int] = set()


def tracing_is_enabled(settings: Settings) -> bool:
    return settings.otel_tracing_enabled and bool(settings.otel_exporter_otlp_traces_endpoint)


def configure_tracing(settings: Settings) -> None:
    global _configured_signature, _httpx_instrumented

    if not tracing_is_enabled(settings):
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
    except ModuleNotFoundError:
        logger.warning(
            "tracing_dependency_missing",
            extra={"event": "tracing_config", "service_name": settings.otel_service_name},
        )
        return

    signature = (
        settings.otel_tracing_enabled,
        settings.otel_exporter_otlp_traces_endpoint,
        settings.otel_service_name,
        settings.otel_exporter_otlp_timeout_seconds,
        settings.otel_sample_ratio,
    )
    if _configured_signature == signature:
        return
    if _configured_signature is not None:
        logger.warning(
            "tracing_reconfiguration_skipped",
            extra={
                "event": "tracing_config",
                "service_name": settings.otel_service_name,
            },
        )
        return

    resource = Resource.create(
        {
            SERVICE_NAME: settings.otel_service_name,
            SERVICE_VERSION: "0.1.0",
            "deployment.environment": settings.app_env,
        }
    )
    provider = TracerProvider(
        resource=resource,
        sampler=TraceIdRatioBased(settings.otel_sample_ratio),
    )
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=settings.otel_exporter_otlp_traces_endpoint,
                timeout=settings.otel_exporter_otlp_timeout_seconds,
            )
        )
    )
    trace.set_tracer_provider(provider)

    if not _httpx_instrumented:
        HTTPXClientInstrumentor().instrument(tracer_provider=provider)
        _httpx_instrumented = True

    _configured_signature = signature


def instrument_app(app: FastAPI, settings: Settings) -> None:
    if not tracing_is_enabled(settings):
        return
    try:
        from opentelemetry import trace
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    except ModuleNotFoundError:
        return
    if id(app) in _instrumented_app_ids:
        return
    FastAPIInstrumentor.instrument_app(app, tracer_provider=trace.get_tracer_provider())
    _instrumented_app_ids.add(id(app))


def instrument_engine(engine: AsyncEngine, settings: Settings) -> None:
    sync_engine = engine.sync_engine
    if not tracing_is_enabled(settings):
        return
    try:
        from opentelemetry import trace
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    except ModuleNotFoundError:
        return
    if id(sync_engine) in _instrumented_engine_ids:
        return
    SQLAlchemyInstrumentor().instrument(
        engine=sync_engine,
        tracer_provider=trace.get_tracer_provider(),
        enable_commenter=False,
    )
    _instrumented_engine_ids.add(id(sync_engine))


def get_trace_context() -> tuple[str | None, str | None]:
    try:
        from opentelemetry import trace
    except ModuleNotFoundError:
        return None, None
    span_context = trace.get_current_span().get_span_context()
    if not span_context.is_valid:
        return None, None
    return f"{span_context.trace_id:032x}", f"{span_context.span_id:016x}"


def set_current_span_attribute(name: str, value: str) -> None:
    try:
        from opentelemetry import trace
    except ModuleNotFoundError:
        return
    span = trace.get_current_span()
    span_context = span.get_span_context()
    if not span_context.is_valid:
        return
    span.set_attribute(name, value)
