"""Observations: the measured values AquaMetric screens and analyses."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import SCHEMA, Base


class Observation(Base):
    """One measured value, from a laboratory or a sensor.

    `sample_id` is null for sensor readings at a known site. The natural key
    (`site_id`, `parameter_code`, `analyzed_at`, `sample_id`, `source`) is what makes
    ingestion idempotent: a retried batch collides and is skipped (ADR-009).

    Censored values (`< LOQ`) are stored as `value = NULL` + `qualifier = '<'` + `loq`,
    never as 0 nor as LOQ/2, because the substitution is a calculation choice, not data.
    """

    __tablename__ = "observation"
    __table_args__ = (
        CheckConstraint("qualifier IN ('<', '>')", name="valid_qualifier"),
        CheckConstraint(
            "qc_flag IN ('ok', 'suspect', 'failed')",
            name="valid_qc_flag",
        ),
        CheckConstraint("source IN ('lab', 'field', 'sensor')", name="valid_source"),
        CheckConstraint(
            "(value IS NULL AND qualifier = '<' AND loq IS NOT NULL) "
            "OR (value IS NOT NULL AND qualifier IS NULL)",
            name="censored_coherence",
        ),
        # Short explicit name: the convention-generated one would exceed PostgreSQL's 63 bytes.
        UniqueConstraint(
            "site_id",
            "parameter_code",
            "analyzed_at",
            "sample_id",
            "source",
            name="uq_obs_natural_key",
        ),
        Index("ix_obs_site_param_time", "site_id", "parameter_code", "analyzed_at"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    # RESTRICT: observations are the evidence; a site with data cannot be deleted.
    site_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.site.id", ondelete="RESTRICT"), nullable=False
    )
    # SET NULL: removing a sample must not erase the sensor-like measurements already reported.
    sample_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.sample.id", ondelete="SET NULL")
    )
    parameter_code: Mapped[str] = mapped_column(String(32), nullable=False)
    value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    unit_code: Mapped[str] = mapped_column(String(16), nullable=False)
    qualifier: Mapped[str | None] = mapped_column(String(1))
    loq: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    method: Mapped[str | None] = mapped_column(String(255))
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    qc_flag: Mapped[str] = mapped_column(String(10), nullable=False, server_default=text("'ok'"))
    source: Mapped[str] = mapped_column(String(10), nullable=False)
