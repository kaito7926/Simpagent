from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


@dataclass(slots=True)
class ApiError(Exception):
    status_code: int
    code: str
    message: str
    extra: dict[str, Any] | None = None


class ErrorEnvelope(JSONResponse):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        correlation_id: str | None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        content: dict[str, Any] = {
            "error": {
                "code": code,
                "message": message,
            }
        }
        if correlation_id:
            content["error"]["correlation_id"] = correlation_id
        if extra:
            content["error"].update(extra)
        super().__init__(status_code=status_code, content=content)


async def api_error_handler(request: Request, exc: ApiError) -> ErrorEnvelope:
    return ErrorEnvelope(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        correlation_id=getattr(request.state, "correlation_id", None),
        extra=exc.extra,
    )


async def generic_error_handler(request: Request, exc: Exception) -> ErrorEnvelope:
    return ErrorEnvelope(
        status_code=500,
        code="internal_error",
        message="A server error occurred. Please try again.",
        correlation_id=getattr(request.state, "correlation_id", None),
    )


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)
