"""Catalog endpoints: public, read-only views of the synchronized catalog (ADR-005)."""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query

from app.core.dependencies import CatalogDep
from app.schemas.catalog import (
    CatalogMetaResponse,
    LimitRead,
    LimitsMeta,
    LimitsResponse,
    ParameterRead,
    RegulationRead,
    UnitRead,
)

# FastAPI's `responses` mapping is untyped (`Any` at the framework boundary); one shared value
# keeps the five catalog endpoints documented the same way.
_ERRORS: dict[int | str, dict[str, Any]] = {
    500: {"description": "Unhandled error, returned as application/problem+json"}
}

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get(
    "/meta",
    response_model=CatalogMetaResponse,
    summary="Catalog provenance",
    description=(
        "Version, bundle sha256 and signature state of the copy synchronized from TerraPlan. "
        "`status = draft-verified` means the chemist has not signed the values yet."
    ),
    responses=_ERRORS,
)
async def read_catalog_meta(catalog: CatalogDep) -> CatalogMetaResponse:
    return CatalogMetaResponse(
        version=catalog.version,
        sha256=catalog.sha256,
        generated_at=catalog.generated_at,
        status=catalog.status,
        validated_by=catalog.validated_by,
        validated_at=catalog.validated_at,
    )


@router.get(
    "/parameters",
    response_model=list[ParameterRead],
    summary="List catalog parameters",
    description="Every parameter, with its canonical unit and the decimals the UI must show.",
    responses=_ERRORS,
)
async def list_parameters(catalog: CatalogDep) -> list[ParameterRead]:
    return [ParameterRead.model_validate(item) for item in catalog.parameters.values()]


@router.get(
    "/units",
    response_model=list[UnitRead],
    summary="List catalog units",
    description="Every unit with the explicit factor that converts it to its canonical unit.",
    responses=_ERRORS,
)
async def list_units(catalog: CatalogDep) -> list[UnitRead]:
    return [UnitRead.model_validate(item) for item in catalog.units.values()]


@router.get(
    "/limits",
    response_model=LimitsResponse,
    summary="List catalog limits",
    description=(
        "Every limit matching the filters, whatever its `status` or `statistic`: the catalog "
        "browser must show what exists, including limits still pending validation. The filter "
        "is `regulation` (query) and the field is `regulationCode` (response): same vocabulary "
        "as the synchronized catalog. `meta.validatedCount` tells how many of the returned "
        "limits can actually produce a screening flag."
    ),
    responses=_ERRORS,
)
async def list_catalog_limits(
    catalog: CatalogDep,
    parameter_code: Annotated[
        str | None, Query(alias="parameterCode", description="Código del parámetro, p. ej. PH.")
    ] = None,
    regulation: Annotated[
        str | None,
        Query(
            description=(
                "Código de la regulación, p. ej. NCh1333. En la respuesta el campo se llama "
                "`regulationCode`."
            )
        ),
    ] = None,
    context: Annotated[str | None, Query(description="Uso del agua (NCh 1.333).")] = None,
    monitoring_area: Annotated[
        str | None, Query(alias="monitoringArea", description="Área de vigilancia (D.S. 53/2014).")
    ] = None,
    quality_level: Annotated[
        str | None, Query(alias="qualityLevel", description="Nivel de calidad (D.S. 53/2014).")
    ] = None,
    limit_status: Annotated[
        Literal["draft-verified", "validated"] | None,
        Query(
            alias="status",
            description=(
                "Filtra por estado de validación: `validated` solo los firmados por el químico, "
                "`draft-verified` solo los pendientes."
            ),
        ),
    ] = None,
) -> LimitsResponse:
    filtered = [
        limit
        for limit in catalog.limits
        if (parameter_code is None or limit.parameter_code == parameter_code)
        and (regulation is None or limit.regulation_code == regulation)
        and (context is None or limit.context == context)
        and (monitoring_area is None or limit.monitoring_area_code == monitoring_area)
        and (quality_level is None or limit.quality_level == quality_level)
        and (limit_status is None or limit.status == limit_status)
    ]
    validated = sum(1 for limit in filtered if limit.status == "validated")
    return LimitsResponse(
        data=[LimitRead.model_validate(limit) for limit in filtered],
        meta=LimitsMeta(
            total=len(filtered),
            validated_count=validated,
            draft_count=len(filtered) - validated,
        ),
    )


@router.get(
    "/regulations",
    response_model=list[RegulationRead],
    summary="List regulations",
    description="Regulations the catalog quotes limits from, with the scope each one covers.",
    responses=_ERRORS,
)
async def list_regulations(catalog: CatalogDep) -> list[RegulationRead]:
    return [RegulationRead.model_validate(item) for item in catalog.regulations.values()]
