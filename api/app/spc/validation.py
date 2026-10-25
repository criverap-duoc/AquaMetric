"""Input guards shared by the SPC modules.

Kept apart so every entry point rejects the same inputs with the same Spanish message instead
of each module inventing its own check (and so a `None` never slips into a mean).
"""

from collections.abc import Sequence
from math import isfinite


def require_finite(values: Sequence[float], *, what: str = "las observaciones") -> list[float]:
    """Return the values as plain floats, rejecting NaN and infinity.

    NaN does not fail loudly in a sum: it silently poisons the center line, the sigma estimate
    and every rule, so the core refuses the series instead of returning poisoned limits
    (02 §7). Missing values must be handled before arriving here.

    Args:
        values: numbers to validate.
        what: Spanish noun phrase used in the error message.

    Returns:
        A new `list[float]`, safe to index and to sum.
    """
    cleaned: list[float] = []
    for position, value in enumerate(values, start=1):
        number = float(value)
        if not isfinite(number):
            raise ValueError(
                f"{what.capitalize()} contienen NaN o infinito (posición {position}); "
                "limpiar antes de calcular."
            )
        cleaned.append(number)
    return cleaned
