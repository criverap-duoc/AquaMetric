import { Info } from "lucide-react";
import { useMemo, useState } from "react";

import { useCatalogMeta, useLimits, useParameters, useUnits } from "@/api/catalog";
import { DataTable } from "@/components/domain/DataTable";
import { ErrorState } from "@/components/domain/ErrorState";
import { LimitBadge } from "@/components/domain/LimitBadge";
import { createLimitColumns } from "@/components/domain/limit-columns";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { createParameterColumns } from "@/features/ajustes/parameter-columns";
import { createUnitColumns } from "@/features/ajustes/unit-columns";
import { formatDateTime } from "@/lib/format";

/** How much of the bundle hash the screen shows before the ellipsis. */
const SHA_PREVIEW = 16;

type LimitStatusFilter = "all" | "validated" | "draft-verified";

function MetaSkeleton() {
  return (
    <Card className="gap-3 p-4" aria-busy="true">
      <Skeleton className="h-5 w-40" />
      <Skeleton className="h-16 w-full" />
      <span className="sr-only">Cargando la procedencia del catálogo…</span>
    </Card>
  );
}

/**
 * Settings screen: the catalog the whole app depends on, in read-only mode.
 *
 * Nothing here can be edited — the catalog is a synchronized copy of TerraPlan's (ADR-005) — and
 * every row says whether the chemist has signed it. A `draft-verified` value is shown, labelled
 * «Pendiente de validación», and never used to claim compliance (ADR-010).
 */
