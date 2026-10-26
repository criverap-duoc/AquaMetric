import { Filter, Info } from "lucide-react";
import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { useCatalogMeta, useParameters } from "@/api/catalog";
import { useObservations, useObservationsAggregate } from "@/api/observations";
import { useSites } from "@/api/sites";
import { MIN_BASELINE_POINTS } from "@/api/spc";
import { DataTable } from "@/components/domain/DataTable";
import { ErrorState } from "@/components/domain/ErrorState";
import { ScatterPlot } from "@/components/domain/ScatterPlot";
import { TrendChart, type TrendPoint } from "@/components/domain/TrendChart";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { createObservationColumns } from "@/features/series/observation-columns";
import { formatDateTime, formatNumber } from "@/lib/format";
import type { ObservationAggregate, ObservationRead } from "@/types/api";

/** Range presets of the global filter bar; the value is the width in days. */
const RANGE_PRESETS = {
  "24h": { days: 1, label: "Últimas 24 h" },
  "7d": { days: 7, label: "Últimos 7 días" },
  "30d": { days: 30, label: "Últimos 30 días" },
} as const;

type RangePreset = keyof typeof RANGE_PRESETS;

const DEFAULT_RANGE: RangePreset = "30d";

const MS_PER_DAY = 86_400_000;

/** Observations the charts load in one request; 30 days of a six-hourly series is 121 points. */
const CHART_POINTS = 500;

/** Rows per page the table can ask the server for. */
const TABLE_PAGE_SIZES = [25, 50, 100, 500] as const;

const DEFAULT_TABLE_PAGE_SIZE = 50;

function isRangePreset(value: string | null): value is RangePreset {
  return value !== null && value in RANGE_PRESETS;
}

interface FilterPanelProps {
  siteCode: string;
  parameterCode: string;
  range: RangePreset;
  siteOptions: Array<{ code: string; label: string }>;
  parameterOptions: Array<{ code: string; label: string }>;
  onChange: (patch: { site?: string; param?: string; range?: RangePreset }) => void;
}

