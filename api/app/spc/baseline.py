"""Phase I baseline selection and the censored-data policy (ADR-003).

Pure module (02 §7): no database, no clock. The service passes the observations it read and gets
back the numbers a chart can consume plus the metadata that makes the estimate auditable.

Censored values (`value = null`, `qualifier = "<"`, `loq`) enter the calculation as `LOQ / 2`
and **only** there: the substitution is never stored, so the database keeps the truth («no
cuantificado, por debajo de este LOQ») and the report says how it was handled. A series with
more than 20 % censored values cannot support reliable limits and is refused (ADR-003).
"""

from collections.abc import Sequence

from app.spc.constants import DEFAULT_CENSORED_MAX_FRACTION, MIN_BASELINE_POINTS
from app.spc.errors import InsufficientDataError

CENSORED_QUALIFIER = "<"
QC_FLAG_OK = "ok"
IMR_METHOD = "imr"


def apply_censored_policy(
    values: Sequence[float | None],
    loqs: Sequence[float | None],
    qualifiers: Sequence[str | None],
    max_fraction: float,
) -> tuple[list[float], dict[str, int | float]]:
    """Replace censored observations with LOQ/2 for the calculation, or refuse the series.

    Args:
        values: measured values; `None` on censored rows.
        loqs: limit of quantification of each row; required on censored rows.
        qualifiers: `"<"` on censored rows, `None` otherwise.
        max_fraction: largest acceptable share of censored values, e.g. `0.2` for 20 %.

    Returns:
        The series ready for a chart (censored rows replaced by `LOQ / 2`) and the metadata
        that documents the substitution: `n`, `censored_count`, `censored_fraction`.

    Raises:
        InsufficientDataError: no values at all, or more than `max_fraction` censored.
        ValueError: sequences of different lengths, a censored row without LOQ, or a row with
            neither value nor the `"<"` qualifier.
    """
    if len(values) != len(loqs) or len(values) != len(qualifiers):
        raise ValueError(
            "Las secuencias de valores, LOQ y qualifiers deben tener el mismo largo "
            f"({len(values)}, {len(loqs)} y {len(qualifiers)})."
        )
    if not values:
        raise InsufficientDataError("No hay observaciones para la línea base (0 valores).")

    censored = [
        index
        for index, (value, qualifier) in enumerate(zip(values, qualifiers, strict=True))
        if value is None and qualifier == CENSORED_QUALIFIER
    ]
    censored_fraction = len(censored) / len(values)
    if censored_fraction > max_fraction:
        raise InsufficientDataError(
            f"{censored_fraction:.0%} de los datos están censurados (el máximo aceptable es "
            f"{max_fraction:.0%}). No es posible estimar límites de control fiables."
        )

    censored_set = set(censored)
    substituted: list[float] = []
    for index, value in enumerate(values):
        if index in censored_set:
            loq = loqs[index]
            if loq is None:
                raise ValueError(
                    f"La observación censurada {index + 1} no tiene LOQ; no se puede sustituir "
                    "por LOQ/2."
                )
            substituted.append(loq / 2)
        elif value is None:
            raise ValueError(
                f"La observación {index + 1} no tiene valor ni qualifier '<'; no es una "
                "observación válida para la línea base."
            )
        else:
            substituted.append(value)

    metadata: dict[str, int | float] = {
        "n": len(values),
        "censored_count": len(censored),
        "censored_fraction": censored_fraction,
    }
    return substituted, metadata


def select_baseline(
    observations: Sequence[tuple[float | None, float | None, str | None, str]],
    min_points: int = MIN_BASELINE_POINTS,
    censored_max_fraction: float = DEFAULT_CENSORED_MAX_FRACTION,
) -> tuple[list[float], dict[str, int | float | str]]:
    """Take the Phase I baseline of one (site, parameter) series.

    Each row is `(value, loq, qualifier, qc_flag)` — value and qualifier as stored by the ingest
    contract (`01 §5`), the LOQ the censored policy needs, and the quality flag. Rows whose
    `qc_flag` is not `"ok"` are excluded: a suspect or failed datum never anchors the limits.

    The order of the checks matters for what the analyst reads: the count first («faltan
    datos»), then the censoring share («hay demasiados datos censurados»). Doing it the other
    way round would report 30 % censored on a series of three values, which answers a question
    nobody asked.

    Args:
        observations: rows in chronological order.
        min_points: minimum number of valid observations, 20 by default (`01 §4.1`).
        censored_max_fraction: largest acceptable share of censored values, 20 % by default.

    Returns:
        The series for the chart (censored rows as `LOQ / 2`) and its metadata: `n`,
        `censored_count`, `censored_fraction`, `method` and `min_points`.

    Raises:
        InsufficientDataError: fewer than `min_points` usable rows, or too many censored values.
        ValueError: a censored row without LOQ, or a row with neither value nor `"<"`.
    """
    usable: list[tuple[float | None, float | None, str | None]] = [
        (value, loq, qualifier)
        for value, loq, qualifier, qc_flag in observations
        if qc_flag == QC_FLAG_OK
    ]
    if len(usable) < min_points:
        raise InsufficientDataError(
            f"Se requieren al menos {min_points} observaciones válidas para la línea base "
            f"(hay {len(usable)})."
        )

    values = [value for value, _, _ in usable]
    loqs = [loq for _, loq, _ in usable]
    qualifiers = [qualifier for _, _, qualifier in usable]
    substituted, metadata = apply_censored_policy(
        values, loqs, qualifiers, max_fraction=censored_max_fraction
    )
    enriched: dict[str, int | float | str] = {
        **metadata,
        "method": IMR_METHOD,
        "min_points": min_points,
    }
    return substituted, enriched
