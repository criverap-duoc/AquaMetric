import { Activity, AlertTriangle, CloudOff, Database, MapPin, ShieldCheck } from "lucide-react";
import { useMemo } from "react";
import { Link } from "react-router-dom";

import { useCatalogMeta, useParameters } from "@/api/catalog";
import { rankSignals, summarizeSeries, useSeriesCharts, type SeriesKey } from "@/api/observations";
import { usePipelineStatus } from "@/api/pipeline";
import { useSites } from "@/api/sites";
import { ErrorState } from "@/components/domain/ErrorState";
import { ProcessStatusBadge } from "@/components/domain/ProcessStatusBadge";
import { StatTile } from "@/components/domain/StatTile";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDateTime, formatNumber, formatPastAge, formatRelativeTime } from "@/lib/format";

/** `GET /pipeline/status` caps `limit` at 50: every batch of the demo fits in one page. */
const BATCH_WINDOW = 50;

const VISIBLE_ALERTS = 5;

/** Catalog states the dashboard shows as a badge; any other status is printed as it comes. */
const CATALOG_STATUS_BADGES: Record<string, { label: string; className: string }> = {
  validated: { label: "Validado", className: "bg-success-soft text-success-soft-foreground" },
  "draft-verified": {
    label: "Pendiente de validación",
    className: "bg-warning-soft text-warning-soft-foreground",
  },
};

const LINK_CLASS =
  "font-mono text-xs underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:outline-none";

/** Newest of a list of ISO timestamps, or `null` when there is nothing to compare. */
function newestTimestamp(values: string[]): string | null {
  const newest = values.reduce((latest, value) => {
    const timestamp = new Date(value).getTime();

    return Number.isNaN(timestamp) || timestamp <= latest ? latest : timestamp;
  }, 0);

  return newest > 0 ? new Date(newest).toISOString() : null;
}

function LoadingSkeleton() {
  return (
    <div className="flex flex-col gap-4" aria-busy="true">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }, (_, index) => (
          <Skeleton key={index} className="h-28 w-full" />
        ))}
      </div>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
        <Skeleton className="h-72 w-full xl:col-span-8" />
        <Skeleton className="h-72 w-full xl:col-span-4" />
      </div>
      <span className="sr-only">Cargando el resumen de la red de monitoreo…</span>
    </div>
  );
}

/**
 * Dashboard of the MVP: four KPIs, the signals the control charts found and the state of the
 * ingest pipeline.
 *
 * Every number is read from the API. What the API cannot answer yet (the screening of every
 * observation) is shown as «—» with the screen that does answer it, instead of a made-up figure.
 */
