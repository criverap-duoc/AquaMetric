"""Pure statistical process control core (ADR-001).

No I/O, no clock, no database, no network (02 §7): sequences in, frozen dataclasses out. The
services decide *where* the numbers come from and *who* may see them; this package decides only
what the numbers mean.
"""

from app.spc.baseline import apply_censored_policy, select_baseline
from app.spc.capability import compute_capability
from app.spc.charts import compute_imr, compute_xbar_r
from app.spc.errors import InsufficientDataError, SPCError
from app.spc.rules import detect_rules
from app.spc.types import (
    CapabilityResult,
    ControlLimits,
    IMRResult,
    RuleViolation,
    XbarRResult,
)

__all__ = [
    "CapabilityResult",
    "ControlLimits",
    "IMRResult",
    "InsufficientDataError",
    "RuleViolation",
    "SPCError",
    "XbarRResult",
    "apply_censored_policy",
    "compute_capability",
    "compute_imr",
    "compute_xbar_r",
    "detect_rules",
    "select_baseline",
]
