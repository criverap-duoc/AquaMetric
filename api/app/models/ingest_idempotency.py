"""Idempotency records for `POST /api/v1/ingest/observations` (ADR-009)."""

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import SCHEMA, Base


class IngestIdempotency(Base):
    """The stored response for an `Idempotency-Key`.

    Written in the same transaction as the rows it acknowledges: if the batch fails, the key
    is never registered, so TerraPlan's retry is replayed instead of rejected.
    """

    __tablename__ = "ingest_idempotency"
    __table_args__ = (
        CheckConstraint("status IN ('success', 'failure')", name="valid_status"),
        {"schema": SCHEMA},
    )

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # JSON is untyped by nature; its shape is the response schema, not a database concern.
    response: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
