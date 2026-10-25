"""Screening endpoints: public read-only analysis, no API key required (02 §5)."""

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.core.dependencies import CatalogDep
from app.schemas.screening import (
    ScreeningLimitsResponse,
    ScreeningRequest,
    ScreeningResponse,
)
from app.services.screening_service import ScreeningService

router = APIRouter(prefix="/screening", tags=["screening"])

# Stated once and reused: the disclaimer is part of the contract, not a UI detail.
_REFERENTIAL_NOTE = (
    "Referencial: no es un dictamen de cumplimiento legal. Solo los límites con "
    "`status = validated` producen `normal`, `above_range` o `below_range`; el resto responde "
    "`not_evaluable` con el motivo."
)


@router.post(
    "/evaluate",
    response_model=ScreeningResponse,
    status_code=status.HTTP_200_OK,
    summary="Screen one observation against a catalog limit",
    description=(
        "Compares a single value with the limit selected by regulation and scope "
        "(NCh 1.333: `context`; D.S. 53/2014: `monitoringArea` + `qualityLevel`). "
        + _REFERENTIAL_NOTE
    ),
    responses={
        400: {"description": "UNKNOWN_PARAMETER or UNIT_MISMATCH"},
        500: {"description": "Unhandled error, returned as application/problem+json"},
    },
)
async def evaluate_observation(
    payload: ScreeningRequest,
    catalog: CatalogDep,
) -> ScreeningResponse:
    """Public on purpose: screening analyses a value, it does not store anything."""
    return ScreeningService(catalog).evaluate(payload)


@router.get(
    "/limits",
    response_model=ScreeningLimitsResponse,
    summary="List the limits a screening can cite",
    description=(
        "Every catalog limit of the parameter and regulation, optionally narrowed by scope. "
        "Draft limits are included so the selector can label them «Pendiente de validación»; "
        "`requiresValidated` is always `true` in the MVP. " + _REFERENTIAL_NOTE
    ),
    responses={
        400: {"description": "UNKNOWN_PARAMETER"},
        500: {"description": "Unhandled error, returned as application/problem+json"},
    },
)
async def list_screening_limits(
    catalog: CatalogDep,
    parameter_code: Annotated[
        str, Query(alias="parameterCode", description="Código del parámetro, p. ej. PH.")
    ],
    regulation: Annotated[str, Query(description="Código de la regulación, p. ej. NCh1333.")],
    context: Annotated[str | None, Query(description="Uso del agua (NCh 1.333).")] = None,
    monitoring_area: Annotated[
        str | None, Query(alias="monitoringArea", description="Área de vigilancia (D.S. 53/2014).")
    ] = None,
    quality_level: Annotated[
        str | None, Query(alias="qualityLevel", description="Nivel de calidad (D.S. 53/2014).")
    ] = None,
) -> ScreeningLimitsResponse:
    limits = ScreeningService(catalog).available_limits(
        parameter_code=parameter_code,
        regulation=regulation,
        context=context,
        monitoring_area=monitoring_area,
        quality_level=quality_level,
    )
    return ScreeningLimitsResponse(limits=limits, requires_validated=True)
