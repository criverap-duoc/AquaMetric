import { Filter, Info } from "lucide-react";
import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { useCatalogMeta, useParameters } from "@/api/catalog";
import { useObservations } from "@/api/observations";
import { useSites } from "@/api/sites";
import { DEFAULT_BASELINE_POINTS, MIN_BASELINE_POINTS, useControlChart } from "@/api/spc";
import { ControlChart } from "@/components/domain/ControlChart";
import { ErrorState } from "@/components/domain/ErrorState";
import { MethodPanel } from "@/components/domain/MethodPanel";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import type { ControlObservation } from "@/features/control/types";
import { ApiError } from "@/lib/api-client";

/** Baseline sizes the analyst can choose: 20 is the Phase I minimum of ADR-001. */
const BASELINE_POINT_OPTIONS = [20, 30, 40, 50] as const;

const DEFAULT_PARAMETER_CODE = "PH";

/**
 * Rows after the baseline that `GET /spc/control-charts` scans by default.
 *
 * Mirrors `DEFAULT_MONITORING_POINTS` of `app/services/spc_service.py`: the chart has to plot the
 * window the rules evaluated, otherwise a signal would point at a row nobody can see.
 */
const MONITORING_POINTS = 100;

interface FilterPanelProps {
  siteCode: string;
  parameterCode: string;
  baselinePoints: number;
  siteOptions: Array<{ code: string; label: string }>;
  parameterOptions: Array<{ code: string; label: string }>;
  onChange: (patch: { site?: string; param?: string; baseline?: number }) => void;
}

