import { Filter, Info } from "lucide-react";
import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { useCatalogMeta, useParameters } from "@/api/catalog";
import { MIN_BASELINE_POINTS, useControlChart } from "@/api/spc";
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
import {
  BASELINE_POINT_OPTIONS,
  CONTROL_SITES,
  DEFAULT_BASELINE_POINTS,
  DEFAULT_PARAMETER_CODE,
  DEFAULT_SITE_CODE,
  controlSeriesFor,
  controlSiteFor,
} from "@/features/control/demo-data";
import { DEMO_PARAMETER_CODES, findDemoSeries } from "@/features/series/demo-data";
import { ApiError } from "@/lib/api-client";

interface FilterPanelProps {
  siteCode: string;
  parameterCode: string;
  baselinePoints: number;
  parameterOptions: Array<{ code: string; label: string }>;
  onChange: (patch: { site?: string; param?: string; baseline?: number }) => void;
}

/** Site · parameter · baseline size, shared by the desktop card and the mobile Sheet. */
function FilterPanel({
  siteCode,
  parameterCode,
  baselinePoints,
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
            {CONTROL_SITES.map((site) => (
              <SelectItem key={site.code} value={site.code}>
                {site.code}
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

  const siteCode = controlSiteFor(searchParams.get("site") ?? "")?.code ?? DEFAULT_SITE_CODE;
  const site = controlSiteFor(siteCode);

  // Only the parameters the demo has a series for: an empty chart would be a dead end.
  const parameterOptions = useMemo(
    () =>
      DEMO_PARAMETER_CODES.filter((code) => findDemoSeries(siteCode, code) !== null).map((code) => ({
        code,
        label: parametersByCode.get(code)?.nameEs ?? code,
      })),
    [siteCode, parametersByCode],
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
      const nextSite = patch.site;
      next.set("site", nextSite);

      // The new site may not have the parameter that is currently plotted: fall back to its first
      // series, otherwise the selectors and the chart would disagree.
      if (findDemoSeries(nextSite, parameterCode) === null) {
        const fallback = DEMO_PARAMETER_CODES.find(
          (code) => findDemoSeries(nextSite, code) !== null,
        );

        if (fallback) {
          next.set("param", fallback);
        }
      }
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

  const series = controlSeriesFor(siteCode, parameterCode);
  const parameter = parametersByCode.get(parameterCode);
  const parameterName = parameter?.nameEs ?? parameterCode;
  const unitCode = series?.unitCode ?? parameter?.canonicalUnitCode ?? "—";
  const decimals = parameter?.decimals ?? series?.decimals ?? 2;
  const catalogVersion = metaQuery.data?.version ?? "—";

  const problem = chartQuery.error instanceof ApiError ? chartQuery.error.problem : null;
  // A short series is not a failure: the analyst needs to know how many points are missing.
  const isInsufficientData = problem?.code === "INSUFFICIENT_DATA";

  const handleRetry = () => {
    void chartQuery.refetch();
    void parametersQuery.refetch();
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

      {chartQuery.isPending ? <ChartSkeleton /> : null}

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

      {chartQuery.isError && !isInsufficientData ? (
        <ErrorState error={chartQuery.error} onRetry={handleRetry} />
      ) : null}

      {chartQuery.data && !series ? (
        <Card className="items-center p-8 text-center">
          <p className="text-sm font-medium">Sin serie para esta combinación</p>
          <p className="max-w-md text-xs text-muted-foreground">
            La carta necesita los valores observados y esta combinación de sitio y parámetro aún no
            tiene datos en la demostración. Elige otro sitio o parámetro.
          </p>
        </Card>
      ) : null}

      {chartQuery.data && series ? (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
          <div className="xl:col-span-8">
            <ControlChart
              observations={series.observations}
              individuals={chartQuery.data.individuals}
              movingRange={chartQuery.data.movingRange}
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

