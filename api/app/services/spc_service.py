"""Orchestration of the SPC endpoints: which rows are Phase I, which are Phase II, and how a
refusal of the pure core becomes a 422 (ADR-001, ADR-003).

No formula lives here. `app.spc/` decides what the numbers mean; this service decides where the
numbers come from and what the analyst is told alongside them: control limits are not normative
limits, and a point beyond UCL is a change in the process, not a breach of a standard (ADR-010).
"""

import logging
from decimal import Decimal
from typing import Final
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog import Catalog
from app.core.clock import Clock
from app.core.errors import (
    InsufficientDataError,
    NotFoundError,
    UnknownParameterError,
    ValidationFailedError,
)
from app.models import Observation, SpcBaseline
from app.repositories.spc_baseline_repository import PHASE_I, SpcBaselineRepository
from app.schemas.spc import (
    BaselineRead,
    BaselineUpsertRequest,
    ControlChartResponse,
    ControlLimitsRead,
    RuleViolationRead,
    SpecLimitsRead,
)
from app.spc import (
    ControlLimits,
    IMRResult,
    RuleViolation,
    compute_imr,
    detect_rules,
    select_baseline,
)
from app.spc import InsufficientDataError as SpcInsufficientDataError
from app.spc.constants import DEFAULT_CENSORED_MAX_FRACTION, MIN_BASELINE_POINTS

logger = logging.getLogger(__name__)

IMR_METHOD: Final = "imr"
DEFAULT_MONITORING_POINTS: Final = 100
VALIDATED_STATUS: Final = "validated"

# A chart can show a single band, so the first regulation with a signed limit wins; the order is
# the same one the screening defaults to (ADR-012).
SPEC_REGULATION_PREFERENCE: Final = ("NCh1333", "DS53-2014-MMA")

# The sentence the UI must never be able to drop (ADR-010).
SCREENING_WARNING: Final = "Screening referencial, no dictamen de cumplimiento legal."
CONTROL_LIMITS_WARNING: Final = (
    "Límites de control calculados con la fase I. Un punto fuera de control indica un cambio en "
    "el proceso, no necesariamente un incumplimiento normativo."
)
ON_THE_FLY_WARNING: Final = (
    "Baseline no persistida; límites computados al vuelo a partir de las observaciones más "
    "antiguas de la serie."
)


