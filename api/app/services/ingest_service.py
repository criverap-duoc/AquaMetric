"""Ingestion: one atomic, idempotent write path for every observation (ADR-009).

TerraPlan, the simulator and the AWS processor all go through here. Validating the whole batch
before writing anything is what makes a 4xx meaningful: nothing is stored, so the sender can fix
the payload and retry with the same `Idempotency-Key`.
"""

import hashlib
import logging
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog import Catalog
from app.core.clock import Clock
from app.core.errors import (
    CatalogVersionMismatchError,
    IdempotencyKeyReuseError,
    UnitMismatchError,
    UnknownParameterError,
    ValidationFailedError,
)
from app.models import Observation
from app.repositories.ingest_idempotency_repository import IngestIdempotencyRepository
from app.repositories.observation_repository import ObservationRepository
from app.repositories.sample_repository import SampleRepository
from app.repositories.site_repository import SiteRepository
from app.schemas.ingest import IngestRequest, IngestResponse

logger = logging.getLogger(__name__)


class IngestService:
    """Validate the batch, then write it in a single transaction.

    Both idempotency levels live here: the `Idempotency-Key` replay answers first, and the
    natural key turns a re-sent batch into `duplicates` instead of new rows.
    """

    def __init__(self, session: AsyncSession, catalog: Catalog, clock: Clock) -> None:
        self._session = session
        self._catalog = catalog
        self._clock = clock
        self._sites = SiteRepository(session)
        self._samples = SampleRepository(session)
        self._observations = ObservationRepository(session)
        self._idempotency = IngestIdempotencyRepository(session)

    async def ingest(
        self, payload: IngestRequest, idempotency_key: str, raw_body: bytes
    ) -> IngestResponse:
        """Store the batch, or fail having written nothing.

        The replay lookup, the catalog checks and the writes share **one** transaction: two
        transactions on the same session are impossible (SQLAlchemy autobegins on the first
        read) and, more importantly, the key must never be registered without its rows.

        Raises:
            IdempotencyKeyReuseError: same key, different body.
            CatalogVersionMismatchError: the payload was built against another catalog major.
            UnknownParameterError, UnitMismatchError, ValidationFailedError: the batch is
                rejected as a whole, before any write.
            ConflictError: a site `code` is owned by another site id.
        """
        payload_hash = hashlib.sha256(raw_body).hexdigest()
        try:
            async with self._session.begin():
                replayed = await self._replay(idempotency_key, payload_hash)
                if replayed is not None:
                    return replayed
                self._check_catalog_version(payload)
                await self._validate_references(payload)
                return await self._write(payload, idempotency_key, payload_hash)
        except IntegrityError as exc:
            # The context manager already rolled back, so nothing was stored.
            logger.warning("ingest integrity error", extra={"idempotencyKey": idempotency_key})
            raise ValidationFailedError(
                "No se pudo guardar el lote: los datos no cumplen las restricciones de la base "
                "(revisa los ids y sus referencias)."
            ) from exc

    async def _replay(self, key: str, payload_hash: str) -> IngestResponse | None:
        """Return the stored answer for a replay; a different body on the same key is a 409."""
        existing = await self._idempotency.get_by_key(key)
        if existing is None:
            return None
        if existing.payload_hash != payload_hash:
            raise IdempotencyKeyReuseError(
                "La Idempotency-Key ya fue usada con un payload distinto."
            )
        logger.info("ingest replay", extra={"idempotencyKey": key})
        return IngestResponse.model_validate(existing.response)

    def _check_catalog_version(self, payload: IngestRequest) -> None:
        """A different major may rename or drop codes, so it is refused instead of guessed."""
        if payload.catalog_version.split(".")[0] != self._catalog.version.split(".")[0]:
            raise CatalogVersionMismatchError(
                f"El catálogo local es v{self._catalog.version} y el lote declara "
                f"v{payload.catalog_version}."
            )

    async def _validate_references(self, payload: IngestRequest) -> None:
        """Reject the whole batch before writing: catalog codes, units and sample references."""
        for index, observation in enumerate(payload.observations):
            parameter = self._catalog.parameters.get(observation.parameter_code)
            if parameter is None:
                raise UnknownParameterError(
                    f"observations[{index}]: el parámetro '{observation.parameter_code}' no "
                    "existe en el catálogo."
                )
            unit = self._catalog.units.get(observation.unit_code)
            if unit is None:
                raise UnitMismatchError(
                    f"observations[{index}]: la unidad '{observation.unit_code}' no existe en "
                    "el catálogo."
                )
            canonical_unit = self._catalog.units[parameter.canonical_unit_code]
            if unit.dimension != canonical_unit.dimension:
                raise UnitMismatchError(
                    f"observations[{index}]: la unidad '{unit.code}' mide {unit.dimension}, "
                    f"pero '{parameter.code}' se mide en {canonical_unit.dimension}."
                )
        await self._validate_sample_ids(payload)

    async def _validate_sample_ids(self, payload: IngestRequest) -> None:
        """An observation may cite a sample from the batch or one TerraPlan already published."""
        batch_ids = {sample.id for sample in payload.samples}
        external: dict[int, UUID] = {}
        for index, observation in enumerate(payload.observations):
            sample_id = observation.sample_id
            if sample_id is not None and sample_id not in batch_ids:
                external[index] = sample_id
        if not external:
            return
        stored = await self._samples.existing_ids(list(external.values()))
        for index, sample_id in external.items():
            if sample_id not in stored:
                raise ValidationFailedError(
                    f"observations[{index}]: la muestra {sample_id} no viene en el lote ni "
                    "existe en la base."
                )

    async def _write(
        self, payload: IngestRequest, idempotency_key: str, payload_hash: str
    ) -> IngestResponse:
        """Write site, samples, observations and the idempotency record in the open transaction."""
        await self._sites.upsert_by_id(payload.site)
        for sample in payload.samples:
            await self._samples.upsert_by_id(sample)
        rows = [Observation(**observation.model_dump()) for observation in payload.observations]
        accepted = await self._observations.bulk_insert_ignore_conflicts(rows)
        response = IngestResponse(accepted=accepted, duplicates=len(rows) - accepted)
        await self._idempotency.save(
            key=idempotency_key,
            payload_hash=payload_hash,
            response=response.model_dump(),
            status="success",
            received_at=self._clock.now(),
        )
        logger.info(
            "ingest stored",
            extra={
                "idempotencyKey": idempotency_key,
                "accepted": response.accepted,
                "duplicates": response.duplicates,
            },
        )
        return response
