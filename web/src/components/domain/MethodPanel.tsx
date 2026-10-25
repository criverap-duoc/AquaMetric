import { Info } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatNumber } from "@/lib/format";
import type { ControlLimits } from "@/types/api";

export interface MethodPanelProps {
  individuals: ControlLimits;
  movingRange: ControlLimits | null;
  /** Points the analyst asked Phase I to use. */
  baselinePoints: number;
  /** `false` when the limits were estimated on the fly and are not frozen (ADR-001). */
  baselinePersisted: boolean;
  /** `n`, `censored_count`, `censored_fraction`, `method`, `min_points` from `app/spc/baseline.py`. */
  metadata: Record<string, string | number>;
  warnings: string[];
  parameterName: string;
  unitCode: string;
  decimals: number;
}

/** The rules, written the way the glossary names them (04 §5). */
const RULES: { code: string; name: string; description: string }[] = [
  {
    code: "R1",
    name: "1 punto fuera de 3 σ",
    description: "Un valor queda más allá de un límite de control.",
  },
  {
    code: "R2",
    name: "9 puntos del mismo lado",
    description: "Nueve valores consecutivos por encima o por debajo de la línea central.",
  },
  {
    code: "R3",
    name: "6 puntos en tendencia",
    description: "Seis valores consecutivos que solo suben o solo bajan.",
  },
  {
    code: "R4",
    name: "2 de 3 más allá de 2 σ",
    description: "Dos de tres valores seguidos en la misma banda de 2 σ a 3 σ.",
  },
  {
    code: "R5",
    name: "4 de 5 más allá de 1 σ",
    description: "Cuatro de cinco valores seguidos en la misma banda de 1 σ a 3 σ.",
  },
];

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-border py-1 last:border-b-0">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="font-mono text-xs tabular-nums">{value}</dd>
    </div>
  );
}

function Formula({ expression, result }: { expression: string; result: string }) {
  return (
    <li className="flex flex-wrap items-baseline justify-between gap-2">
      <code className="font-mono text-xs text-muted-foreground">{expression}</code>
      <span className="font-mono text-xs tabular-nums">{result}</span>
    </li>
  );
}

/**
 * "¿Cómo se calculó?" panel: the numbers of the chart with the method behind them (04 §2.4).
 *
 * It repeats what `docs/spc-methods.md` says in plain Spanish, so a chemist can audit the chart
 * without reading the source. Limits are estimated in Phase I with `MR̄ / d₂` (ADR-001); the panel
 * shows the size of the baseline, how many censored values entered as `LOQ / 2` (ADR-003) and
 * whether the limits are frozen or were computed on the fly.
 */
export function MethodPanel({
  individuals,
  movingRange,
  baselinePoints,
  baselinePersisted,
  metadata,
  warnings,
  parameterName,
  unitCode,
  decimals,
}: MethodPanelProps) {
  const censoredCount = Number(metadata.censored_count ?? 0);
  const censoredFraction = Number(metadata.censored_fraction ?? 0);
  const minimumPoints = Number(metadata.min_points ?? baselinePoints);

  return (
    <Card className="gap-3 p-4">
      <CardHeader className="p-0">
        <CardTitle>
          <h3 className="text-base font-semibold">¿Cómo se calculó?</h3>
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          Carta I-MR de {parameterName}: promedios de a uno, con la variación medida entre valores
          consecutivos.
        </p>
      </CardHeader>

      <CardContent className="flex flex-col gap-4 p-0">
        <section aria-label="Línea base">
          <h4 className="text-xs font-semibold">Línea base (Fase I)</h4>
          <dl className="mt-1">
            <MetaRow
              label="Estado de los límites"
              value={baselinePersisted ? "Congelados" : "Calculados en esta consulta"}
            />
            <MetaRow
              label="Puntos usados"
              value={`${individuals.nPoints} de ${baselinePoints} solicitados`}
            />
            <MetaRow label="Mínimo exigido" value={`${minimumPoints} puntos`} />
            <MetaRow
              label="Censurados en la base"
              value={`${censoredCount} · ${formatNumber(censoredFraction * 100, 1)} %`}
            />
          </dl>
        </section>

        <section aria-label="Límites de control">
          <h4 className="text-xs font-semibold">Límites de control (3 σ)</h4>
          <ul className="mt-1 flex flex-col gap-1">
            <Formula
              expression="CL = promedio de la línea base"
              result={`${formatNumber(individuals.center, decimals)} ${unitCode}`}
            />
            <Formula
              expression="UCL = CL + 2,66 · MR̄"
              result={`${formatNumber(individuals.ucl, decimals)} ${unitCode}`}
            />
            <Formula
              expression="LCL = CL − 2,66 · MR̄"
              result={`${formatNumber(individuals.lcl, decimals)} ${unitCode}`}
            />
            <Formula
              expression="σ = MR̄ / 1,128   (d₂ con n = 2)"
              result={`${formatNumber(individuals.sigma, decimals)} ${unitCode}`}
            />
            {movingRange ? (
              <Formula
                expression="MR: UCL = 3,267 · MR̄"
                result={`${formatNumber(movingRange.ucl, decimals)} ${unitCode}`}
              />
            ) : null}
          </ul>
        </section>

        <section aria-label="Reglas de decisión">
          <h4 className="text-xs font-semibold">Reglas de decisión (R1 a R5)</h4>
          <ul className="mt-1 flex flex-col gap-1.5">
            {RULES.map((rule) => (
              <li key={rule.code} className="flex items-start gap-2 text-xs">
                <span className="mt-px rounded-sm bg-muted px-1 font-mono font-medium">
                  {rule.code}
                </span>
                <span>
                  <span className="font-medium">{rule.name}.</span>{" "}
                  <span className="text-muted-foreground">{rule.description}</span>
                </span>
              </li>
            ))}
          </ul>
        </section>

        <section aria-label="Supuestos">
          <h4 className="text-xs font-semibold">Supuestos</h4>
          <ul className="mt-1 flex list-disc flex-col gap-1 pl-4 text-xs text-muted-foreground">
            <li>
              Los límites usan la variación entre valores consecutivos (MR̄ / 1,128), no la
              desviación estándar global de la serie.
            </li>
            <li>
              Se asume una distribución aproximadamente normal; en parámetros muy sesgados conviene
              revisar una transformación logarítmica.
            </li>
            <li>
              Los valores censurados (&lt; LOQ) entran al cálculo de la línea base como LOQ/2 y
              nunca se guardan con ese valor.
            </li>
            <li>
              Los límites de control describen el proceso, no la norma: un valor en control puede
              quedar fuera del rango referencial.
            </li>
          </ul>
        </section>

        {warnings.length > 0 ? (
          <div className="rounded-md bg-info-soft p-3 text-xs text-info-soft-foreground">
            <p className="flex items-center gap-1.5 font-medium">
              <Info aria-hidden="true" className="size-3.5" />
              Para tener en cuenta
            </p>
            <ul className="mt-1 flex list-disc flex-col gap-1 pl-4">
              {warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