class SpcService:
    """Compute a control chart, or freeze its limits, for one (site, parameter) series."""

    def __init__(
        self,
        session: AsyncSession,
        catalog: Catalog,
        clock: Clock,
        *,
        censored_max_fraction: float = DEFAULT_CENSORED_MAX_FRACTION,
        baseline_min_points: int = MIN_BASELINE_POINTS,
    ) -> None:
        self._session = session
        self._catalog = catalog
        self._clock = clock
        self._censored_max_fraction = censored_max_fraction
        self._baseline_min_points = baseline_min_points
        self._baselines = SpcBaselineRepository(session)

    async def compute_chart(
        self,
        site_id: UUID,
        parameter_code: str,
        *,
        baseline_points: int = MIN_BASELINE_POINTS,
        monitoring_points: int = DEFAULT_MONITORING_POINTS,
    ) -> ControlChartResponse:
        """Estimate the I-MR limits from the oldest rows and scan the newer ones for signals.

        The chart is never persisted here: a GET must not write, so a missing baseline is
        answered with limits computed on the fly plus `baselinePersisted = false`.

        Raises:
            UnknownParameterError: `parameterCode` is not in the catalog.
            InsufficientDataError: fewer points than the baseline needs, too many censored
                values, or a series with no variation to estimate sigma from.
        """
        self._require_parameter(parameter_code)
        baseline_rows = await self._baselines.get_observations(
            site_id, parameter_code, limit=baseline_points
        )
        values, metadata = self._baseline_series(baseline_rows, baseline_points, parameter_code)
        imr = self._imr(values)

        persisted = await self._baselines.get_baseline(site_id, parameter_code, PHASE_I)
        monitoring_rows = await self._baselines.get_observations(
            site_id,
            parameter_code,
            after=baseline_rows[-1].analyzed_at,
            limit=monitoring_points,
        )
        monitoring_values, censored_count = _monitoring_series(monitoring_rows)
        violations = detect_rules(monitoring_values, imr.individuals) if monitoring_values else []

        warnings = [CONTROL_LIMITS_WARNING, SCREENING_WARNING]
        if censored_count:
            warnings.append(
                f"{censored_count} observaciones censuradas (< LOQ) quedaron fuera del monitoreo."
            )
        if persisted is None:
            warnings.append(ON_THE_FLY_WARNING)

        return ControlChartResponse(
            individuals=_limits_read(imr.individuals),
            moving_range=_limits_read(imr.moving_range),
            spec_limits=self._spec_limits(parameter_code),
            violations=[_violation_read(violation) for violation in violations],
            baseline_persisted=persisted is not None,
            baseline_metadata=metadata,
            warnings=warnings,
        )

    async def persist_baseline(self, request: BaselineUpsertRequest) -> BaselineRead:
        """Freeze the Phase I limits of one series, replacing any previous ones.

        Raises:
            UnknownParameterError: `parameterCode` is not in the catalog.
            ValidationFailedError: `method = xbar_r` (the table stores one chart, X̄-R needs two).
            InsufficientDataError: the series cannot support limits, or the caller disabled the
                censored policy on a series that contains censored values.
        """
        self._require_parameter(request.parameter_code)
        if request.method != IMR_METHOD:
            raise ValidationFailedError(
                "El método 'xbar_r' todavía no se persiste: la tabla guarda los límites de una "
                "carta y X̄-R necesita dos. Usa method='imr'."
            )
        async with self._session.begin():
            rows = await self._baselines.get_observations(
                request.site_id, request.parameter_code, limit=request.baseline_points
            )
            censored = sum(1 for observation in rows if observation.value is None)
            if censored and not request.apply_censored_policy:
                raise InsufficientDataError(
                    f"{censored} observaciones censuradas (< LOQ) y la política de sustitución "
                    "está desactivada: no se pueden estimar límites de control."
                )
            values, _metadata = self._baseline_series(
                rows, request.baseline_points, request.parameter_code
            )
            imr = self._imr(values)
            baseline = await self._baselines.upsert_baseline(
                site_id=request.site_id,
                parameter_code=request.parameter_code,
                phase=PHASE_I,
                method=IMR_METHOD,
                n_points=len(values),
                data_range_start=rows[0].analyzed_at,
                data_range_end=rows[-1].analyzed_at,
                center_line=imr.individuals.center,
                ucl=imr.individuals.ucl,
                lcl=imr.individuals.lcl,
                catalog_version=self._catalog.version,
                computed_at=self._clock.now(),
            )
        logger.info(
            "baseline persisted",
            extra={
                "siteId": str(request.site_id),
                "parameterCode": request.parameter_code,
                "nPoints": baseline.n_points,
            },
        )
        return _baseline_read(baseline)

    async def get_persisted_baseline(
        self,
        site_id: UUID,
        parameter_code: str,
        phase: str = PHASE_I,
    ) -> BaselineRead:
        """The frozen limits of one series, or a 404 when they were never persisted.

        Raises:
            UnknownParameterError: `parameterCode` is not in the catalog.
            NotFoundError: nothing stored for that (site, parameter, phase).
        """
        self._require_parameter(parameter_code)
        baseline = await self._baselines.get_baseline(site_id, parameter_code, phase)
        if baseline is None:
            raise NotFoundError(
                f"No hay línea base persistida para el parámetro '{parameter_code}' en la fase "
                f"'{phase}'. Ejecuta POST /api/v1/spc/baseline para calcularla."
            )
        return _baseline_read(baseline)

    async def get_rules(
        self,
        site_id: UUID,
        parameter_code: str,
        *,
        baseline_points: int = MIN_BASELINE_POINTS,
    ) -> list[RuleViolationRead]:
        """Only the signals of the monitoring window; the chart itself is another endpoint."""
        chart = await self.compute_chart(site_id, parameter_code, baseline_points=baseline_points)
        return chart.violations

    def _spec_limits(self, parameter_code: str) -> SpecLimitsRead | None:
        """The normative range that may be drawn beside the control limits, if it is unique.

        Only `status = validated` limits are published: a `draft-verified` value is a decision the
        chemist has not signed yet, and drawing it would turn a pending value into a threshold
        (ADR-010). The first regulation of `SPEC_REGULATION_PREFERENCE` that has a signed limit
        wins; if that regulation has several signed limits (one per water use or monitoring
        area) there is no single band to draw, so the answer is `None` instead of a guess.
        """
        parameter = self._catalog.parameters[parameter_code]
        canonical = self._catalog.units.get(parameter.canonical_unit_code)
        if canonical is None or canonical.factor_to_canonical == 0:
            logger.warning(
                "canonical unit missing from the catalog",
                extra={"parameterCode": parameter_code},
            )
            return None

        for regulation in SPEC_REGULATION_PREFERENCE:
            validated = [
                limit
                for limit in self._catalog.limits
                if limit.parameter_code == parameter_code
                and limit.regulation_code == regulation
                and limit.status == VALIDATED_STATUS
            ]
            if not validated:
                continue
            if len(validated) > 1:
                logger.info(
                    "normative range omitted: several validated limits match",
                    extra={"parameterCode": parameter_code, "regulationCode": regulation},
                )
                return None
            limit = validated[0]
            if limit.min is None and limit.max is None:
                return None
            scale = self._unit_scale(limit.unit_code, canonical.factor_to_canonical)
            if scale is None:
                return None
            return SpecLimitsRead(
                min=None if limit.min is None else limit.min * scale,
                max=None if limit.max is None else limit.max * scale,
                unit_code=parameter.canonical_unit_code,
                regulation_code=limit.regulation_code,
                status=limit.status,
            )
        return None

    def _unit_scale(self, unit_code: str, canonical_factor: float) -> float | None:
        """Factor that converts a limit published in `unit_code` to the canonical unit.

        The catalog stores most limits already in the canonical unit, but a regulation that
        publishes µg/L for a mg/L parameter must not end up drawn three orders of magnitude off.
        An unknown unit means the value cannot be positioned, so the range is omitted.
        """
        unit = self._catalog.units.get(unit_code)
        if unit is None:
            logger.warning("limit unit missing from the catalog", extra={"unitCode": unit_code})
            return None
        return unit.factor_to_canonical / canonical_factor

    def _require_parameter(self, code: str) -> None:
        if code not in self._catalog.parameters:
            raise UnknownParameterError(f"El parámetro '{code}' no existe en el catálogo.")

    def _baseline_series(
        self,
        rows: list[Observation],
        baseline_points: int,
        parameter_code: str,
    ) -> tuple[list[float], dict[str, float | int | str]]:
        """Turn stored rows into the series the core consumes, or explain what is missing.

        `baseline_min_points` is a floor, not a default: a caller cannot ask for limits built on
        fewer points than ADR-001 allows, even if the query string says so.
        """
        required = max(baseline_points, self._baseline_min_points)
        if len(rows) < required:
            raise InsufficientDataError(
                f"Se requieren al menos {required} observaciones para la línea base de "
                f"'{parameter_code}' (hay {len(rows)})."
            )
        try:
            return select_baseline(
                [_baseline_row(observation) for observation in rows],
                min_points=required,
                censored_max_fraction=self._censored_max_fraction,
            )
        except SpcInsufficientDataError as exc:
            raise InsufficientDataError(str(exc)) from exc

    @staticmethod
    def _imr(values: list[float]) -> IMRResult:
        """The core refuses weak series with its own exception; the API speaks problem+json."""
        try:
            return compute_imr(values)
        except (SpcInsufficientDataError, ValueError) as exc:
            raise InsufficientDataError(str(exc)) from exc


