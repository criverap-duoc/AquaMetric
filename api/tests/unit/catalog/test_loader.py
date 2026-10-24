"""Contract tests for the catalog loader, run against the real synchronized catalog.

Counts, codes and hashes are asserted against the TerraPlan v1.0.0 copy: if TerraPlan ships
a new catalog, these tests are updated together with `catalog/`. They are also the guard
against someone hand-editing the copy (see docs/adr/012-screening-single-observation.md).
"""

import json
import shutil
from hashlib import sha256
from pathlib import Path

import pytest

from app.catalog.loader import (
    ABSOLUTE_STATISTICS,
    CATALOG_FILES,
    Catalog,
    CatalogLoadError,
    load_catalog,
)

# tests/unit/catalog/test_loader.py -> repository root
CATALOG_DIR = Path(__file__).parents[4] / "catalog"

EXPECTED_PARAMETER_COUNT = 9
EXPECTED_UNIT_COUNT = 8
EXPECTED_LIMIT_COUNT = 60
EXPECTED_REGULATION_COUNT = 2
# Prefix of the sha256 of catalog.meta.json as published by TerraPlan; the hash inside the
# file is the logical-bundle hash and therefore different by design.
EXPECTED_META_FILE_HASH_PREFIX = "39ccf5"


@pytest.fixture(scope="session")
def catalog() -> Catalog:
    """Load the shared catalog once; it is immutable and read-only for the whole session."""
    return load_catalog(CATALOG_DIR)


def test_catalog_has_expected_entity_counts(catalog: Catalog) -> None:
    assert len(catalog.parameters) == EXPECTED_PARAMETER_COUNT
    assert len(catalog.units) == EXPECTED_UNIT_COUNT
    assert len(catalog.limits) == EXPECTED_LIMIT_COUNT
    assert len(catalog.regulations) == EXPECTED_REGULATION_COUNT


def test_catalog_version_and_meta_file_hash(catalog: Catalog) -> None:
    assert catalog.version == "1.0.0"

    meta_bytes = (CATALOG_DIR / "catalog.meta.json").read_bytes()
    file_hash = sha256(meta_bytes).hexdigest()
    assert file_hash.startswith(EXPECTED_META_FILE_HASH_PREFIX)

    # catalog.sha256 is the bundle hash declared by TerraPlan, never the file hash.
    declared_bundle_hash = json.loads(meta_bytes)["sha256"]
    assert catalog.sha256 == declared_bundle_hash
    assert catalog.sha256 != file_hash


def test_every_parameter_canonical_unit_exists(catalog: Catalog) -> None:
    for parameter in catalog.parameters.values():
        assert parameter.canonical_unit_code in catalog.units, parameter.code


def test_every_limit_parameter_exists(catalog: Catalog) -> None:
    for limit in catalog.limits:
        assert limit.parameter_code in catalog.parameters, limit.parameter_code


def test_every_limit_unit_exists(catalog: Catalog) -> None:
    for limit in catalog.limits:
        assert limit.unit_code in catalog.units, limit.unit_code


def test_all_limits_are_draft_verified(catalog: Catalog) -> None:
    """Hallazgo 1 del ADR-012: TerraPlan todavía no ha validado ningún límite.

    Mientras eso no cambie, el screening debe responder `not_evaluable`. Si este test empieza
    a fallar es que el catálogo avanzó y hay que revisar las expectativas del screening.
    """
    assert {limit.status for limit in catalog.limits} == {"draft-verified"}


def test_nch1333_absolute_limits_are_comparable_with_one_observation(catalog: Catalog) -> None:
    """NCh 1.333 es la única regulación cuyos límites admiten comparación puntual."""
    absolute_limits = {
        (limit.parameter_code, limit.context): (limit.statistic, limit.min, limit.max)
        for limit in catalog.limits
        if limit.regulation_code == "NCh1333" and limit.statistic in ABSOLUTE_STATISTICS
    }

    assert absolute_limits == {
        ("PH", "vida_acuatica"): ("max_absolute", 6.0, 9.0),
        ("PH", "riego"): ("max_absolute", 5.5, 9.0),
        ("DO", "vida_acuatica"): ("min_absolute", 5.0, None),
        ("COND", "riego"): ("max_absolute", None, 750.0),
    }


def test_load_catalog_rejects_version_mismatch(tmp_path: Path) -> None:
    for file_name in CATALOG_FILES:
        shutil.copyfile(CATALOG_DIR / file_name, tmp_path / file_name)

    meta_path = tmp_path / "catalog.meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["version"] = "9.9.9"
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    with pytest.raises(CatalogLoadError, match="9.9.9"):
        load_catalog(tmp_path)
