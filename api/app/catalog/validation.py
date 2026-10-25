"""Strict field readers for the catalog documents.

The catalog JSON is an untyped boundary: every field the loader consumes goes through one of
these helpers, so a wrong type fails at startup with a Spanish message instead of reaching
screening as `None`. `CatalogLoadError` lives here because these readers are its raisers.

Deliberately **not** a `DomainError`: this surfaces while loading configuration, never inside
an HTTP request, so no problem+json handler should translate it.
"""

from collections.abc import Mapping
from pathlib import Path
from typing import Any


class CatalogLoadError(Exception):
    """The synchronized catalog is missing, unreadable or internally inconsistent."""


def require_str(raw: Mapping[str, Any], field: str, *, path: Path) -> str:
    """A non-empty string field."""
    value = raw.get(field)
    if not isinstance(value, str) or not value:
        raise CatalogLoadError(f"{path.name}: campo '{field}' ausente o no es texto")
    return value


def optional_str(raw: Mapping[str, Any], field: str, *, path: Path) -> str | None:
    """A string field that may be absent or null."""
    value = raw.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        raise CatalogLoadError(f"{path.name}: campo '{field}' no es texto")
    return value


def require_int(raw: Mapping[str, Any], field: str, *, path: Path) -> int:
    """An integer field; `bool` is rejected because it is an `int` subclass in Python."""
    value = raw.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        raise CatalogLoadError(f"{path.name}: campo '{field}' ausente o no es entero")
    return value


def require_bool(raw: Mapping[str, Any], field: str, *, path: Path) -> bool:
    """A boolean field."""
    value = raw.get(field)
    if not isinstance(value, bool):
        raise CatalogLoadError(f"{path.name}: campo '{field}' ausente o no es booleano")
    return value


def optional_float(raw: Mapping[str, Any], field: str, *, path: Path) -> float | None:
    """A numeric field that may be absent or null, normalised to `float`."""
    value = raw.get(field)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise CatalogLoadError(f"{path.name}: campo '{field}' no es numérico")
    return float(value)
