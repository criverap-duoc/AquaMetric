#!/usr/bin/env python3
"""Synchronize the read-only catalog copy from TerraPlan.

TerraPlan owns `catalog/`; this repository keeps a byte-for-byte copy so both projects read
the same parameters, units and limits. The script is idempotent: a file is copied only when
its sha256 differs from the source, which makes it safe to run in CI and before tests.

Usage (from any directory):
    python scripts/sync_catalog.py
    python scripts/sync_catalog.py --from-path ../terraplan-node/catalog --to-path catalog

Exit code 1 means something must be fixed by hand: a missing file, a version mismatch
between the `.v1.json` files and `catalog.meta.json`, or an unreadable meta file.
"""

import argparse
import json
import re
import shutil
import sys
from hashlib import sha256
from pathlib import Path
from typing import Final

# scripts/sync_catalog.py -> repository root
REPO_ROOT: Final = Path(__file__).resolve().parents[1]
# Defaults are anchored to the repository, so the script behaves the same from any cwd.
DEFAULT_SOURCE: Final = REPO_ROOT.parent / "terraplan-node" / "catalog"
DEFAULT_TARGET: Final = REPO_ROOT / "catalog"

META_FILE: Final = "catalog.meta.json"
VERSIONED_FILES: Final = (
    "parameters.v1.json",
    "units.v1.json",
    "limits.v1.json",
    "regulations.v1.json",
)
# Must mirror app/catalog/loader.py: the loader fails at startup when a file is missing.
CATALOG_FILES: Final = (META_FILE, *VERSIONED_FILES)

SHA256_HEX: Final = re.compile(r"^[0-9a-f]{64}$")
CHUNK_SIZE: Final = 65536


class SyncError(Exception):
    """Unrecoverable problem in the source catalog; reported to the operator."""


def file_sha256(path: Path) -> str | None:
    """Return the sha256 of a file, or None when it does not exist yet (first sync)."""
    if not path.is_file():
        return None
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, object]:
    """Parse one catalog file, naming the file in every error message."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SyncError(f"{path.name}: JSON inválido ({exc.msg}, línea {exc.lineno})") from exc
    if not isinstance(payload, dict):
        raise SyncError(f"{path.name}: se esperaba un objeto JSON en la raíz")
    return payload


def read_version(payload: dict[str, object], *, path: Path) -> str:
    """Return the `version` of a catalog document."""
    value = payload.get("version")
    if not isinstance(value, str) or not value:
        raise SyncError(f"{path.name}: campo 'version' ausente o vacío")
    return value


def read_declared_bundle_sha256(payload: dict[str, object], *, path: Path) -> str:
    """Validate the logical bundle hash TerraPlan publishes inside catalog.meta.json.

    It is NOT the hash of the file itself: a file cannot contain its own hash, so TerraPlan
    hashes a logical bundle of the five JSON documents. This script only checks that the
    field is a well-formed sha256 and reports it; comparing it with the file hash would be
    meaningless and has already caused confusion (see docs/adr/012-*).
    """
    value = payload.get("sha256")
    if not isinstance(value, str) or not SHA256_HEX.match(value):
        raise SyncError(f"{path.name}: campo 'sha256' ausente o no es un sha256 hexadecimal")
    return value


def check_versions(source: Path, expected: str) -> None:
    """TerraPlan must publish the same version in every file; the loader rejects otherwise."""
    for name in VERSIONED_FILES:
        path = source / name
        found = read_version(read_json(path), path=path)
        if found != expected:
            raise SyncError(
                f"{name}: version '{found}' no coincide con '{expected}' de {META_FILE}"
            )


def print_table(rows: list[tuple[str, str, str, str, str]]) -> None:
    """Print the sync report: file, size and both hashes, so a reviewer can diff runs."""
    headers = ("archivo", "bytes", "sha256_local", "sha256_remoto", "acción")
    table = [headers, *rows]
    widths = [max(len(row[column]) for row in table) for column in range(len(headers))]
    for index, row in enumerate(table):
        line = "  ".join(cell.ljust(widths[column]) for column, cell in enumerate(row))
        print(line.rstrip())
        if index == 0:
            print("  ".join("-" * width for width in widths))


def sync(source: Path, target: Path) -> int:
    """Copy every catalog file whose sha256 differs from the source; return the exit code."""
    missing = [name for name in CATALOG_FILES if not (source / name).is_file()]
    if missing:
        raise SyncError(
            f"{source}: faltan archivos del catálogo ({', '.join(missing)}). "
            "Revisa --from-path y sincroniza el repo de TerraPlan."
        )

    meta_path = source / META_FILE
    meta = read_json(meta_path)
    version = read_version(meta, path=meta_path)
    bundle_sha256 = read_declared_bundle_sha256(meta, path=meta_path)
    check_versions(source, version)

    local_meta_path = target / META_FILE
    previous_bundle_sha256: str | None = None
    if local_meta_path.is_file():
        try:
            previous_meta = read_json(local_meta_path)
            previous_bundle_sha256 = read_declared_bundle_sha256(previous_meta, path=local_meta_path)
        except SyncError:
            # A hand-edited local copy is not fatal: the sync below overwrites it.
            previous_bundle_sha256 = None

    target.mkdir(parents=True, exist_ok=True)

    rows: list[tuple[str, str, str, str, str]] = []
    for name in CATALOG_FILES:
        remote_hash = file_sha256(source / name)
        local_hash = file_sha256(target / name)
        action = "omitido"
        if local_hash != remote_hash:
            shutil.copyfile(source / name, target / name)
            local_hash = file_sha256(target / name)
            action = "copiado"
        if local_hash != remote_hash:
            raise SyncError(f"{name}: la copia no coincide con el origen después de copiar")
        size = (target / name).stat().st_size
        rows.append((name, str(size), local_hash or "", remote_hash or "", action))

    print_table(rows)
    copied = sum(1 for row in rows if row[4] == "copiado")
    print()
    print(f"catálogo v{version} · bundle lógico sha256 {bundle_sha256}")
    if previous_bundle_sha256 is not None and previous_bundle_sha256 != bundle_sha256:
        print(f"bundle anterior {previous_bundle_sha256} -> nuevo {bundle_sha256}")
    print(f"{copied} copiado(s), {len(rows) - copied} omitido(s)")
    print(
        "nota: la columna sha256_* es el hash del archivo; el campo 'sha256' de "
        f"{META_FILE} identifica el bundle lógico y no se autoverifica."
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    """CLI definition; defaults are anchored to the repository, not to the current directory."""
    parser = argparse.ArgumentParser(
        description="Sincroniza la copia de solo lectura del catálogo compartido de TerraPlan."
    )
    parser.add_argument(
        "--from-path",
        type=Path,
        default=DEFAULT_SOURCE,
        help="Carpeta del catálogo en TerraPlan (por defecto ../terraplan-node/catalog "
        "respecto de la raíz del repo).",
    )
    parser.add_argument(
        "--to-path",
        type=Path,
        default=DEFAULT_TARGET,
        help="Carpeta de destino en este repo (por defecto ../catalog respecto de api/, "
        "o sea <repo>/catalog).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point: report the table and return 0 when the copy matches the source."""
    args = build_parser().parse_args(argv)
    try:
        return sync(args.from_path, args.to_path)
    except SyncError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"ERROR: no se pudo sincronizar el catálogo: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
