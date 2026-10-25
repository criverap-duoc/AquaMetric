import { Info, Search } from "lucide-react";
import { useMemo, useState, type FormEvent } from "react";

import { useLimits, useParameters, useRegulations, useUnits } from "@/api/catalog";
import { useScreeningEvaluate } from "@/api/screening";
import { DataTable } from "@/components/domain/DataTable";
import { ErrorState } from "@/components/domain/ErrorState";
import { LimitBadge } from "@/components/domain/LimitBadge";
import { ScreeningBadge } from "@/components/domain/ScreeningBadge";
import { createLimitColumns } from "@/components/domain/limit-columns";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { formatNumber, formatUnit } from "@/lib/format";
import type { LimitApplied, ScreeningResponse } from "@/types/api";

/** Values of one scope column, without duplicates and without the nulls. */
function uniqueValues(values: Array<string | null>): string[] {
  return [...new Set(values.filter((value): value is string => Boolean(value)))];
}

function rangeLabel(limit: LimitApplied, decimals: number): string {
  const format = (value: number) => formatNumber(value, decimals);

  if (limit.min !== null && limit.max !== null) {
    return `${format(limit.min)} – ${formatUnit(limit.max, limit.unitCode, decimals)}`;
  }

  if (limit.max !== null) {
    return `máximo ${formatUnit(limit.max, limit.unitCode, decimals)}`;
  }

  if (limit.min !== null) {
    return `mínimo ${formatUnit(limit.min, limit.unitCode, decimals)}`;
  }

  return "sin rango numérico";
}