/** Site · parameter · baseline size, shared by the desktop card and the mobile Sheet. */
function FilterPanel({
  siteCode,
  parameterCode,
  baselinePoints,
  siteOptions,
  parameterOptions,
  onChange,
}: FilterPanelProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <div className="flex flex-col gap-1">
        <label htmlFor="control-site" className="text-xs text-muted-foreground">
          Sitio
        </label>
        <Select value={siteCode} onValueChange={(value) => onChange({ site: value })}>
          <SelectTrigger id="control-site" className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {siteOptions.map((site) => (
              <SelectItem key={site.code} value={site.code}>
                {site.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="control-parameter" className="text-xs text-muted-foreground">
          Parámetro
        </label>
        <Select value={parameterCode} onValueChange={(value) => onChange({ param: value })}>
          <SelectTrigger id="control-parameter" className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {parameterOptions.map((parameter) => (
              <SelectItem key={parameter.code} value={parameter.code}>
                {parameter.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="control-baseline" className="text-xs text-muted-foreground">
          Puntos de la línea base
        </label>
        <Select
          value={String(baselinePoints)}
          onValueChange={(value) => onChange({ baseline: Number(value) })}
        >
          <SelectTrigger id="control-baseline" className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {BASELINE_POINT_OPTIONS.map((points) => (
              <SelectItem key={points} value={String(points)}>
                {points} observaciones
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}

/** Placeholder with the shape of the card: two panels, one taller than the other. */
function ChartSkeleton() {
  return (
    <Card className="gap-3 p-4" aria-busy="true">
      <Skeleton className="h-5 w-56" />
      <Skeleton className="h-4 w-72" />
      <Skeleton className="h-64 w-full" />
      <Skeleton className="h-32 w-full" />
      <span className="sr-only">Calculando la carta de control…</span>
    </Card>
  );
}

/**
 * Control (SPC) page: the I-MR chart of one series plus the panel that explains how it was
 * computed.
 *
 * Filters live in the URL (`?site=&param=&baseline=`) so a link reproduces the same chart
 * (04 §4). The limits, the signals and the baseline metadata come from
 * `GET /api/v1/spc/control-charts`; the plotted values come from the deterministic demo series
 * until `GET /api/v1/observations` exists (TODO #E-1f).
 */
export function ControlPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [isFiltersOpen, setIsFiltersOpen] = useState(false);

  const parametersQuery = useParameters();
  const metaQuery = useCatalogMeta();

  const parametersByCode = useMemo(
    () => new Map((parametersQuery.data ?? []).map((parameter) => [parameter.code, parameter])),
    [parametersQuery.data],
  );

  const sitesQuery = useSites({ page: 1, pageSize: 100 });

  // Sites come from the API only: an unseeded database has to say «sin sitios», never invent them.
  const siteOptions = useMemo(
    () =>
      (sitesQuery.data?.data ?? []).map((row) => ({
        id: row.id,
        code: row.code,
        name: row.name,
      })),
    [sitesQuery.data],
  );

  const siteSelectOptions = useMemo(
    () =>
      siteOptions.map((option) => ({
        code: option.code,
        label: `${option.code} · ${option.name}`,
      })),
    [siteOptions],
  );

  const requestedSite = searchParams.get("site");
  const site = siteOptions.find((option) => option.code === requestedSite) ?? siteOptions[0] ?? null;
  const siteCode = site?.code ?? "";

  // Every catalog parameter is offered: a series without enough history answers «datos
  // insuficientes» below, which is the honest state instead of a hidden option.
  const parameterOptions = useMemo(
    () =>
      (parametersQuery.data ?? []).map((parameter) => ({
        code: parameter.code,
        label: parameter.nameEs,
      })),
    [parametersQuery.data],
  );

  const requestedParameter = searchParams.get("param") ?? DEFAULT_PARAMETER_CODE;
  const parameterCode = parameterOptions.some((option) => option.code === requestedParameter)
    ? requestedParameter
    : (parameterOptions[0]?.code ?? DEFAULT_PARAMETER_CODE);

  const requestedBaseline = Number(searchParams.get("baseline"));
  const baselinePoints = (BASELINE_POINT_OPTIONS as readonly number[]).includes(requestedBaseline)
    ? requestedBaseline
    : DEFAULT_BASELINE_POINTS;

  const updateFilters = (patch: { site?: string; param?: string; baseline?: number }) => {
    const next = new URLSearchParams(searchParams);

    if (patch.site) {
      next.set("site", patch.site);
    }

    if (patch.param) {
      next.set("param", patch.param);
    }

    if (patch.baseline !== undefined) {
      next.set("baseline", String(patch.baseline));
    }

    setSearchParams(next, { replace: true });
  };

  const chartQuery = useControlChart({
    siteId: site?.id ?? "",
    parameterCode,
    baselinePoints,
  });

  // The window the API scanned: the oldest `baselinePoints` observations plus the monitored rows.
  // Requesting exactly that many rows in ascending order reproduces the two slices the SPC service
  // builds, so the plotted points are the ones the rules evaluated.
  const observationsQuery = useObservations({
    siteId: site?.id,
    parameterCode,
    order: "asc",
    page: 1,
    pageSize: baselinePoints + MONITORING_POINTS,
  });

  const series = useMemo<ControlObservation[] | null>(() => {
    const rows = observationsQuery.data?.data ?? [];

    if (rows.length === 0) {
      return null;
    }

    return rows.map((row, index) => ({
      index,
      analyzedAt: row.analyzedAt,
      value: row.value,
      qualifier: row.qualifier,
      loq: row.loq,
      qcFlag: row.qcFlag,
    }));
  }, [observationsQuery.data]);

  const parameter = parametersByCode.get(parameterCode);
  const parameterName = parameter?.nameEs ?? parameterCode;
  const unitCode = parameter?.canonicalUnitCode ?? "—";
  const decimals = parameter?.decimals ?? 2;
  const catalogVersion = metaQuery.data?.version ?? "—";

  const problem = chartQuery.error instanceof ApiError ? chartQuery.error.problem : null;
  // A short series is not a failure: the analyst needs to know how many points are missing.
  const isInsufficientData = problem?.code === "INSUFFICIENT_DATA";

  const isPending = chartQuery.isPending || observationsQuery.isPending || sitesQuery.isPending;
  const error = sitesQuery.error ?? parametersQuery.error ?? chartQuery.error ?? observationsQuery.error;

  const handleRetry = () => {
    void chartQuery.refetch();
    void observationsQuery.refetch();
    void parametersQuery.refetch();
    void sitesQuery.refetch();
  };

  return (
    <section className="flex flex-col gap-4">
      <header className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Control (SPC)</h1>
          <p className="text-xs text-muted-foreground">
            Carta I-MR de un parámetro: límites de control estimados en la línea base y señales de
            las reglas R1 a R5.
          </p>
        </div>

        <Button
          type="button"
          variant="outline"
          size="sm"
          className="lg:hidden"
          aria-expanded={isFiltersOpen}
          onClick={() => setIsFiltersOpen(true)}
        >
          <Filter aria-hidden="true" />
          Filtros
        </Button>
      </header>

      <Card className="hidden p-4 lg:block">
        <FilterPanel
          siteCode={siteCode}
          parameterCode={parameterCode}
          baselinePoints={baselinePoints}
          siteOptions={siteSelectOptions}
          parameterOptions={parameterOptions}
          onChange={updateFilters}
        />
      </Card>

      <Sheet open={isFiltersOpen} onOpenChange={setIsFiltersOpen}>
        <SheetContent side="right" className="w-full sm:max-w-sm">
          <SheetHeader>
            <SheetTitle>Filtros</SheetTitle>
          </SheetHeader>
          <div className="px-4 pb-4">
            <FilterPanel
              siteCode={siteCode}
              parameterCode={parameterCode}
              baselinePoints={baselinePoints}
              siteOptions={siteSelectOptions}
              parameterOptions={parameterOptions}
              onChange={updateFilters}
            />
          </div>
        </SheetContent>
      </Sheet>

      <div className="flex items-start gap-2 rounded-md bg-warning-soft p-3 text-warning-soft-foreground">
        <Info aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
        <p className="text-xs">
          <span className="font-medium">Límite de control ≠ límite normativo.</span> Estos límites
          describen la variación del proceso (media ± 3 σ) y no evalúan cumplimiento legal: el
          screening es referencial (ADR-010).
        </p>
      </div>

      {!error && isPending ? <ChartSkeleton /> : null}

      {!error && !isPending && siteOptions.length === 0 ? (
        <Card className="items-center p-8 text-center">
          <p className="text-sm font-medium">Todavía no hay sitios registrados</p>
          <p className="max-w-md text-xs text-muted-foreground">
            Carga un lote con el simulador y la carta de control aparecerá aquí.
          </p>
        </Card>
      ) : null}

      {isInsufficientData ? (
        <div className="flex flex-col items-start gap-2 rounded-md bg-info-soft p-4 text-info-soft-foreground">
          <div className="flex items-start gap-2">
            <Info aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
            <div className="flex flex-col gap-1">
              <p className="text-sm font-medium">Datos insuficientes para la línea base</p>
              <p className="text-xs">
                {problem?.detail ??
                  `Se requieren al menos ${MIN_BASELINE_POINTS} observaciones válidas.`}{" "}
                Reduce el tamaño de la línea base o elige un sitio con más historial.
              </p>
            </div>
          </div>
          <Button type="button" variant="outline" size="sm" onClick={handleRetry}>
            Reintentar
          </Button>
        </div>
      ) : null}

      {error && !isInsufficientData ? <ErrorState error={error} onRetry={handleRetry} /> : null}

      {chartQuery.data && series ? (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
          <div className="xl:col-span-8">
            <ControlChart
              observations={series}
              individuals={chartQuery.data.individuals}
              movingRange={chartQuery.data.movingRange}
              specLimits={
                chartQuery.data.specLimits
                  ? {
                      min: chartQuery.data.specLimits.min ?? undefined,
                      max: chartQuery.data.specLimits.max ?? undefined,
                      regulationCode: chartQuery.data.specLimits.regulationCode,
                    }
                  : null
              }
              violations={chartQuery.data.violations}
              parameterName={parameterName}
              unitCode={unitCode}
              decimals={decimals}
              siteCode={siteCode}
              catalogVersion={catalogVersion}
              updatedAt={new Date(chartQuery.dataUpdatedAt)}
            />
          </div>

          <div className="xl:col-span-4">
            <MethodPanel
              individuals={chartQuery.data.individuals}
              movingRange={chartQuery.data.movingRange}
              baselinePoints={baselinePoints}
              baselinePersisted={chartQuery.data.baselinePersisted}
              metadata={chartQuery.data.baselineMetadata}
              warnings={chartQuery.data.warnings}
              parameterName={parameterName}
              unitCode={unitCode}
              decimals={decimals}
            />
          </div>
        </div>
      ) : null}
    </section>
  );
}