export function AjustesPage() {
  const metaQuery = useCatalogMeta();
  const parametersQuery = useParameters();
  const unitsQuery = useUnits();

  const [limitStatus, setLimitStatus] = useState<LimitStatusFilter>("all");

  const limitsQuery = useLimits(
    limitStatus === "all" ? {} : { status: limitStatus },
  );

  const parameters = useMemo(() => parametersQuery.data ?? [], [parametersQuery.data]);
  const units = unitsQuery.data ?? [];
  const limits = limitsQuery.data?.data ?? [];

  const parameterColumns = useMemo(() => createParameterColumns(), []);
  const unitColumns = useMemo(() => createUnitColumns(), []);
  const limitColumns = useMemo(() => createLimitColumns(parameters), [parameters]);

  const meta = metaQuery.data;

  return (
    <section className="flex flex-col gap-4">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Ajustes</h1>
        <p className="text-xs text-muted-foreground">
          Catálogo compartido con TerraPlan (fuente de verdad). Solo lectura.
        </p>
      </header>

      {metaQuery.isError ? (
        <ErrorState error={metaQuery.error} onRetry={() => void metaQuery.refetch()} />
      ) : null}

      {metaQuery.isPending ? <MetaSkeleton /> : null}

      {meta ? (
        <Card className="gap-2 p-4">
          <CardHeader className="p-0">
            <CardTitle>
              <h2 className="text-base font-semibold">Catálogo</h2>
            </CardTitle>
            <CardDescription className="text-xs">
              Versión, huella del paquete y estado de la firma del químico
            </CardDescription>
          </CardHeader>

          <CardContent className="grid grid-cols-1 gap-3 p-0 text-xs sm:grid-cols-2 xl:grid-cols-4">
            <div className="flex flex-col gap-0.5">
              <span className="text-muted-foreground">Versión</span>
              <span className="font-mono">{meta.version}</span>
            </div>
            <div className="flex flex-col gap-0.5">
              <span className="text-muted-foreground">sha256</span>
              <span className="font-mono break-all">
                {meta.sha256.slice(0, SHA_PREVIEW)}…
              </span>
            </div>
            <div className="flex flex-col gap-0.5">
              <span className="text-muted-foreground">Generado</span>
              <span className="font-mono tabular-nums">{formatDateTime(meta.generatedAt)}</span>
            </div>
            <div className="flex flex-col gap-0.5">
              <span className="text-muted-foreground">Firma del químico</span>
              <LimitBadge status={meta.status} />
              <span className="text-muted-foreground">
                {meta.validatedBy
                  ? `${meta.validatedBy} · ${meta.validatedAt ? formatDateTime(meta.validatedAt) : "—"}`
                  : "Sin firma registrada"}
              </span>
            </div>
          </CardContent>
        </Card>
      ) : null}

      <Tabs defaultValue="parameters" className="gap-3">
        <TabsList>
          <TabsTrigger value="parameters">Parámetros</TabsTrigger>
          <TabsTrigger value="units">Unidades</TabsTrigger>
          <TabsTrigger value="limits">Límites</TabsTrigger>
        </TabsList>

        <TabsContent value="parameters">
          <Card className="gap-2 p-4">
            <CardHeader className="p-0">
              <CardTitle>
                <h2 className="text-base font-semibold">Parámetros</h2>
              </CardTitle>
              <CardDescription className="text-xs">
                Unidad canónica y decimales de presentación de cada parámetro
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {parametersQuery.isError ? (
                <ErrorState
                  error={parametersQuery.error}
                  onRetry={() => void parametersQuery.refetch()}
                />
              ) : (
                <DataTable
                  columns={parameterColumns}
                  data={parameters}
                  isLoading={parametersQuery.isPending}
                  caption="Parámetros del catálogo"
                  emptyMessage="El catálogo no tiene parámetros cargados."
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="units">
          <Card className="gap-2 p-4">
            <CardHeader className="p-0">
              <CardTitle>
                <h2 className="text-base font-semibold">Unidades</h2>
              </CardTitle>
              <CardDescription className="text-xs">
                Factor explícito de conversión a la unidad canónica de cada dimensión
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {unitsQuery.isError ? (
                <ErrorState error={unitsQuery.error} onRetry={() => void unitsQuery.refetch()} />
              ) : (
                <DataTable
                  columns={unitColumns}
                  data={units}
                  isLoading={unitsQuery.isPending}
                  caption="Unidades del catálogo"
                  emptyMessage="El catálogo no tiene unidades cargadas."
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="limits">
          <Card className="gap-2 p-4">
            <CardHeader className="p-0">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <CardTitle>
                    <h2 className="text-base font-semibold">Límites</h2>
                  </CardTitle>
                  <CardDescription className="text-xs">
                    {limitsQuery.data
                      ? `${limitsQuery.data.meta.total} límites · ${limitsQuery.data.meta.validatedCount} validados · ${limitsQuery.data.meta.draftCount} pendientes`
                      : "Rangos de referencia publicados por cada regulación"}
                  </CardDescription>
                </div>

                <div className="flex flex-col gap-1">
                  <label htmlFor="limits-status" className="text-xs text-muted-foreground">
                    Estado
                  </label>
                  <Select
                    value={limitStatus}
                    onValueChange={(value) => setLimitStatus(value as LimitStatusFilter)}
                  >
                    <SelectTrigger id="limits-status" className="w-52">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Todos</SelectItem>
                      <SelectItem value="validated">Validados</SelectItem>
                      <SelectItem value="draft-verified">Pendientes de validación</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardHeader>

            <CardContent className="p-0">
              {limitsQuery.isError ? (
                <ErrorState error={limitsQuery.error} onRetry={() => void limitsQuery.refetch()} />
              ) : (
                <DataTable
                  columns={limitColumns}
                  data={limits}
                  isLoading={limitsQuery.isPending}
                  caption="Límites del catálogo por parámetro y regulación"
                  emptyMessage="No hay límites con ese estado."
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <div className="flex items-start gap-2 rounded-md bg-info-soft p-3 text-info-soft-foreground">
        <Info aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
        <p className="text-xs">
          El catálogo se sincroniza desde TerraPlan con{" "}
          <span className="font-mono">scripts/sync_catalog.py</span> y se verifica por sha256
          (ADR-005). Los valores pendientes los valida el químico. Referencias en el repositorio:{" "}
          <span className="font-mono">docs/glossary.md</span> y{" "}
          <span className="font-mono">docs/adr/010-screening-not-compliance.md</span>.
        </p>
      </div>
    </section>
  );
}


