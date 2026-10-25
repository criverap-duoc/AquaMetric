"""Screening orchestration: resolve catalog codes, then delegate the decision (02 §6).

The service owns the lookups and the unit guard; `app.screening` stays pure and unaware of the
catalog object, so the policy can be tested with hand-built limits and no filesystem.
"""

from app.catalog import Catalog, Limit, Parameter, Unit
from app.core.errors import UnitMismatchError, UnknownParameterError
from app.schemas.screening import LimitApplied, ScreeningRequest, ScreeningResponse
from app.screening import screen_observation, select_applicable_limit

# Always present: the MVP never publishes a compliance verdict (ADR-010, ADR-012 §6).
REFERENTIAL_WARNINGS = (
    "Screening referencial, no dictamen de cumplimiento normativo.",
    "Una observación individual no reemplaza la evaluación estadística requerida por la norma.",
)

# Extra sentence per regulation, because each one fails differently.
REGULATION_WARNINGS = {
    "NCh1333": (
        "Referencia por uso; no constituye resolución administrativa ni certificación de "
        "cumplimiento."
    ),
    "DS53-2014-MMA": (
        "La evaluación formal requiere serie trienal, cobertura estacional y cálculo P95/P5 "
        "según área de vigilancia."
    ),
}


class ScreeningService:
    """Answers «is this value inside the reference range?» for one observation.

    No database access and no clock: the answer depends only on the request and the catalog,
    which is what makes it reproducible when the catalog version changes.
    """

    def __init__(self, catalog: Catalog) -> None:
        self._catalog = catalog

    def evaluate(self, request: ScreeningRequest) -> ScreeningResponse:
        """Screen one value against the single limit its scope selects.

        Raises:
            UnknownParameterError: `parameterCode` is not in the catalog.
            UnitMismatchError: `unitCode` is unknown or measures another dimension.
        """
        parameter = self._parameter(request.parameter_code)
        unit = self._unit(request.unit_code, parameter)
        limit = select_applicable_limit(
            self._catalog.limits,
            request.parameter_code,
            request.regulation,
            request.context,
            request.monitoring_area,
            request.quality_level,
        )
        result = screen_observation(
            request.value * unit.factor_to_canonical,
            None,
            None,
            parameter,
            limit,
        )
        warnings = [*REFERENTIAL_WARNINGS, *self._regulation_warnings(request.regulation)]
        if unit.code != parameter.canonical_unit_code:
            warnings.append(
                f"Valor convertido de {unit.code} a {parameter.canonical_unit_code} "
                f"(factor {unit.factor_to_canonical:g}) antes de comparar."
            )
        return ScreeningResponse(
            flag=result.flag,
            reason=result.reason,
            limit_applied=self._limit_payload(result.limit_applied),
            exceedance_ratio=result.exceedance_ratio,
            warnings=warnings,
        )

    def available_limits(
        self,
        *,
        parameter_code: str,
        regulation: str,
        context: str | None = None,
        monitoring_area: str | None = None,
        quality_level: str | None = None,
    ) -> list[LimitApplied]:
        """Limits of one parameter and regulation, narrowed by the scope the caller states.

        Draft limits are listed: the selector must show them as «Pendiente de validación»
        instead of hiding what the catalog actually contains.

        Raises:
            UnknownParameterError: `parameterCode` is not in the catalog.
        """
        self._parameter(parameter_code)
        return [
            LimitApplied.model_validate(limit)
            for limit in self._catalog.limits
            if limit.parameter_code == parameter_code
            and limit.regulation_code == regulation
            and (context is None or limit.context == context)
            and (monitoring_area is None or limit.monitoring_area_code == monitoring_area)
            and (quality_level is None or limit.quality_level == quality_level)
        ]

    def _parameter(self, code: str) -> Parameter:
        parameter = self._catalog.parameters.get(code)
        if parameter is None:
            raise UnknownParameterError(f"El parámetro '{code}' no existe en el catálogo.")
        return parameter

    def _unit(self, code: str, parameter: Parameter) -> Unit:
        unit = self._catalog.units.get(code)
        if unit is None:
            raise UnitMismatchError(f"La unidad '{code}' no existe en el catálogo.")
        canonical = self._catalog.units[parameter.canonical_unit_code]
        if unit.dimension != canonical.dimension:
            raise UnitMismatchError(
                f"La unidad '{code}' mide {unit.dimension}, no lo que mide {parameter.code} "
                f"({parameter.canonical_unit_code})."
            )
        return unit

    def _regulation_warnings(self, regulation: str) -> list[str]:
        warning = REGULATION_WARNINGS.get(regulation)
        return [warning] if warning is not None else []

    @staticmethod
    def _limit_payload(limit: Limit | None) -> LimitApplied | None:
        return None if limit is None else LimitApplied.model_validate(limit)
