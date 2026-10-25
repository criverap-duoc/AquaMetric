import { CloudOff, Database, Layers, MapPin } from "lucide-react";
import { useMemo } from "react";
import { Link } from "react-router-dom";

import { useParameters } from "@/api/catalog";
import { usePipelineStatus } from "@/api/pipeline";
import { DataTable } from "@/components/domain/DataTable";
import { ErrorState } from "@/components/domain/ErrorState";
import { StatTile } from "@/components/domain/StatTile";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { createBatchColumns } from "@/features/pipeline/batch-columns";
import { formatDate, formatDateTime, formatUnit } from "@/lib/format";
import type { SiteLastRead } from "@/types/api";

const RECENT_BATCHES = 10;

function timeOnly(value: string): string {
  return formatDate(value, {
    dateStyle: undefined,
    timeStyle: undefined,
    hour: "2-digit",
    minute: "2-digit",
  });
}

function LoadingSkeleton() {
  return (
    <div className="flex flex-col gap-4" aria-busy="true">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }, (_, index) => (
          <Skeleton key={index} className="h-28 w-full" />
        ))}
      </div>
      <Skeleton className="h-64 w-full" />
      <span className="sr-only">Cargando el estado del pipeline…</span>
    </div>
  );
}

/**
 * Pipeline screen: what arrived and when, without pretending the AWS objects exist.
 *
 * `awsDeployed = false` is rendered as an informative banner, not as an error: the demo feeds the
 * API directly and the S3 → Lambda path is optional (ADR-002, ADR-004).
 */
export function PipelinePage() {
  const statusQuery = usePipelineStatus({ limit: RECENT_BATCHES });
  const parametersQuery = useParameters();

  const status = statusQuery.data;
  const batches = status?.recentBatches ?? [];
  const readings: SiteLastRead[] = status?.lastObservationPerSite ?? [];
  const columns = useMemo(() => createBatchColumns(), []);

  const decimalsByCode = new Map(
    (parametersQuery.data ?? []).map((parameter) => [parameter.code, parameter.decimals]),
  );

  const lastBatch = batches[0];
  const acceptedTotal = batches.reduce((total, batch) => total + batch.accepted, 0);
  const duplicatesTotal = batches.reduce((total, batch) => total + batch.duplicates, 0);

  return (
    <section className="flex flex-col gap-4">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Pipeline</h1>
        <p className="text-xs text-muted-foreground">
          Estado de las ingestas recientes y última lectura por sitio.
        </p>
      </header>

      {statusQuery.isError ? (
        <ErrorState error={statusQuery.error} onRetry={() => void statusQuery.refetch()} />
      ) : null}

      {statusQuery.isPending ? <LoadingSkeleton /> : null}

      {status && !status.awsDeployed ? (
        <div className="flex items-start gap-2 rounded-md bg-info-soft p-3 text-info-soft-foreground">
          <CloudOff aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          <p className="text-xs">
            <span className="font-medium">Pipeline AWS no desplegado.</span> La demo funciona con
            ingesta directa a la API; el pipeline S3 → Lambda es opcional (ver ADR-004).
          </p>
        </div>
      ) : null}

      {status ? (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatTile
              label="Lotes recientes"
              value={batches.length}
              icon={Layers}
              hint={`Máximo ${status.limit} registrados`}
            />
            <StatTile
              label="Última ingesta"
              value={lastBatch ? timeOnly(lastBatch.receivedAt) : "—"}
              icon={Database}
              hint={lastBatch ? formatDate(lastBatch.receivedAt) : "Sin ingestas registradas"}
            />
            <StatTile
              label="Sitios con datos"
              value={readings.length}
              icon={MapPin}
              hint="Con al menos una observación"
            />
            <StatTile
              label="Filas aceptadas"
              value={acceptedTotal}
              hint={`${duplicatesTotal} duplicadas descartadas`}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
            <Card className="gap-2 p-4 xl:col-span-8">
              <CardHeader className="p-0">
                <CardTitle>
                  <h2 className="text-base font-semibold">Últimos lotes</h2>
                </CardTitle>
                <CardDescription className="text-xs">
                  Registro de idempotencia: misma clave y mismo contenido responde lo guardado, sin
                  reescribir filas
                </CardDescription>
              </CardHeader>

              <CardContent className="p-0">
                {batches.length === 0 ? (
                  <div className="flex flex-col items-center gap-2 rounded-md border border-dashed border-border px-4 py-10 text-center">
                    <Layers aria-hidden="true" className="size-6 text-muted-foreground" />
                    <p className="text-sm font-medium">Sin ingestas registradas</p>
                    <p className="max-w-sm text-xs text-muted-foreground">
                      Ejecuta <span className="font-mono">scripts/seed_demo.sh</span> (ver README)
                      para cargar los sitios y las series de demostración.
                    </p>
                  </div>
                ) : (
                  <DataTable
                    columns={columns}
                    data={batches}
                    pageSize={25}
                    caption="Lotes de ingesta recientes"
                  />
                )}
              </CardContent>
            </Card>

            <Card className="gap-2 p-4 xl:col-span-4">
              <CardHeader className="p-0">
                <CardTitle>
                  <h2 className="text-base font-semibold">Última lectura por sitio</h2>
                </CardTitle>
                <CardDescription className="text-xs">
                  El dato más reciente de cada sitio, con su parámetro y unidad
                </CardDescription>
              </CardHeader>

              <CardContent className="p-0">
                {readings.length === 0 ? (
                  <p className="rounded-md border border-dashed border-border px-4 py-8 text-center text-xs text-muted-foreground">
                    Todavía no hay observaciones almacenadas.
                  </p>
                ) : (
                  <ul className="flex flex-col divide-y divide-border">
                    {readings.map((reading) => (
                      <li
                        key={reading.siteId}
                        className="flex flex-col gap-1 py-2 first:pt-0 last:pb-0"
                      >
                        <div className="flex items-baseline justify-between gap-2">
                          <Link
                            to={`/series?site=${reading.siteCode}`}
                            className="font-mono text-xs underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:outline-none"
                          >
                            {reading.siteCode}
                          </Link>
                          <span className="font-mono text-xs tabular-nums">
                            {reading.value === null
                              ? "censurado"
                              : formatUnit(
                                  reading.value,
                                  reading.unitCode,
                                  decimalsByCode.get(reading.parameterCode) ?? 2,
                                )}
                          </span>
                        </div>
                        <div className="flex items-baseline justify-between gap-2 text-xs text-muted-foreground">
                          <span className="font-mono">{reading.parameterCode}</span>
                          <span className="font-mono tabular-nums">
                            {formatDateTime(reading.analyzedAt)}
                          </span>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      ) : null}
    </section>
  );
}


