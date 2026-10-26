"""Public reads of the stored observations (01 §5).

Both endpoints are GETs: the UI is read-only and the single write path into the table stays
`POST /api/v1/ingest/observations`, where validation and idempotency live (ADR-009).
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import AwareDatetime

from app.core.config import OBSERVATIONS_PAGE_SIZE_MAX
from app.core.db import SessionDep
from app.core.dependencies import CatalogDep
from app.schemas.observation import (
    ObservationAggregateRead,
    ObservationOrder,
    ObservationsResponse,
)
from app.services.observation_service import ObservationService

router = APIRouter(prefix="/observations", tags=["observations"])

_SITE_ID = Query(
    alias="siteId",
    description="Sitio (UUID) cuyas observaciones se quieren; omitido, devuelve todos.",
)
_PARAMETER_CODE = Query(
    alias="parameterCode",
    description="Código del parámetro del catálogo, p. ej. PH.",
    examples=["PH"],
)
_FROM = Query(
    alias="from",
    description="Inicio del rango sobre `analyzedAt` (ISO-8601 con zona). Inclusivo.",
)
_TO = Query(
    alias="to",
    description="Fin del rango sobre `analyzedAt` (ISO-8601 con zona). Inclusivo.",
)
_ORDER = Query(
    description=(
        "Orden cronológico: `desc` (más reciente primero, para la tabla) o `asc` "
        "(para la carta de control, que trabaja sobre la ventana de la fase I)."
    )
)


@router.get(
    "",
    response_model=ObservationsResponse,
    summary="List observations",
    description=(
        "One page of `aquametric.observation`, filtered by site, parameter and analyzed-at "
        "window. Every row carries `siteCode`, so a screen needs one request instead of two. "
        "Censored results travel as `value = null` + `qualifier = '<'` + `loq`, never as 0 nor as "
        "LOQ/2 (ADR-003). The `total` of `meta` counts every row that matches the filter, not the "
        "rows of the page."
    ),
    responses={
        400: {"description": "UNKNOWN_PARAMETER, or a date without timezone"},
        404: {"description": "NOT_FOUND: the site does not exist"},
        500: {"description": "Unhandled error, returned as application/problem+json"},
    },
)
async def list_observations(
    session: SessionDep,
    catalog: CatalogDep,
    site_id: Annotated[UUID | None, _SITE_ID] = None,
    parameter_code: Annotated[str | None, _PARAMETER_CODE] = None,
    from_dt: Annotated[AwareDatetime | None, _FROM] = None,
    to_dt: Annotated[AwareDatetime | None, _TO] = None,
    page: Annotated[int, Query(ge=1, description="Página, desde 1.")] = 1,
    page_size: Annotated[
        int,
        Query(
            alias="pageSize",
            ge=1,
            le=OBSERVATIONS_PAGE_SIZE_MAX,
            description=f"Observaciones por página (1–{OBSERVATIONS_PAGE_SIZE_MAX}).",
        ),
    ] = 100,
    order: Annotated[ObservationOrder, _ORDER] = "desc",
) -> ObservationsResponse:
    """Public read: the observations the Series screen plots are not sensitive."""
    service = ObservationService(session, catalog)
    return await service.list_observations(
        site_id=site_id,
        parameter_code=parameter_code,
        from_dt=from_dt,
        to_dt=to_dt,
        page=page,
        page_size=page_size,
        order=order,
    )


@router.get(
    "/aggregate",
    response_model=ObservationAggregateRead,
    summary="Aggregate one window of observations",
    description=(
        "Count, censored count, minimum, maximum and mean of the window in a single query. The "
        "statistics use measured values only: a `< LOQ` row has no number, and substituting "
        "`LOQ/2` would publish an invented measurement (ADR-003). It answers «cuántas "
        "observaciones hay» without downloading them."
    ),
    responses={
        400: {"description": "UNKNOWN_PARAMETER, or a date without timezone"},
        404: {"description": "NOT_FOUND: the site does not exist"},
        500: {"description": "Unhandled error, returned as application/problem+json"},
    },
)
async def aggregate_observations(
    session: SessionDep,
    catalog: CatalogDep,
    site_id: Annotated[UUID | None, _SITE_ID] = None,
    parameter_code: Annotated[str | None, _PARAMETER_CODE] = None,
    from_dt: Annotated[AwareDatetime | None, _FROM] = None,
    to_dt: Annotated[AwareDatetime | None, _TO] = None,
) -> ObservationAggregateRead:
    """Public read: an aggregate of public rows is public."""
    service = ObservationService(session, catalog)
    return await service.aggregate(
        site_id=site_id,
        parameter_code=parameter_code,
        from_dt=from_dt,
        to_dt=to_dt,
    )
