"""Catalog endpoints: public, read-only views of the synchronized catalog (ADR-005)."""

from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.core.dependencies import CatalogDep
from app.schemas.catalog import (
    CatalogMetaResponse,
    ParameterRead,
    RegulationRead,
    UnitRead,
)
from app.schemas.screening import CatalogLimitRead

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
    response_model=list[CatalogLimitRead],
    summary="List catalog limits",
    description=(
        "Every limit matching the filters, whatever its `status` or `statistic`: the catalog "
        "browser must show what exists, including limits still pending validation. The filter "
        "is `regulation` (query) and the field is `regulationCode` (response): same vocabulary "
        "as the synchronized catalog."
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
) -> list[CatalogLimitRead]:
    return [
        CatalogLimitRead.model_validate(limit)
        for limit in catalog.limits
        if (parameter_code is None or limit.parameter_code == parameter_code)
        and (regulation is None or limit.regulation_code == regulation)
    ]


@router.get(
    "/regulations",
    response_model=list[RegulationRead],
    summary="List regulations",
    description="Regulations the catalog quotes limits from, with the scope each one covers.",
    responses=_ERRORS,
)
async def list_regulations(catalog: CatalogDep) -> list[RegulationRead]:
    return [RegulationRead.model_validate(item) for item in catalog.regulations.values()]
