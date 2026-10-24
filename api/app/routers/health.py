"""Liveness probe: the only public surface shipped in phase A-1."""

from fastapi import APIRouter, Request
from pydantic import AwareDatetime

from app import SERVICE_NAME, __version__
from app.core.clock import ClockDep
from app.core.config import SettingsDep
from app.schemas.base import CamelModel

router = APIRouter(prefix="/api/v1", tags=["health"])


class HealthResponse(CamelModel):
    """Readiness signal for uptime monitors and the deploy checklist."""

    status: str
    service: str
    version: str
    env: str
    timestamp: AwareDatetime
    request_id: str


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Returns 200 while the process can serve requests. Public: no API key required.",
    responses={
        500: {"description": "Unhandled error, returned as application/problem+json"},
    },
)
async def read_health(
    request: Request,
    settings: SettingsDep,
    clock: ClockDep,
) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=SERVICE_NAME,
        version=__version__,
        env=settings.env,
        timestamp=clock.now(),
        request_id=getattr(request.state, "request_id", ""),
    )
