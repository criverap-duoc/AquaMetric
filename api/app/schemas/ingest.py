"""Contracts for `POST /api/v1/ingest/observations` (01 §5, ADR-009).

The batch is a single site, its samples and their observations. Everything that can be
decided without the database is decided here (shapes, limits, censored coherence); whether a
sample already exists is the service's job, so the schema never guesses about PostgreSQL.
"""

from typing import Annotated, Final, Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, Field, StringConstraints, model_validator

from app.schemas.base import CamelModel, StrictCamelModel

# Contract caps (01 §5): one batch is small enough to validate in memory before writing.
MAX_SAMPLES_PER_BATCH: Final = 500
MAX_OBSERVATIONS_PER_BATCH: Final = 5000

WaterBodyType = Literal["river", "lake", "estuary", "groundwater", "effluent", "drinking"]
SampleStatus = Literal["collected", "in_transit", "received", "analyzed", "rejected"]
Qualifier = Literal["<", ">"]
QcFlag = Literal["ok", "suspect", "failed"]
ObservationSource = Literal["lab", "field", "sensor"]

_SiteCode = Annotated[str, StringConstraints(min_length=1, max_length=64)]
_Text = Annotated[str, StringConstraints(min_length=1, max_length=255)]
_Matrix = Annotated[str, StringConstraints(min_length=1, max_length=20)]
_ParameterCode = Annotated[str, StringConstraints(min_length=1, max_length=32)]
_UnitCode = Annotated[str, StringConstraints(min_length=1, max_length=16)]
_CatalogVersion = Annotated[str, StringConstraints(min_length=1, max_length=32)]
_Method = Annotated[str, StringConstraints(min_length=1, max_length=255)]


class SiteIn(StrictCamelModel):
    """A site upserted by id; `code` is the identifier TerraPlan and the simulator exchange."""

    id: UUID
    code: _SiteCode
    name: _Text
    water_body_type: WaterBodyType
    latitude: float | None = None
    longitude: float | None = None
    is_active: bool = True


class SampleIn(StrictCamelModel):
    """A collected container; TerraPlan republishes it when the laboratory advances its state."""

    id: UUID
    site_id: UUID
    campaign_id: UUID | None = None
    matrix: _Matrix
    collected_at: AwareDatetime
    lab_received_at: AwareDatetime | None = None
    status: SampleStatus


class ObservationIn(StrictCamelModel):
    """One measured value, measured or censored.

    Censored (`< LOQ`) rows carry no value: `value = null`, `qualifier = "<"` and `loq`, which
    is what the database stores (ADR-003). `sampleId` is null for a sensor reading.
    """

    id: UUID
    site_id: UUID
    sample_id: UUID | None = None
    parameter_code: _ParameterCode
    value: float | None = None
    unit_code: _UnitCode
    qualifier: Qualifier | None = None
    loq: float | None = None
    method: _Method | None = None
    analyzed_at: AwareDatetime
    qc_flag: QcFlag = "ok"
    source: ObservationSource

    @model_validator(mode="after")
    def _check_censored_coherence(self) -> Self:
        """`value`, `qualifier` and `loq` must describe the same thing.

        A `model_validator` (not a `field_validator`) because the rule needs all three fields
        at once, whatever order they arrive in.
        """
        if self.value is None:
            if self.qualifier != "<" or self.loq is None:
                raise ValueError(
                    "Una observación sin valor debe traer qualifier '<' y un loq informado."
                )
        elif self.qualifier is not None or self.loq is not None:
            raise ValueError(
                "Una observación con valor no puede traer qualifier ni loq; "
                "para un valor censurado envía value null."
            )
        return self


class IngestRequest(StrictCamelModel):
    """An atomic batch: all of it is stored or none of it is (ADR-009)."""

    catalog_version: _CatalogVersion
    site: SiteIn
    samples: list[SampleIn] = Field(default_factory=list, max_length=MAX_SAMPLES_PER_BATCH)
    observations: list[ObservationIn] = Field(min_length=1, max_length=MAX_OBSERVATIONS_PER_BATCH)

    @model_validator(mode="after")
    def _check_batch_coherence(self) -> Self:
        """Reject what the batch alone can disprove.

        Existence of a sample in PostgreSQL cannot be checked here, so the service resolves it
        before writing; what a single site batch can check is that everything points at *this*
        site and that an observation does not cite a batch sample from another site.
        """
        for index, sample in enumerate(self.samples):
            if sample.site_id != self.site.id:
                raise ValueError(
                    f"samples[{index}]: siteId no corresponde al sitio del lote ({self.site.id})."
                )
        batch_sites = {sample.id: sample.site_id for sample in self.samples}
        for index, observation in enumerate(self.observations):
            if observation.site_id != self.site.id:
                raise ValueError(
                    f"observations[{index}]: siteId no corresponde al sitio del lote "
                    f"({self.site.id})."
                )
            sample_site = batch_sites.get(observation.sample_id) if observation.sample_id else None
            if sample_site is not None and sample_site != observation.site_id:
                raise ValueError(
                    f"observations[{index}]: la muestra {observation.sample_id} pertenece a "
                    "otro sitio."
                )
        return self


class IngestResponse(CamelModel):
    """`accepted` rows written, `duplicates` already present per the natural key (ADR-009)."""

    accepted: int
    duplicates: int
