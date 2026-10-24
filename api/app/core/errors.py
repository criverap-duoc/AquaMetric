"""Domain errors rendered as RFC 9457 `application/problem+json`.

Every failure leaves the API through this module so clients always receive the same
shape as TerraPlan (stable `code`, Spanish `detail`, correlation id).
"""

import logging
from typing import ClassVar, TypedDict
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

PROBLEM_MEDIA_TYPE = "application/problem+json"

logger = logging.getLogger(__name__)


class FieldError(TypedDict):
    """Per-field validation message returned in `errors[]`."""

    field: str
    message: str


class ProblemDetail(TypedDict):
    """Problem document shared with TerraPlan; keys are camelCase as the public contract."""

    type: str
    title: str
    status: int
    code: str
    detail: str
    requestId: str
    errors: list[FieldError]


class DomainError(Exception):
    """Base class for expected business failures.

    Subclasses only declare `code`, `status` and `title`, so routers never map errors
    by hand and the stable code table lives in one place.
    """

    code: ClassVar[str] = "INTERNAL"
    status: ClassVar[int] = 500
    title: ClassVar[str] = "Internal error"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


# Status -> (code, title, Spanish detail) for errors raised by the framework layer.
_HTTP_ERRORS: dict[int, tuple[str, str, str]] = {
    400: ("VALIDATION_ERROR", "Invalid request", "La solicitud contiene datos inválidos."),
    401: ("UNAUTHORIZED", "Unauthorized", "Falta la API key o no es válida."),
    404: ("NOT_FOUND", "Not found", "El recurso solicitado no existe."),
    409: ("CONFLICT", "Conflict", "La solicitud entra en conflicto con el estado actual."),
}
# Unmapped statuses come from framework guards (e.g. 405), which are client errors.
_FALLBACK_HTTP_ERROR = (
    "VALIDATION_ERROR",
    "Request rejected",
    "La solicitud no pudo procesarse.",
)


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "") or uuid4().hex)


def _problem_response(
    *,
    request: Request,
    status: int,
    code: str,
    title: str,
    detail: str,
    errors: list[FieldError] | None = None,
) -> JSONResponse:
    payload = ProblemDetail(
        type="about:blank",
        title=title,
        status=status,
        code=code,
        detail=detail,
        requestId=_request_id(request),
        errors=errors or [],
    )
    return JSONResponse(
        status_code=status,
        content=payload,
        media_type=PROBLEM_MEDIA_TYPE,
    )


async def handle_domain_error(request: Request, exc: Exception) -> Response:
    if not isinstance(exc, DomainError):
        return await handle_unexpected_error(request, exc)
    if exc.status >= 500:
        logger.error("domain error", extra={"code": exc.code})
    return _problem_response(
        request=request,
        status=exc.status,
        code=exc.code,
        title=exc.title,
        detail=exc.detail,
    )


async def handle_validation_error(request: Request, exc: Exception) -> Response:
    raw_errors = exc.errors() if isinstance(exc, RequestValidationError) else []
    errors: list[FieldError] = [
        FieldError(
            field=".".join(str(part) for part in error["loc"]),
            message=str(error["msg"]),
        )
        for error in raw_errors
    ]
    return _problem_response(
        request=request,
        status=400,
        code="VALIDATION_ERROR",
        title="Invalid request",
        detail="La solicitud contiene datos inválidos.",
        errors=errors,
    )


async def handle_http_error(request: Request, exc: Exception) -> Response:
    status = exc.status_code if isinstance(exc, StarletteHTTPException) else 500
    if status >= 500:
        return await handle_unexpected_error(request, exc)
    code, title, detail = _HTTP_ERRORS.get(status, _FALLBACK_HTTP_ERROR)
    return _problem_response(
        request=request,
        status=status,
        code=code,
        title=title,
        detail=detail,
    )


async def handle_unexpected_error(request: Request, exc: Exception) -> Response:
    logger.exception("unhandled error", extra={"requestId": _request_id(request)})
    return _problem_response(
        request=request,
        status=500,
        code="INTERNAL",
        title="Internal error",
        detail="Ocurrió un error interno. Intenta nuevamente o cita el requestId.",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Single registration point: handlers keep problem+json consistent across routers."""
    app.add_exception_handler(DomainError, handle_domain_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
