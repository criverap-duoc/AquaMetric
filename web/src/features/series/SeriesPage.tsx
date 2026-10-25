import { Filter, Info } from "lucide-react";
import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { useCatalogMeta, useParameters } from "@/api/catalog";
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
import {
  DEMO_PARAMETER_CODES,
  DEMO_SITES,
  findDemoSeries,
} from "@/features/series/demo-data";
import { formatDateTime } from "@/lib/format";
import type { Observation } from "@/types/api";

/** Range presets of the global filter bar; the value is the width in days. */
const RANGE_PRESETS = {
  "24h": { days: 1, label: "Últimas 24 h" },
  "7d": { days: 7, label: "Últimos 7 días" },
  "30d": { days: 30, label: "Últimos 30 días" },
} as const;

type RangePreset = keyof typeof RANGE_PRESETS;

const DEFAULT_RANGE: RangePreset = "30d";

const MS_PER_DAY = 86_400_000;

function isRangePreset(value: string | null): value is RangePreset {
  return value !== null && value in RANGE_PRESETS;
}

interface FilterPanelProps {
  siteCode: string;
  parameterCode: string;
  range: RangePreset;
  parameterOptions: Array<{ code: string; label: string }>;
  onChange: (patch: { site?: string; param?: string; range?: RangePreset }) => void;
}

/** Site · parameter · range: the same three controls on desktop and inside the mobile Sheet. */
function FilterPanel({
  siteCode,
  parameterCode,
  range,
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
            {DEMO_SITES.map((site) => (
              <SelectItem key={site.code} value={site.code}>
                {site.code}
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


export function SeriesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [isFiltersOpen, setIsFiltersOpen] = useState(false);

  const parametersQuery = useParameters();
  const metaQuery = useCatalogMeta();

  const parametersByCode = useMemo(
    () => new Map((parametersQuery.data ?? []).map((parameter) => [parameter.code, parameter])),
    [parametersQuery.data],
  );

  const parameterOptions = DEMO_PARAMETER_CODES.map((code) => ({
    code,
    label: parametersByCode.get(code)?.nameEs ?? code,
  }));

  const siteCode = searchParams.get("site") ?? DEMO_SITES[0].code;
  const parameterCode = searchParams.get("param") ?? DEMO_PARAMETER_CODES[0];
  const rawRange = searchParams.get("range");
  const range: RangePreset = isRangePreset(rawRange) ? rawRange : DEFAULT_RANGE;

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

    setSearchParams(next, { replace: true });
  };

  const series = findDemoSeries(siteCode, parameterCode);
  const parameter = parametersByCode.get(parameterCode);

  // The demo series are anchored to the instant `demo-data.ts` was built, so the last reading is
  // the reference for "last 24 h". Using it instead of `Date.now()` keeps render pure.
  const referenceTime = useMemo(() => {
    const latest = series?.observations.at(-1);
    return latest ? new Date(latest.analyzedAt).getTime() : 0;
  }, [series]);

  const visibleObservations = useMemo<Observation[]>(() => {
    if (!series || referenceTime === 0) {
      return [];
    }

    const cutoff = referenceTime - RANGE_PRESETS[range].days * MS_PER_DAY;

    return series.observations.filter(
      (observation) => new Date(observation.analyzedAt).getTime() >= cutoff,
    );
  }, [series, range, referenceTime]);

  const trendPoints = useMemo<TrendPoint[]>(
    () =>
      visibleObservations.map((observation) => ({
        timestamp: new Date(observation.analyzedAt),
        value: observation.value,
      })),
    [visibleObservations],
  );

  const unitCode = series?.unitCode ?? "—";
  const decimals = parameter?.decimals ?? series?.decimals ?? 2;
  const parameterName = parameter?.nameEs ?? parameterCode;

  const observationColumns = useMemo(
    () => createObservationColumns(unitCode, decimals),
    [unitCode, decimals],
  );

  const catalogVersion = metaQuery.data?.version ?? "—";
  const source = `${siteCode} · ${parameterName} · datos demo del simulador · catálogo v${catalogVersion} · actualizado ${formatDateTime(new Date())}`;

  const handleRetry = () => {
    void parametersQuery.refetch();
    void metaQuery.refetch();
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
              parameterOptions={parameterOptions}
              onChange={updateFilters}
            />
          </div>
        </SheetContent>
      </Sheet>

      <div className="flex items-start gap-2 rounded-md bg-info-soft p-3 text-info-soft-foreground">
        <Info aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
        <p className="text-xs">
          Datos de demostración del simulador determinista (seed 42). Las series reales se leerán de{" "}
          <span className="font-mono">GET /api/v1/observations</span> cuando exista ese endpoint.
        </p>
      </div>

      {parametersQuery.isError ? (
        <ErrorState error={parametersQuery.error} onRetry={handleRetry} />
      ) : null}

      {parametersQuery.isPending ? <ChartSkeleton /> : null}
      {!parametersQuery.isPending && !parametersQuery.isError ? (
        visibleObservations.length === 0 ? (
          <Card className="items-center p-8 text-center">
            <p className="text-sm font-medium">Sin observaciones en este rango</p>
            <p className="max-w-md text-xs text-muted-foreground">
              Amplía el rango de fechas o elige otro sitio o parámetro.
            </p>
          </Card>
        ) : (
          <>
            {visibleObservations.length < MIN_BASELINE_POINTS ? (
              <div className="flex items-start gap-2 rounded-md bg-info-soft p-3 text-info-soft-foreground">
                <Info aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
                <p className="text-xs">
                  Se requieren al menos {MIN_BASELINE_POINTS} observaciones para estimar la línea
                  base; este rango tiene {visibleObservations.length}. Amplía el rango de fechas.
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
                    {visibleObservations.length}
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
                    data={visibleObservations}
                    caption={`Observaciones de ${parameterName} en ${siteCode}`}
                    emptyMessage="Sin observaciones en este rango."
                  />
                </CardContent>
              </Card>
            </div>
          </>
        )
      ) : null}
    </section>
  );
}