export function ResumenPage() {
  const metaQuery = useCatalogMeta();
  const sitesQuery = useSites({ page: 1, pageSize: 100 });
  const parametersQuery = useParameters();
  const statusQuery = usePipelineStatus({ limit: BATCH_WINDOW });

  const sites = useMemo(() => sitesQuery.data?.data ?? [], [sitesQuery.data]);
  const parameters = useMemo(() => parametersQuery.data ?? [], [parametersQuery.data]);

  // One chart per (site, parameter). `useSeriesCharts` drops the pairs without observations, so
  // «de Y series» is the number the API could answer for, not a hardcoded list.
  const pairs = useMemo<SeriesKey[]>(
    () =>
      sites.flatMap((site) =>
        parameters.map((parameter) => ({
          siteId: site.id,
          siteCode: site.code,
          parameterCode: parameter.code,
        })),
      ),
    [sites, parameters],
  );

  const charts = useSeriesCharts(pairs);
  const summary = useMemo(() => summarizeSeries(charts.series), [charts.series]);
  const alerts = useMemo(() => rankSignals(charts.series, VISIBLE_ALERTS), [charts.series]);

  const status = statusQuery.data;
  const batches = useMemo(() => status?.recentBatches ?? [], [status]);
  const readings = useMemo(() => status?.lastObservationPerSite ?? [], [status]);

  // The endpoint reports batches, not row counts: summing what each batch accepted is the only
  // real total the API can give today (an aggregation endpoint would be backend work).
  const ingested = useMemo(
    () => batches.reduce((total, batch) => total + batch.accepted, 0),
    [batches],
  );

  const lastReadingAt = useMemo(
    () => newestTimestamp(readings.map((reading) => reading.analyzedAt)),
    [readings],
  );

  // A timestamp in the future means the simulator clock ran ahead of the server; the absolute
  // date is then the only honest label, because «dentro de 29 días» is noise on a dashboard.
  const lastReadingAge = lastReadingAt ? formatPastAge(lastReadingAt) : null;

  const lastBatchAt = batches[0]?.receivedAt ?? null;
  const activeSites = sites.filter((site) => site.isActive).length;
  const meta = metaQuery.data;
  const catalogBadge = meta ? CATALOG_STATUS_BADGES[meta.status] : undefined;

  const isBlocked = sitesQuery.isError || statusQuery.isError;
  const isLoading = sitesQuery.isPending || statusQuery.isPending || charts.isPending;

  const retryAll = () => {
    void sitesQuery.refetch();
    void statusQuery.refetch();
    void metaQuery.refetch();
  };

  return (
    <section className="flex flex-col gap-4">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Resumen</h1>
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
          <span>Catálogo v{meta?.version ?? "—"}</span>
          {catalogBadge ? (
            <Badge className={`rounded-sm ${catalogBadge.className}`}>{catalogBadge.label}</Badge>
          ) : null}
          <span aria-hidden="true">·</span>
          <span>
            Última lectura{" "}
            <span className="font-mono tabular-nums">
              {lastReadingAt ? formatDateTime(lastReadingAt) : "—"}
            </span>
            {lastReadingAge ? ` (${lastReadingAge})` : ""}
          </span>
        </div>
      </header>

      <div className="flex items-start gap-2 rounded-md bg-warning-soft p-3 text-warning-soft-foreground">
        <AlertTriangle aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
        <p className="text-xs">
          Screening referencial, no dictamen de cumplimiento legal: compara cada observación con el
          rango de referencia del catálogo y no evalúa la norma completa. Ver{" "}
          <span className="font-mono">docs/adr/010-screening-not-compliance.md</span>.
        </p>
      </div>

      {isBlocked ? (
        <ErrorState
          error={sitesQuery.error ?? statusQuery.error}
          onRetry={retryAll}
          title="No se pudo cargar el resumen."
        />
      ) : null}

      {charts.failedCount > 0 ? (
        <div className="flex items-start gap-2 rounded-md bg-warning-soft p-3 text-warning-soft-foreground">
          <AlertTriangle aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          <p className="text-xs">
            {charts.failedCount} de {pairs.length} series no se pudieron calcular; las cifras de
            abajo suman solo las que respondieron.
          </p>
        </div>
      ) : null}

      {isLoading ? <LoadingSkeleton /> : null}

      {!isLoading && !isBlocked && sites.length === 0 ? (
        <Card className="items-center gap-2 p-8 text-center">
          <p className="text-sm font-medium">Sin datos cargados</p>
          <p className="max-w-md text-xs text-muted-foreground">
            Ejecuta <span className="font-mono">scripts/seed_demo.sh</span> con la API arriba y el
            catálogo sincronizado: escribe 4 sitios × 5 parámetros × 30 días (ver README).
          </p>
        </Card>
      ) : null}

      {!isLoading && !isBlocked && sites.length > 0 ? (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatTile
              label="Observaciones ingeridas"
              value={formatNumber(ingested, 0)}
              unit="lecturas"
              hint={`${formatNumber(batches.length, 0)} lotes aceptados · simulador de 30 días`}
              icon={Database}
            />
            <StatTile
              label="Sitios activos"
              value={formatNumber(activeSites, 0)}
              unit={`de ${formatNumber(sites.length, 0)}`}
              hint="Sitios SIM-* del simulador de muestreo"
              icon={MapPin}
            />
            <StatTile
              label="Series con señales"
              value={formatNumber(summary.seriesWithSignals, 0)}
              unit={`de ${formatNumber(summary.totalSeries, 0)}`}
              hint="Reglas R1–R5 sobre la ventana de monitoreo (línea base de 20 puntos)"
              icon={Activity}
              status={summary.seriesWithSignals > 0 ? "warning" : "normal"}
            />
            <StatTile
              label="Fuera de rango referencial"
              value="—"
              hint="Ver /screening para evaluar una observación contra el catálogo"
              icon={ShieldCheck}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-6 xl:grid-cols-12">
            <Card className="gap-2 p-4 md:col-span-6 xl:col-span-8">
              <CardHeader className="p-0">
                <CardTitle>
                  <h2 className="text-base font-semibold">Últimas alertas</h2>
                </CardTitle>
                <CardDescription className="text-xs">
                  La señal más fuerte de cada serie, según las reglas R1–R5 de la ventana de
                  monitoreo
                </CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                {alerts.length === 0 ? (
                  <p className="rounded-md border border-dashed border-border px-4 py-8 text-center text-xs text-muted-foreground">
                    Ninguna serie tiene señales en la ventana de monitoreo: los límites de control
                    de la línea base siguen explicando la variación del proceso.
                  </p>
                ) : (
                  <ul className="flex flex-col divide-y divide-border">
                    {alerts.map((alert) => (
                      <li
                        key={alert.id}
                        className="flex flex-col gap-1 py-2 first:pt-0 last:pb-0"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <Link
                            to={`/control?site=${encodeURIComponent(alert.siteCode)}&param=${encodeURIComponent(alert.parameterCode)}`}
                            className={LINK_CLASS}
                          >
                            {alert.siteCode} · {alert.parameterCode}
                          </Link>
                          <ProcessStatusBadge status={alert.severity} />
                        </div>
                        <p className="text-xs">
                          <span className="rounded-sm bg-destructive-soft px-1 py-0.5 font-mono font-medium text-destructive-soft-foreground">
                            {alert.rule}
                          </span>{" "}
                          {alert.description}
                        </p>
                      </li>
                    ))}
                  </ul>
                )}
                <p className="pt-3 text-xs text-muted-foreground">
                  La carta de control (ver{" "}
                  <Link to="/control" className="underline-offset-4 hover:underline">
                    /control
                  </Link>
                  ) calcula las reglas R1–R5 sobre los datos reales. Un punto fuera de control es un
                  cambio del proceso, no un incumplimiento normativo.
                </p>
              </CardContent>
            </Card>

            <Card className="gap-2 p-4 md:col-span-6 xl:col-span-4">
              <CardHeader className="p-0">
                <CardTitle>
                  <h2 className="text-base font-semibold">Estado del pipeline</h2>
                </CardTitle>
                <CardDescription className="text-xs">
                  Ingesta de lecturas del simulador
                </CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-3 p-0">
                {status?.awsDeployed ? (
                  <div className="flex flex-col items-center gap-2 rounded-md bg-success-soft p-4 text-center text-success-soft-foreground">
                    <Database aria-hidden="true" className="size-6" />
                    <p className="text-sm font-medium">Pipeline AWS desplegado</p>
                    <p className="text-xs">
                      Las lecturas del simulador también entran por S3 → Lambda → API, con el mismo
                      camino de escritura.
                    </p>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-2 rounded-md bg-info-soft p-4 text-center text-info-soft-foreground">
                    <CloudOff aria-hidden="true" className="size-6" />
                    <p className="text-sm font-medium">Pipeline AWS no desplegado</p>
                    <p className="text-xs">
                      El recorrido S3 → Lambda → API está documentado con SAM y se activa en la fase
                      G. La demo carga los datos por ingesta directa a la API (ADR-002 y ADR-004).
                    </p>
                  </div>
                )}

                <dl className="flex flex-col gap-1.5 text-xs">
                  <div className="flex items-baseline justify-between gap-2">
                    <dt className="text-muted-foreground">Última ingesta</dt>
                    <dd className="font-mono tabular-nums">
                      {lastBatchAt ? formatRelativeTime(lastBatchAt) : "—"}
                    </dd>
                  </div>
                  <div className="flex items-baseline justify-between gap-2">
                    <dt className="text-muted-foreground">Lotes registrados</dt>
                    <dd className="font-mono tabular-nums">{formatNumber(batches.length, 0)}</dd>
                  </div>
                  <div className="flex items-baseline justify-between gap-2">
                    <dt className="text-muted-foreground">Lecturas aceptadas</dt>
                    <dd className="font-mono tabular-nums">{formatNumber(ingested, 0)}</dd>
                  </div>
                  <div className="flex items-baseline justify-between gap-2">
                    <dt className="text-muted-foreground">Duplicadas descartadas</dt>
                    <dd className="font-mono tabular-nums">
                      {formatNumber(
                        batches.reduce((total, batch) => total + batch.duplicates, 0),
                        0,
                      )}
                    </dd>
                  </div>
                </dl>

                <Link
                  to="/pipeline"
                  className="text-xs underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:outline-none"
                >
                  Ver el detalle de las ingestas
                </Link>
              </CardContent>
            </Card>

          </div>
        </>
      ) : null}

    </section>
  );
}