/** The flag plus everything needed to audit it, in amber when it is a range departure. */
function ScreeningResult({
  response,
  decimals,
}: {
  response: ScreeningResponse;
  decimals: number;
}) {
  const limit = response.limitApplied;

  return (
    <Card className="gap-3 p-4">
      <CardHeader className="p-0">
        <CardTitle>
          <h2 className="text-base font-semibold">Resultado</h2>
        </CardTitle>
        <CardDescription className="text-xs">
          Comparación de una observación con el rango de referencia del catálogo
        </CardDescription>
      </CardHeader>

      <CardContent className="flex flex-col gap-3 p-0">
        <div className="flex flex-wrap items-center gap-2">
          <ScreeningBadge flag={response.flag} reason={response.reason} />
          <p className="text-xs">{response.reason}</p>
        </div>

        {limit ? (
          <div className="flex flex-wrap items-center gap-2 rounded-md border border-border p-3">
            <LimitBadge status={limit.status} />
            <span className="font-mono text-xs">{limit.regulationCode}</span>
            <span className="text-xs text-muted-foreground">{rangeLabel(limit, decimals)}</span>
          </div>
        ) : null}

        {response.exceedanceRatio !== null ? (
          <p className="text-xs text-muted-foreground">
            El valor es {formatNumber(response.exceedanceRatio, 2)} × el borde del rango.
          </p>
        ) : null}

        <ul className="flex list-disc flex-col gap-1 pl-4 text-xs text-muted-foreground">
          {response.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

/**
 * Screening screen: one value against one catalog limit.
 *
 * The disclaimer is fixed and not dismissible because the flag is referential: an observation
 * outside the range is not an infringement and the formal assessment needs a three-year series
 * (ADR-010, ADR-012).
 */
export function ScreeningPage() {
  const parametersQuery = useParameters();
  const unitsQuery = useUnits();
  const regulationsQuery = useRegulations();

  const [parameterCode, setParameterCode] = useState("");
  const [valueInput, setValueInput] = useState("");
  const [unitCode, setUnitCode] = useState<string | null>(null);
  const [regulationCode, setRegulationCode] = useState<string | null>(null);
  const [contextCode, setContextCode] = useState<string | null>(null);
  const [monitoringArea, setMonitoringArea] = useState<string | null>(null);
  const [qualityLevel, setQualityLevel] = useState<string | null>(null);

  const parameters = useMemo(() => parametersQuery.data ?? [], [parametersQuery.data]);
  const units = unitsQuery.data ?? [];
  const regulations = regulationsQuery.data ?? [];

  // Derived instead of stored, so a late response never leaves a stale selection behind.
  const parameter = parameters.find((item) => item.code === parameterCode) ?? parameters[0];
  const regulation = regulations.find((item) => item.code === regulationCode) ?? regulations[0];

  const canonicalCode = parameter?.canonicalUnitCode ?? "";
  const dimension = units.find((item) => item.code === canonicalCode)?.dimension;
  const parameterUnits = units.filter((item) => item.dimension === dimension);
  const selectedUnitCode = unitCode ?? canonicalCode;

  const limitsQuery = useLimits({
    parameterCode: parameter?.code,
    regulation: regulation?.code,
  });
  const limits = limitsQuery.data?.data ?? [];
  const contexts = uniqueValues(limits.map((limit) => limit.context));
  const monitoringAreas = uniqueValues(limits.map((limit) => limit.monitoringAreaCode));
  const qualityLevels = uniqueValues(limits.map((limit) => limit.qualityLevel));

  const selectedContext = contextCode ?? contexts[0] ?? null;
  const selectedArea = monitoringArea ?? monitoringAreas[0] ?? null;
  const selectedLevel = qualityLevel ?? qualityLevels[0] ?? null;

  const columns = useMemo(() => createLimitColumns(parameters), [parameters]);

  const parsedValue = Number(valueInput.replace(",", "."));
  const isValidValue = valueInput.trim() !== "" && Number.isFinite(parsedValue);
  const canEvaluate = Boolean(parameter && regulation && selectedUnitCode) && isValidValue;

  const evaluate = useScreeningEvaluate();

  const handleParameterChange = (code: string) => {
    setParameterCode(code);
    // The unit and the scope belong to the previous parameter: dropping them avoids a mismatch.
    setUnitCode(null);
    setContextCode(null);
    setMonitoringArea(null);
    setQualityLevel(null);
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!parameter || !regulation || !canEvaluate) {
      return;
    }

    evaluate.mutate({
      parameterCode: parameter.code,
      value: parsedValue,
      unitCode: selectedUnitCode,
      analyzedAt: new Date().toISOString(),
      regulation: regulation.code,
      context: selectedContext,
      monitoringArea: selectedArea,
      qualityLevel: selectedLevel,
    });
  };

  return (
    <section className="flex flex-col gap-4">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Screening</h1>
        <p className="text-xs text-muted-foreground">
          Screening referencial. Compara una observación con un límite normativo del catálogo. No es
          un dictamen de cumplimiento legal.
        </p>
      </header>

      <div className="flex items-start gap-2 rounded-md bg-warning-soft p-3 text-warning-soft-foreground">
        <Info aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
        <p className="text-xs">
          Screening referencial, no dictamen de cumplimiento legal. La evaluación formal requiere
          análisis trienal (ver ADR-010).
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
        <Card className="gap-3 p-4 xl:col-span-5">
          <CardHeader className="p-0">
            <CardTitle>
              <h2 className="text-base font-semibold">Evaluar observación</h2>
            </CardTitle>
            <CardDescription className="text-xs">
              Un valor, un límite. La unidad se convierte explícitamente antes de comparar.
            </CardDescription>
          </CardHeader>

          <CardContent className="p-0">
            {parametersQuery.isPending ? (
              <p className="text-xs text-muted-foreground">Cargando el catálogo…</p>
            ) : null}

            {parametersQuery.isError ? (
              <ErrorState
                error={parametersQuery.error}
                onRetry={() => void parametersQuery.refetch()}
              />
            ) : null}

            {parametersQuery.data ? (
              <form className="flex flex-col gap-3" onSubmit={handleSubmit}>
                <div className="flex flex-col gap-1">
                  <label htmlFor="screening-parameter" className="text-xs text-muted-foreground">
                    Parámetro
                  </label>
                  <Select value={parameter?.code ?? ""} onValueChange={handleParameterChange}>
                    <SelectTrigger id="screening-parameter" className="w-full">
                      <SelectValue placeholder="Elige un parámetro" />
                    </SelectTrigger>
                    <SelectContent>
                      {parameters.map((item) => (
                        <SelectItem key={item.code} value={item.code}>
                          {item.nameEs} ({item.code})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <div className="flex flex-col gap-1">
                    <label htmlFor="screening-value" className="text-xs text-muted-foreground">
                      Valor medido
                    </label>
                    <Input
                      id="screening-value"
                      inputMode="decimal"
                      placeholder="7,6"
                      value={valueInput}
                      onChange={(event) => setValueInput(event.target.value)}
                      className="font-mono tabular-nums"
                    />
                  </div>

                  <div className="flex flex-col gap-1">
                    <label htmlFor="screening-unit" className="text-xs text-muted-foreground">
                      Unidad
                    </label>
                    <Select value={selectedUnitCode} onValueChange={setUnitCode}>
                      <SelectTrigger id="screening-unit" className="w-full">
                        <SelectValue placeholder="Unidad" />
                      </SelectTrigger>
                      <SelectContent>
                        {parameterUnits.map((unit) => (
                          <SelectItem key={unit.code} value={unit.code}>
                            {unit.code} · {unit.nameEs}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="flex flex-col gap-1">
                  <label htmlFor="screening-regulation" className="text-xs text-muted-foreground">
                    Regulación
                  </label>
                  <Select
                    value={regulation?.code ?? ""}
                    onValueChange={(code) => {
                      setRegulationCode(code);
                      setContextCode(null);
                      setMonitoringArea(null);
                      setQualityLevel(null);
                    }}
                  >
                    <SelectTrigger id="screening-regulation" className="w-full">
                      <SelectValue placeholder="Regulación" />
                    </SelectTrigger>
                    <SelectContent>
                      {regulations.map((item) => (
                        <SelectItem key={item.code} value={item.code}>
                          {item.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {contexts.length > 0 ? (
                  <div className="flex flex-col gap-1">
                    <label htmlFor="screening-context" className="text-xs text-muted-foreground">
                      Uso del agua (contexto)
                    </label>
                    <Select value={selectedContext ?? ""} onValueChange={setContextCode}>
                      <SelectTrigger id="screening-context" className="w-full">
                        <SelectValue placeholder="Contexto" />
                      </SelectTrigger>
                      <SelectContent>
                        {contexts.map((value) => (
                          <SelectItem key={value} value={value}>
                            {value.replaceAll("_", " ")}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                ) : null}

                {monitoringAreas.length > 0 ? (
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <div className="flex flex-col gap-1">
                      <label htmlFor="screening-area" className="text-xs text-muted-foreground">
                        Área de vigilancia
                      </label>
                      <Select value={selectedArea ?? ""} onValueChange={setMonitoringArea}>
                        <SelectTrigger id="screening-area" className="w-full">
                          <SelectValue placeholder="Área" />
                        </SelectTrigger>
                        <SelectContent>
                          {monitoringAreas.map((value) => (
                            <SelectItem key={value} value={value}>
                              {value}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="flex flex-col gap-1">
                      <label htmlFor="screening-level" className="text-xs text-muted-foreground">
                        Nivel de calidad
                      </label>
                      <Select value={selectedLevel ?? ""} onValueChange={setQualityLevel}>
                        <SelectTrigger id="screening-level" className="w-full">
                          <SelectValue placeholder="Nivel" />
                        </SelectTrigger>
                        <SelectContent>
                          {qualityLevels.map((value) => (
                            <SelectItem key={value} value={value}>
                              {value}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                ) : null}

                <Button type="submit" disabled={!canEvaluate || evaluate.isPending}>
                  <Search aria-hidden="true" />
                  {evaluate.isPending ? "Evaluando…" : "Evaluar"}
                </Button>
              </form>
            ) : null}
          </CardContent>
        </Card>

        <div className="flex flex-col gap-4 xl:col-span-7">
          {evaluate.isError ? (
            <ErrorState error={evaluate.error} onRetry={() => evaluate.reset()} />
          ) : null}

          {evaluate.data ? (
            <ScreeningResult response={evaluate.data} decimals={parameter?.decimals ?? 2} />
          ) : null}

          {!evaluate.data && !evaluate.isError ? (
            <Card className="items-center p-8 text-center">
              <p className="text-sm font-medium">Sin evaluación todavía</p>
              <p className="max-w-md text-xs text-muted-foreground">
                Elige el parámetro, escribe el valor con su unidad y presiona «Evaluar». El
                resultado es referencial: describe el rango del catálogo, no un veredicto.
              </p>
            </Card>
          ) : null}
        </div>
      </div>

      <Card className="gap-2 p-4">
        <CardHeader className="p-0">
          <CardTitle>
            <h2 className="text-base font-semibold">Límites disponibles</h2>
          </CardTitle>
          <CardDescription className="text-xs">
            {limitsQuery.data
              ? `${limitsQuery.data.meta.total} límites · ${limitsQuery.data.meta.validatedCount} validados · ${limitsQuery.data.meta.draftCount} pendientes`
              : "Límites del parámetro y la regulación elegidos · solo los validados producen un resultado"}
          </CardDescription>
        </CardHeader>

        <CardContent className="p-0">
          {limitsQuery.isError ? (
            <ErrorState error={limitsQuery.error} onRetry={() => void limitsQuery.refetch()} />
          ) : (
            <DataTable
              columns={columns}
              data={limits}
              isLoading={limitsQuery.isPending}
              caption="Límites del catálogo para el parámetro y la regulación elegidos"
              emptyMessage="Este parámetro no tiene límites en la regulación elegida."
            />
          )}
        </CardContent>
      </Card>
    </section>
  );
}




