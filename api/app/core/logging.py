"""Structured JSON logging plus per-request correlation ids."""

import json
import logging
import sys
import time
from datetime import UTC, datetime
from typing import Final
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER: Final = "X-Request-ID"
REQUEST_LOGGER: Final = "app.request"

_RESERVED_ATTRIBUTES: Final = frozenset(
    logging.LogRecord("_", logging.INFO, "", 0, "", None, None).__dict__
) | {"message", "asctime", "taskName"}


class JsonFormatter(logging.Formatter):
    """One JSON object per line, so log aggregators can filter by requestId or code."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(
            {
                key: value
                for key, value in record.__dict__.items()
                if key not in _RESERVED_ATTRIBUTES
            }
        )
        if record.exc_info is not None:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Called once per process; `force` keeps uvicorn reload workers on the same format."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)


class RequestIdMiddleware:
    """Correlate logs and responses: one id in request state, headers and problem bodies."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _incoming_request_id(scope) or uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        started_at = time.perf_counter()

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
                _log_request(scope, request_id, int(message["status"]), started_at)
            await send(message)

        await self.app(scope, receive, send_with_request_id)


def _incoming_request_id(scope: Scope) -> str | None:
    """Honour a client-provided id but cap its length: it ends up in logs and headers."""
    value = Headers(scope=scope).get(REQUEST_ID_HEADER)
    if value is None:
        return None
    return value.strip()[:128] or None


def _log_request(scope: Scope, request_id: str, status: int, started_at: float) -> None:
    logging.getLogger(REQUEST_LOGGER).info(
        "%s %s -> %s",
        scope["method"],
        scope["path"],
        status,
        extra={
            "requestId": request_id,
            "status": status,
            "durationMs": round((time.perf_counter() - started_at) * 1000, 2),
        },
    )
