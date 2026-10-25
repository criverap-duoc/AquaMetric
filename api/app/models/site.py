"""Sampling sites: the entity every sample and observation belongs to."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, Numeric, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import SCHEMA, Base


class Site(Base):
    """A water body location.

    `code` is the stable identifier TerraPlan and the simulator exchange (`RIO-MAIPO-01`,
    `SIM-RIO-MAIPO-01`); the uuid is internal.
    """

    __tablename__ = "site"
    __table_args__ = (
        CheckConstraint(
            "water_body_type IN "
            "('river', 'lake', 'estuary', 'groundwater', 'effluent', 'drinking')",
            name="valid_water_body_type",
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    water_body_type: Mapped[str] = mapped_column(String(20), nullable=False)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
