"""Phase I control limits per (site, parameter); filled in phase D (SPC).

The table exists from the first migration so the schema is stable, but nothing computes or
reads it yet: `app/spc/` arrives in phase D with golden tests.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import SCHEMA, Base


class SpcBaseline(Base):
    """Frozen control limits estimated from a Phase I window.

    The data range and catalog version are stored with the limits so a chart recomputed
    months later can be explained: same inputs, same limits.
    """

    __tablename__ = "spc_baseline"
    __table_args__ = (
        CheckConstraint("phase IN ('phase_i', 'phase_ii')", name="valid_phase"),
        CheckConstraint("method IN ('imr', 'xbar_r')", name="valid_method"),
        UniqueConstraint("site_id", "parameter_code", "phase", name="uq_baseline_site_param_phase"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.site.id", ondelete="RESTRICT"), nullable=False
    )
    parameter_code: Mapped[str] = mapped_column(String(32), nullable=False)
    phase: Mapped[str] = mapped_column(String(10), nullable=False)
    method: Mapped[str] = mapped_column(String(20), nullable=False)
    n_points: Mapped[int] = mapped_column(Integer, nullable=False)
    data_range_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data_range_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    center_line: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    ucl: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    lcl: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    catalog_version: Mapped[str] = mapped_column(String(20), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
