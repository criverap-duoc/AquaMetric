import { Activity, AlertTriangle, CloudOff, MapPin, ShieldCheck } from "lucide-react";

import { useCatalogMeta } from "@/api/catalog";
import { ErrorState } from "@/components/domain/ErrorState";
import { ProcessStatusBadge, type ProcessStatus } from "@/components/domain/ProcessStatusBadge";
import { ScreeningBadge } from "@/components/domain/ScreeningBadge";
import { StatTile } from "@/components/domain/StatTile";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { DEMO_OVERVIEW, DEMO_SERIES, type EventKind } from "@/features/series/demo-data";
import { formatDate, formatNumber } from "@/lib/format";

interface DemoAlert {
  id: string;
  siteCode: string;
  parameterCode: string;
  event: EventKind;
}

const ALERT_STATUS: Record<EventKind, ProcessStatus> = {
  shift: "out_of_control",
  spike: "out_of_control",
  drift: "warning",
  dropout: "insufficient_data",
  censored: "insufficient_data",
};

const ALERT_TEXT: Record<EventKind, string> = {
  shift: "Salto de nivel: la media del tramo se desplaza varias sigmas.",
  spike: "Pico aislado: una lectura muy por encima del resto de la serie.",
  drift: "Deriva lenta: la serie se aleja de la línea central de forma sostenida.",
  dropout: "Corte de señal: la serie queda con un hueco de seis lecturas.",
  censored: "Valores censurados por debajo del límite de cuantificación.",
};

const VISIBLE_ALERTS = 6;

/** One row per injected anomaly of the demo scenario, so the dashboard has real content. */
function buildDemoAlerts(): DemoAlert[] {
  return DEMO_SERIES.flatMap((series) =>
    series.events.map((event) => ({
      id: `${series.site.code}-${series.parameterCode}-${event}`,
      siteCode: series.site.code,
      parameterCode: series.parameterCode,
      event,
    })),
  ).slice(0, VISIBLE_ALERTS);
}

const DEMO_ALERTS = buildDemoAlerts();

const CATALOG_STATUS_LABELS: Record<string, string> = {
  validated: "Validado por el químico",
  "draft-verified": "Pendiente de validación",
};

/**
 * Dashboard of the MVP: four KPIs, the alerts of the demo scenario and the state of the AWS
 * pipeline. Every number is labelled with its source: the demo series come from the simulator,
 * the catalog from the API.
 */
export function ResumenPage() {
  const metaQuery = useCatalogMeta();
  const meta = metaQuery.data;
  const catalogStatus = meta ? (CATALOG_STATUS_LABELS[meta.status] ?? meta.status) : "—";
  const lastObservation = DEMO_OVERVIEW.lastObservationAt;

  return (
    <section className="flex flex-col gap-4">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Resumen</h1>
        <p className="text-xs text-muted-foreground">
          Catálogo v{meta?.version ?? "—"} · {catalogStatus} · última lectura{" "}
          {lastObservation ? formatDate(lastObservation) : "—"}
        </p>
      </header>

      <div className="flex items-start gap-2 rounded-md bg-warning-soft p-3 text-warning-soft-foreground">
        <AlertTriangle aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
        <p className="text-xs">
          Screening referencial, no dictamen de cumplimiento legal: compara cada observación con el
          rango de referencia del catálogo y no evalúa la norma completa. Ver{" "}
          <span className="font-mono">docs/adr/010-screening-not-compliance.md</span>.
        </p>
      </div>

      {metaQuery.isError ? (
        <ErrorState error={metaQuery.error} onRetry={() => void metaQuery.refetch()} />
      ) : null}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile
          label="Observaciones 24 h"
          value={formatNumber(DEMO_OVERVIEW.observationsLast24h, 0)}
          hint="Datos demo · simulador seed 42"
          icon={Activity}
        />
        <StatTile
          label="Sitios activos"
          value={formatNumber(DEMO_OVERVIEW.siteCount, 0)}
          unit="sitios"
          hint="Sitios SIM-* del simulador"
          icon={MapPin}
        />
        <StatTile
          label="Series con señales"
          value={formatNumber(DEMO_OVERVIEW.seriesWithAnomalies, 0)}
          unit={`de ${DEMO_SERIES.length}`}
          hint="Escenario demo · la carta de control llega en E-1c"
          icon={Activity}
          status="warning"
        />
        <StatTile
          label="Fuera de rango referencial"
          value="—"
          hint="Pendiente: screening por observación (E-1d)"
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
              Eventos conocidos del escenario de demostración
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <ul className="flex flex-col divide-y divide-border">
              {DEMO_ALERTS.map((alert) => (
                <li key={alert.id} className="flex flex-col gap-1 py-2 first:pt-0 last:pb-0">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-mono text-xs text-muted-foreground">
                      {alert.siteCode} · {alert.parameterCode}
                    </span>
                    {alert.event === "censored" ? (
                      <ScreeningBadge
                        flag="not_evaluable"
                        reason="Un valor censurado (< LOQ) no se evalúa: el valor real se desconoce."
                      />
                    ) : (
                      <ProcessStatusBadge status={ALERT_STATUS[alert.event]} />
                    )}
                  </div>
                  <p className="text-xs">{ALERT_TEXT[alert.event]}</p>
                </li>
              ))}
            </ul>
            <p className="pt-3 text-xs text-muted-foreground">
              El estado se deduce del escenario del simulador. La carta de control calculará las
              reglas R1–R5 sobre los datos reales (fase E-1c).
            </p>
          </CardContent>
        </Card>

        <Card className="gap-2 p-4 md:col-span-6 xl:col-span-4">
          <CardHeader className="p-0">
            <CardTitle>
              <h2 className="text-base font-semibold">Estado del pipeline</h2>
            </CardTitle>
            <CardDescription className="text-xs">Ingesta de lecturas del simulador</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col items-center gap-2 p-0 py-6 text-center">
            <CloudOff aria-hidden="true" className="size-6 text-muted-foreground" />
            <p className="text-sm font-medium">Pipeline AWS no desplegado</p>
            <p className="max-w-xs text-xs text-muted-foreground">
              El recorrido S3 → Lambda → API se documenta con SAM y no es necesario para esta
              demostración: los datos entran por ingesta directa a la API (ADR-002 y ADR-004).
            </p>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
