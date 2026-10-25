import { MapPin } from "lucide-react";
import { Link } from "react-router-dom";

import { useSites } from "@/api/sites";
import { ErrorState } from "@/components/domain/ErrorState";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Site, WaterBodyType } from "@/types/api";

const WATER_BODY_LABELS: Record<WaterBodyType, string> = {
  river: "Río",
  lake: "Lago",
  estuary: "Estuario",
  groundwater: "Agua subterránea",
  effluent: "Efluente",
  drinking: "Agua potable",
};

/** The demo has four sites and TerraPlan will add a handful more, so one page is enough. */
const SITES_PAGE_SIZE = 100;

function Coordinate({ axis, value }: { axis: "lat" | "lon"; value: number | null }) {
  const label = axis === "lat" ? "Latitud" : "Longitud";

  return (
    <span className="font-mono text-xs tabular-nums">
      <span className="sr-only">{label}: </span>
      {value === null ? "—" : `${formatNumber(value, 4)}°`}
    </span>
  );
}

function SiteCard({ site }: { site: Site }) {
  return (
    <li>
      <Card className="h-full gap-2 p-4">
        <CardHeader className="p-0">
          <CardTitle>
            <h2 className="font-mono text-sm font-semibold">{site.code}</h2>
          </CardTitle>
          <p className="text-sm">{site.name}</p>
        </CardHeader>

        <CardContent className="flex flex-col gap-2 p-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline">{WATER_BODY_LABELS[site.waterBodyType]}</Badge>
            <Badge
              className={cn(
                "rounded-sm",
                site.isActive
                  ? "bg-success-soft text-success-soft-foreground"
                  : "bg-muted text-muted-foreground",
              )}
            >
              {site.isActive ? "Activo" : "Inactivo"}
            </Badge>
          </div>

          <p className="flex items-center gap-1 text-muted-foreground">
            <MapPin aria-hidden="true" className="size-3 shrink-0" />
            <Coordinate axis="lat" value={site.latitude} />
            <span aria-hidden="true">·</span>
            <Coordinate axis="lon" value={site.longitude} />
          </p>

          <Button asChild variant="ghost" size="sm" className="self-start">
            <Link to={`/series?site=${encodeURIComponent(site.code)}`}>
              Ver series<span className="sr-only"> de {site.code}</span>
            </Link>
          </Button>
        </CardContent>
      </Card>
    </li>
  );
}

/**
 * Sites screen.
 *
 * The list comes from `GET /sites` (the endpoint that also hands out the `siteId` the SPC routes
 * need). Every state is explicit: a blank screen when the demo has not been seeded is the one
 * outcome the analyst cannot debug on their own.
 */
export function SitiosPage() {
  const sitesQuery = useSites({ page: 1, pageSize: SITES_PAGE_SIZE });

  const sites = sitesQuery.data?.data ?? [];
  const total = sitesQuery.data?.meta.total ?? 0;

  return (
    <section className="flex flex-col gap-4">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Sitios</h1>
        <p className="text-xs text-muted-foreground">
          Sitios de monitoreo con datos publicados. Cada tarjeta enlaza a la serie del sitio; los
          valores se muestran en la zona America/Santiago.
        </p>
      </header>

      {sitesQuery.isError ? (
        <ErrorState error={sitesQuery.error} onRetry={() => void sitesQuery.refetch()} />
      ) : null}

      {sitesQuery.isPending ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3" aria-busy="true">
          {Array.from({ length: 6 }, (_, index) => (
            <Skeleton key={index} className="h-40 w-full" />
          ))}
          <span className="sr-only">Cargando los sitios…</span>
        </div>
      ) : null}

      {!sitesQuery.isPending && !sitesQuery.isError && sites.length === 0 ? (
        <Card className="items-center gap-2 border-dashed p-8 text-center">
          <MapPin aria-hidden="true" className="size-6 text-muted-foreground" />
          <p className="text-sm font-medium">Todavía no hay sitios publicados</p>
          <p className="max-w-md text-xs text-muted-foreground">
            Ejecuta <span className="font-mono">./scripts/seed_demo.sh</span> con la API corriendo
            para cargar los 4 sitios × 5 parámetros de la demostración (ver README, «Datos demo»).
          </p>
          <Button asChild variant="outline" size="sm">
            <Link to="/pipeline">Ver estado del pipeline</Link>
          </Button>
        </Card>
      ) : null}

      {sites.length > 0 ? (
        <>
          <ul className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {sites.map((site) => (
              <SiteCard key={site.id} site={site} />
            ))}
          </ul>
          <p className="text-xs text-muted-foreground">
            <span className="font-mono tabular-nums">{formatNumber(total, 0)}</span> sitios · Fuente:{" "}
            <span className="font-mono">GET /api/v1/sites</span>
          </p>
        </>
      ) : null}
    </section>
  );
}

