"""SPC endpoints: public charts and the single authenticated write of the slice (02 §5, ADR-001).

Only `POST /spc/baseline` writes and therefore requires `X-API-Key`; the three GETs are public and
read-only, which is why `GET /spc/control-charts` computes the limits on the fly instead of
persisting them. Every response repeats that these are control limits, not normative limits.
"""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.config import SettingsDep
from app.core.db import SessionDep
from app.core.dependencies import CatalogDep, ClockDep
from app.core.security import get_ingest_key
from app.schemas.spc import (
    BaselineRead,
    BaselineUpsertRequest,
    ControlChartResponse,
    RuleViolationRead,
)
from app.services.spc_service import SpcService
from app.spc.constants import MIN_BASELINE_POINTS

router = APIRouter(prefix="/spc", tags=["spc"])

_SITE_ID = Query(alias="siteId", description="Sitio (UUID) al que pertenece la serie.")
_PARAMETER_CODE = Query(
    alias="parameterCode",
    description="Código del parámetro del catálogo, p. ej. PH.",
    examples=["PH"],
)
_BASELINE_POINTS = Query(
    alias="baselinePoints",
    ge=MIN_BASELINE_POINTS,
    le=200,
    description="Observaciones de la fase I usadas para estimar los límites (mínimo 20).",
)


@router.get(
    "/control-charts",
    response_model=ControlChartResponse,
    summary="Control chart (I-MR) of one series",
    description=(
        "Estimates the Phase I control limits from the oldest `baselinePoints` observations and "
        "scans the following `monitoringPoints` against them (rules R1–R5). The limits are "
        "computed on the fly and flagged as such unless a baseline was persisted for the series. "
        "These are control limits estimated from the process, not normative limits: a point out "
        "of control is a change in the process, not a breach of a standard."
    ),
    responses={
        400: {"description": "UNKNOWN_PARAMETER"},
        422: {"description": "INSUFFICIENT_DATA: the series cannot support limits"},
        500: {"description": "Unhandled error, returned as application/problem+json"},
    },
)
async def get_control_charts(
    session: SessionDep,
    catalog: CatalogDep,
    clock: ClockDep,
    settings: SettingsDep,
    site_id: Annotated[UUID, _SITE_ID],
    parameter_code: Annotated[str, _PARAMETER_CODE],
    baseline_points: Annotated[int, _BASELINE_POINTS] = MIN_BASELINE_POINTS,
    monitoring_points: Annotated[
        int,
        Query(
            alias="monitoringPoints",
            ge=1,
            le=500,
            description="Observaciones posteriores a la fase I que se evalúan contra los límites.",
        ),
    ] = 100,
) -> ControlChartResponse:
    """Public on purpose: reading a chart stores nothing."""
    service = SpcService(
        session,
        catalog,
        clock,
        censored_max_fraction=settings.censored_max_fraction,
        baseline_min_points=settings.baseline_min_points,
    )
    return await service.compute_chart(
        site_id,
        parameter_code,
        baseline_points=baseline_points,
        monitoring_points=monitoring_points,
    )


@router.get(
    "/baseline",
    response_model=BaselineRead,
    summary="Persisted Phase I baseline of one series",
    description=(
        "The frozen limits stored for a (site, parameter, phase), with the data range and the "
        "catalog version they were computed against. Answers 404 when the series was never "
        "persisted: limits computed on the fly are not a baseline."
    ),
    responses={
        400: {"description": "UNKNOWN_PARAMETER"},
        404: {"description": "NOT_FOUND: no baseline persisted for that series"},
        500: {"description": "Unhandled error, returned as application/problem+json"},
    },
)
async def get_baseline(
    session: SessionDep,
    catalog: CatalogDep,
    clock: ClockDep,
    site_id: Annotated[UUID, _SITE_ID],
    parameter_code: Annotated[str, _PARAMETER_CODE],
    phase: Annotated[
        Literal["phase_i", "phase_ii"],
        Query(description="Fase de los límites; `phase_i` son los congelados del MVP."),
    ] = "phase_i",
) -> BaselineRead:
    """Public read: the stored limits are the same numbers any client would get."""
    service = SpcService(session, catalog, clock)
    return await service.get_persisted_baseline(site_id, parameter_code, phase)


@router.post(
    "/baseline",
    response_model=BaselineRead,
    status_code=status.HTTP_201_CREATED,
    summary="Freeze the Phase I baseline of one series",
    description=(
        "Computes the I-MR limits from the oldest `baselinePoints` observations and stores them "
        "for the series, replacing any previous baseline of the same phase. Re-posting the same "
        "series recomputes the limits and keeps a single row."
    ),
    responses={
        400: {
            "description": "UNKNOWN_PARAMETER, VALIDATION_ERROR, or method='xbar_r' (not persisted)"
        },
        401: {"description": "UNAUTHORIZED: missing or invalid X-API-Key"},
        422: {"description": "INSUFFICIENT_DATA: the series cannot support limits"},
        500: {"description": "Unhandled error, returned as application/problem+json"},
    },
)
async def post_baseline(
    payload: BaselineUpsertRequest,
    session: SessionDep,
    catalog: CatalogDep,
    clock: ClockDep,
    _api_key: Annotated[str, Depends(get_ingest_key)],
) -> BaselineRead:
    """Writing endpoint: `X-API-Key` is mandatory (ADR-011)."""
    service = SpcService(session, catalog, clock)
    return await service.persist_baseline(payload)


@router.get(
    "/rules",
    response_model=list[RuleViolationRead],
    summary="Signals found in the monitoring window of one series",
    description=(
        "The list `GET /spc/control-charts` returns under `violations`: R1 one point beyond 3σ, "
        "R2 nine consecutive points on one side, R3 six increasing or decreasing, R4 two of "
        "three beyond 2σ, R5 four of five beyond 1σ. An empty list means in control."
    ),
    responses={
        400: {"description": "UNKNOWN_PARAMETER"},
        422: {"description": "INSUFFICIENT_DATA: the series cannot support limits"},
        500: {"description": "Unhandled error, returned as application/problem+json"},
    },
)
async def get_rules(
    session: SessionDep,
    catalog: CatalogDep,
    clock: ClockDep,
    site_id: Annotated[UUID, _SITE_ID],
    parameter_code: Annotated[str, _PARAMETER_CODE],
    baseline_points: Annotated[int, _BASELINE_POINTS] = MIN_BASELINE_POINTS,
) -> list[RuleViolationRead]:
    """Public read: the UI shows the signals next to the chart."""
    service = SpcService(session, catalog, clock)
    return await service.get_rules(site_id, parameter_code, baseline_points=baseline_points)
