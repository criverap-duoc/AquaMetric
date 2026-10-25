"""Samples: a physical container collected at a site and analysed by a laboratory."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import SCHEMA, Base


class Sample(Base):
    """A sample groups the observations the laboratory reports for one collection event.

    `status` follows TerraPlan's lifecycle; a sample may be republished with a newer status,
    which is why ingestion updates it instead of inserting a second row.
    """

    __tablename__ = "sample"
    __table_args__ = (
        CheckConstraint(
            "status IN ('collected', 'in_transit', 'received', 'analyzed', 'rejected')",
            name="valid_status",
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    # RESTRICT: deleting a site with samples is a data-integrity error, never a silent cascade.
    site_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.site.id", ondelete="RESTRICT"), nullable=False
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    matrix: Mapped[str] = mapped_column(String(20), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lab_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False)