def _baseline_row(
    observation: Observation,
) -> tuple[float | None, float | None, str | None, str]:
    """`(value, loq, qualifier, qc_flag)`; a censored row carries no value (ADR-003)."""
    value = None if observation.value is None else float(observation.value)
    loq = None if observation.loq is None else float(observation.loq)
    return value, loq, observation.qualifier, observation.qc_flag


def _monitoring_series(rows: list[Observation]) -> tuple[list[float], int]:
    """Phase II values: measured rows only, plus how many censored ones were left out.

    A censored value is not a number: substituting LOQ/2 in the monitoring window would draw an
    invented measurement, so it is excluded and counted in the warnings instead.
    """
    values: list[float] = []
    censored = 0
    for observation in rows:
        if observation.value is None:
            censored += 1
        else:
            values.append(float(observation.value))
    return values, censored


def _limits_read(limits: ControlLimits) -> ControlLimitsRead:
    return ControlLimitsRead(
        center=limits.center,
        ucl=limits.ucl,
        lcl=limits.lcl,
        sigma=limits.sigma,
        method=limits.method,
        n_points=limits.n_points,
    )


def _violation_read(violation: RuleViolation) -> RuleViolationRead:
    return RuleViolationRead(
        rule=violation.rule,
        index=violation.index,
        description=violation.description,
    )


def _baseline_read(baseline: SpcBaseline) -> BaselineRead:
    """Persisted limits as the API publishes them; an incomplete row is a 500, not a zero."""
    return BaselineRead(
        id=baseline.id,
        site_id=baseline.site_id,
        parameter_code=baseline.parameter_code,
        phase=baseline.phase,
        method=baseline.method,
        n_points=baseline.n_points,
        data_range_start=baseline.data_range_start,
        data_range_end=baseline.data_range_end,
        center_line=_number(baseline.center_line),
        ucl=_number(baseline.ucl),
        lcl=_number(baseline.lcl),
        catalog_version=baseline.catalog_version,
        computed_at=baseline.computed_at,
    )


def _number(value: Decimal | None) -> float:
    """Numeric columns are nullable in the schema; a baseline without limits is a server bug."""
    if value is None:
        raise ValueError("La línea base persistida está incompleta (falta un límite de control).")
    return float(value)
