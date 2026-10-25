"""Errors raised by the pure SPC core.

The core never returns a half-answer: when the data cannot support a sound estimate it raises
and lets the service translate the exception into the API's `INSUFFICIENT_DATA` problem
(02 §8). Messages are written in Spanish because they end up in front of the analyst.
"""


class SPCError(Exception):
    """Base class for every failure of the statistical core."""


class InsufficientDataError(SPCError):
    """The series is too short (or too censored) for a defensible answer.

    Raised instead of returning limits or a capability index computed over ten points, because
    a plausible-looking number built on thin data is worse than no number at all.
    """
