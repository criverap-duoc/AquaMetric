"""Public contract of `GET /api/v1/pipeline/status` (ADR-002, ADR-004).

The pipeline page must be able to say «Pipeline AWS no desplegado» without dressing it as a
failure: the demo feeds the API directly, so the object reports what the database knows (the
`ingest_idempotency` log and the last reading of each site) plus one flag that tells the UI
whether the S3 → Lambda path exists at all.
"""

from uuid import UUID

from pydantic import AwareDatetime, Field

from app.schemas.base import CamelModel


class BatchSummary(CamelModel):
    """One accepted ingest batch, read from `aquametric.ingest_idempotency` (ADR-009)."""

    key: str = Field(description="`Idempotency-Key` the sender used; the sha256 of the batch.")
    received_at: AwareDatetime = Field(description="Instante en que se registró el lote (UTC).")
    status: str = Field(description="`success`; una clave fallida nunca queda registrada.")
    accepted: int = Field(description="Filas escritas, según la respuesta guardada del lote.")
    duplicates: int = Field(description="Filas ya presentes por clave natural, no reescritas.")


class SiteLastRead(CamelModel):
    """Latest observation of one site, with the parameter it measured."""

    site_id: UUID
    site_code: str = Field(description="Código del sitio (p. ej. SIM-RIO-MAIPO-01).")
    parameter_code: str
    analyzed_at: AwareDatetime
    value: float | None = Field(description="Nulo si la última lectura fue censurada (< LOQ).")
    unit_code: str


class PipelineStatusResponse(CamelModel):
    """What the pipeline screen shows, without claiming a deployment that may not exist."""

    aws_deployed: bool = Field(
        description=(
            "`false` mientras la demo corra con ingesta directa. No es un error: la API funciona "
            "sin el pipeline (ADR-004)."
        )
    )
    recent_batches: list[BatchSummary] = Field(default_factory=list)
    last_observation_per_site: list[SiteLastRead] = Field(default_factory=list)
    limit: int = Field(description="Cuántos lotes recientes se devolvieron como máximo.")
