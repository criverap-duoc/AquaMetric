"""Dependencies shared by routers: the loaded catalog and the injected clock."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.catalog import Catalog, load_catalog
from app.core.clock import ClockDep
from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_catalog() -> Catalog:
    """Parse the synchronized catalog once per process.

    Raises:
        CatalogLoadError: the catalog directory is missing or inconsistent. That is a
            deployment/configuration problem, not a client one, so it surfaces as 500 and
            never as problem+json for a 4xx.
    """
    return load_catalog(get_settings().catalog_dir)


CatalogDep = Annotated[Catalog, Depends(get_catalog)]

__all__ = ["CatalogDep", "ClockDep", "get_catalog"]
