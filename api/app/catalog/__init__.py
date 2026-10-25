"""Access to the catalog copy synchronized from TerraPlan (read-only, never edited by hand).

`entities` holds the immutable values; `loader` reads and validates the JSON files. Both are
re-exported here so callers import from one place.
"""

from app.catalog.entities import Catalog, Limit, Parameter, Regulation, Unit
from app.catalog.loader import (
    ABSOLUTE_STATISTICS,
    CATALOG_FILES,
    CatalogLoadError,
    load_catalog,
)

__all__ = [
    "ABSOLUTE_STATISTICS",
    "CATALOG_FILES",
    "Catalog",
    "CatalogLoadError",
    "Limit",
    "Parameter",
    "Regulation",
    "Unit",
    "load_catalog",
]