/** Site · parameter · range: the same three controls on desktop and inside the mobile Sheet. */
function FilterPanel({
  siteCode,
  parameterCode,
  range,
  siteOptions,
  parameterOptions,
  onChange,
}: FilterPanelProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <div className="flex flex-col gap-1">
        <label htmlFor="series-site" className="text-xs text-muted-foreground">
          Sitio
        </label>
        <Select value={siteCode} onValueChange={(value) => onChange({ site: value })}>
          <SelectTrigger id="series-site" className="w-full">
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
        <label htmlFor="series-parameter" className="text-xs text-muted-foreground">
          Parámetro
        </label>
        <Select value={parameterCode} onValueChange={(value) => onChange({ param: value })}>
          <SelectTrigger id="series-parameter" className="w-full">
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
        <label htmlFor="series-range" className="text-xs text-muted-foreground">
          Rango de fechas
        </label>
        <Select
          value={range}
          onValueChange={(value) => {
            if (isRangePreset(value)) {
              onChange({ range: value });
            }
          }}
        >
          <SelectTrigger id="series-range" className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(RANGE_PRESETS).map(([preset, { label }]) => (
              <SelectItem key={preset} value={preset}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}

function ChartSkeleton() {
  return (
    <div className="space-y-2" aria-busy="true">
      <Skeleton className="h-64 w-full" />
      <Skeleton className="h-3 w-2/3" />
      <span className="sr-only">Cargando serie…</span>
    </div>
  );
}

/** Mean of the window, or «—» when every value in it was censored (`< LOQ`). */
function formatWindowMean(
  summary: ObservationAggregate | undefined,
  decimals: number,
  unitCode: string,
): string {
  if (!summary || summary.meanValue === null) {
    return "—";
  }

  return `${formatNumber(summary.meanValue, decimals)} ${unitCode}`;
}

/** «mín–máx unidad», or «—» for the same reason as the mean. */
function formatWindowRange(
  summary: ObservationAggregate | undefined,
  decimals: number,
  unitCode: string,
): string {
  if (!summary || summary.minValue === null || summary.maxValue === null) {
    return "—";
  }

  const minimum = formatNumber(summary.minValue, decimals);
  const maximum = formatNumber(summary.maxValue, decimals);

  return `${minimum}–${maximum} ${unitCode}`;
}


export function SeriesPage() {
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
  // The uuid travels with the code because the SPC endpoints key their series by `siteId`.
  const siteOptions = useMemo(
    () =>
      (sitesQuery.data?.data ?? []).map((row) => ({
        code: row.code,
        id: row.id,
        label: `${row.code} · ${row.name}`,
      })),
    [sitesQuery.data],
  );

  // Every catalog parameter is offered, not only the ones with data: «este sitio no mide TURB» is
  // information the analyst needs, and the empty state says it without pretending an error.
  const parameterOptions = useMemo(
    () =>
      (parametersQuery.data ?? []).map((parameter) => ({
        code: parameter.code,
        label: parameter.nameEs,
      })),
    [parametersQuery.data],
  );

  const requestedSite = searchParams.get("site");
  const site = siteOptions.find((option) => option.code === requestedSite) ?? siteOptions[0] ?? null;
  const siteCode = site?.code ?? "";
  const parameterCode =
    parameterOptions.find((option) => option.code === searchParams.get("param"))?.code ??
    parameterOptions[0]?.code ??
    "";
  const rawRange = searchParams.get("range");
  const range: RangePreset = isRangePreset(rawRange) ? rawRange : DEFAULT_RANGE;

  const requestedPageSize = Number(searchParams.get("pageSize"));
  const tablePage = Math.max(1, Number(searchParams.get("page") ?? 1) || 1);
  const tablePageSize = (TABLE_PAGE_SIZES as readonly number[]).includes(requestedPageSize)
    ? requestedPageSize
    : DEFAULT_TABLE_PAGE_SIZE;

  // The window ends «now», so a seed generated with a future start instant is not plotted as if
  // the sensor had reported tomorrow (`GET /pipeline/status` applies the same rule).
  const window = useMemo(() => {
    const to = new Date();
    const from = new Date(to.getTime() - RANGE_PRESETS[range].days * MS_PER_DAY);

    return { from: from.toISOString(), to: to.toISOString() };
  }, [range]);

  // Filters live in the URL so a regulator can share the exact view (04 §4).
  const updateFilters = (patch: { site?: string; param?: string; range?: RangePreset }) => {
    const next = new URLSearchParams(searchParams);

    if (patch.site) {
      next.set("site", patch.site);
    }

    if (patch.param) {
      next.set("param", patch.param);
    }

    if (patch.range) {
      next.set("range", patch.range);
    }

    // Another filter is another series: page 2 of the previous one means nothing.
    if (patch.site || patch.param || patch.range) {
      next.delete("page");
    }

    setSearchParams(next, { replace: true });
  };

  /** Server pagination: the table asks for a page, the footer prints the totals of the API. */
  const updatePage = (page: number, pageSize: number) => {
    const next = new URLSearchParams(searchParams);
    next.set("page", String(page));
    next.set("pageSize", String(pageSize));
    setSearchParams(next, { replace: true });
  };

  // Two reads of the same window: the charts want all of it, the table one page. TanStack Query
  // dedupes them when the analyst leaves the table at 500 rows on page 1.
  const chartQuery = useObservations({
    siteId: site?.id,
    parameterCode,
    from: window.from,
    to: window.to,
    page: 1,
    pageSize: CHART_POINTS,
    order: "desc",
  });
  const tableQuery = useObservations({
    siteId: site?.id,
    parameterCode,
    from: window.from,
    to: window.to,
    page: tablePage,
    pageSize: tablePageSize,
    order: "desc",
  });
  const aggregateQuery = useObservationsAggregate({
    siteId: site?.id,
    parameterCode,
    from: window.from,
    to: window.to,
  });

  const parameter = parametersByCode.get(parameterCode);

  // The endpoint answers newest first (the table order); the charts need the series chronological.
  const chartObservations = useMemo<ObservationRead[]>(
    () => [...(chartQuery.data?.data ?? [])].reverse(),
    [chartQuery.data],
  );
  const tableObservations = tableQuery.data?.data ?? [];
  const totalObservations = tableQuery.data?.meta.total ?? 0;
  const summary = aggregateQuery.data;

  const trendPoints = useMemo<TrendPoint[]>(
    () =>
      chartObservations.map((observation) => ({
        timestamp: new Date(observation.analyzedAt),
        value: observation.value,
      })),
    [chartObservations],
  );

  const unitCode = parameter?.canonicalUnitCode ?? chartObservations[0]?.unitCode ?? "—";
  const decimals = parameter?.decimals ?? 2;
  const parameterName = parameter?.nameEs ?? parameterCode;

  const observationColumns = useMemo(
    () => createObservationColumns(unitCode, decimals),
    [unitCode, decimals],
  );

  const catalogVersion = metaQuery.data?.version ?? "—";
  const updatedAt = chartQuery.dataUpdatedAt > 0 ? new Date(chartQuery.dataUpdatedAt) : new Date();
  const source = `${siteCode} · ${parameterName} · GET /observations · catálogo v${catalogVersion} · actualizado ${formatDateTime(updatedAt)}`;

  const isPending = parametersQuery.isPending || sitesQuery.isPending || chartQuery.isPending;
  const error = parametersQuery.error ?? sitesQuery.error ?? chartQuery.error;

  const handleRetry = () => {
    void parametersQuery.refetch();
    void sitesQuery.refetch();
    void chartQuery.refetch();
    void tableQuery.refetch();
    void aggregateQuery.refetch();
  };

  return (
    <section className="flex flex-col gap-4">
      <header className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Series</h1>
          <p className="text-xs text-muted-foreground">
            Serie temporal y dispersión de un parámetro en un sitio.
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
          range={range}
          siteOptions={siteOptions}
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
              range={range}
              siteOptions={siteOptions}
              parameterOptions={parameterOptions}
              onChange={updateFilters}
            />
          </div>
        </SheetContent>
      </Sheet>

      <div className="flex items-start gap-2 rounded-md bg-info-soft p-3 text-info-soft-foreground">
        <Info aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
        <p className="text-xs">
          Serie leída de <span className="font-mono">GET /api/v1/observations</span> sobre una
          ventana que termina ahora. Los resultados censurados (<span className="font-mono">&lt; LOQ</span>
          ) se muestran con su operador y nunca se estiman.
        </p>
      </div>

      {error ? <ErrorState error={error} onRetry={handleRetry} /> : null}

      {!error && isPending ? <ChartSkeleton /> : null}

      {!error && !isPending && siteOptions.length === 0 ? (
        <Card className="items-center p-8 text-center">
          <p className="text-sm font-medium">Todavía no hay sitios registrados</p>
          <p className="max-w-md text-xs text-muted-foreground">
            Carga un lote con el simulador y la serie aparecerá aquí.
          </p>
        </Card>
      ) : null}

      {!error && !isPending && siteOptions.length > 0 && totalObservations === 0 ? (
        <Card className="items-center p-8 text-center">
          <p className="text-sm font-medium">Sin observaciones en este rango</p>
          <p className="max-w-md text-xs text-muted-foreground">
            Amplía el rango de fechas o elige otro sitio o parámetro.
          </p>
        </Card>
      ) : null}

      {!error && !isPending && siteOptions.length > 0 && totalObservations > 0 ? (
        <>
          {summary ? (
            <p className="text-xs text-muted-foreground">
              <span className="font-mono tabular-nums">{formatNumber(summary.count, 0)}</span>{" "}
              observaciones en el rango
              {summary.censoredCount > 0
                ? ` · ${formatNumber(summary.censoredCount, 0)} censuradas (< LOQ)`
                : ""}{" "}
              · media {formatWindowMean(summary, decimals, unitCode)} · rango{" "}
              {formatWindowRange(summary, decimals, unitCode)}
            </p>
          ) : null}

          {summary && summary.count < MIN_BASELINE_POINTS ? (
            <div className="flex items-start gap-2 rounded-md bg-info-soft p-3 text-info-soft-foreground">
              <Info aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
              <p className="text-xs">
                Se requieren al menos {MIN_BASELINE_POINTS} observaciones para estimar la línea
                base; este rango tiene {summary.count}. Amplía el rango de fechas.
              </p>
            </div>
          ) : null}

            <div className="grid grid-cols-1 gap-4 md:grid-cols-6 xl:grid-cols-12">
              <Card className="gap-2 p-4 pb-2 md:col-span-6 xl:col-span-8">
                <CardHeader className="p-0">
                  <CardTitle>
                    <h2 className="text-base font-semibold">Tendencia</h2>
                  </CardTitle>
                  <CardDescription className="text-xs">
                    {parameterName} · {RANGE_PRESETS[range].label} · n ={" "}
                    {formatNumber(chartObservations.length, 0)}
                    {summary && summary.count > chartObservations.length
                      ? ` (los ${CHART_POINTS} más recientes de ${formatNumber(summary.count, 0)})`
                      : ""}
                  </CardDescription>
                </CardHeader>
                <CardContent className="p-0">
                  <TrendChart
                    data={trendPoints}
                    unitCode={unitCode}
                    parameterName={parameterName}
                    decimals={decimals}
                    source={source}
                  />
                </CardContent>
              </Card>

              <Card className="gap-2 p-4 pb-2 md:col-span-6 xl:col-span-4">
                <CardHeader className="p-0">
                  <CardTitle>
                    <h2 className="text-base font-semibold">Dispersión</h2>
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Recta de mínimos cuadrados sobre las mismas observaciones
                  </CardDescription>
                </CardHeader>
                <CardContent className="p-0">
                  <ScatterPlot
                    data={trendPoints}
                    unitCode={unitCode}
                    parameterName={parameterName}
                    decimals={decimals}
                    source={source}
                  />
                </CardContent>
              </Card>

              <Card className="gap-2 p-4 md:col-span-6 xl:col-span-12">
                <CardHeader className="p-0">
                  <CardTitle>
                    <h2 className="text-base font-semibold">Observaciones</h2>
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Ordena por cualquier columna · los valores censurados se muestran con el
                    operador y sin estimar
                  </CardDescription>
                </CardHeader>
                <CardContent className="p-0">
                  <DataTable
                    columns={observationColumns}
                    data={tableObservations}
                    isLoading={tableQuery.isPending}
                    caption={`Observaciones de ${parameterName} en ${siteCode}`}
                    emptyMessage="Sin observaciones en este rango."
                    serverPagination={{
                      page: tablePage,
                      pageSize: tablePageSize,
                      total: totalObservations,
                      pageSizeOptions: TABLE_PAGE_SIZES,
                      onPageChange: (page) => updatePage(page, tablePageSize),
                      onPageSizeChange: (pageSize) => updatePage(1, pageSize),
                    }}
                  />
                </CardContent>
              </Card>
            </div>
        </>
      ) : null}
    </section>
  );
}


