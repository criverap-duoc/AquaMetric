"""Sites endpoint: the public list the selectors of Series and Control use (02 §5)."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.core.db import SessionDep
from app.repositories.site_repository import SiteRepository
from app.schemas.site import SiteListMeta, SiteListResponse, SiteRead

router = APIRouter(prefix="/sites", tags=["sites"])


@router.get(
    "",
    response_model=SiteListResponse,
    summary="List sampling sites",
    description=(
        "Paginated list of the sites stored in `aquametric.site`, ordered by `code`. The uuid is "
        "the one `GET /spc/control-charts` expects as `siteId`, so the selectors no longer have "
        "to guess it. Inactive sites are listed as well: they still own historical data."
    ),
    responses={500: {"description": "Unhandled error, returned as application/problem+json"}},
)
async def list_sites(
    session: SessionDep,
    page: Annotated[int, Query(ge=1, description="Página, desde 1.")] = 1,
    page_size: Annotated[
        int, Query(alias="pageSize", ge=1, le=100, description="Sitios por página (1–100).")
    ] = 50,
    is_active: Annotated[
        bool | None,
        Query(alias="isActive", description="Filtra por sitio activo; omitido devuelve todos."),
    ] = None,
) -> SiteListResponse:
    """Public read: the site catalog is not sensitive and the UI is read-only."""
    sites, total = await SiteRepository(session).list_paginated(page, page_size, is_active)
    return SiteListResponse(
        data=[SiteRead.model_validate(site) for site in sites],
        meta=SiteListMeta(page=page, page_size=page_size, total=total),
    )
