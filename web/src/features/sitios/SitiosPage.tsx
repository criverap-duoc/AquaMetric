import { MapPin } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DEMO_SITES } from "@/features/series/demo-data";
import type { WaterBodyType } from "@/types/api";

const WATER_BODY_LABELS: Record<WaterBodyType, string> = {
  river: "Río",
  lake: "Lago",
  estuary: "Estuario",
  groundwater: "Agua subterránea",
  effluent: "Efluente",
  drinking: "Agua potable",
};

/**
 * Sites screen.
 *
 * `GET /sites` is not published yet (Fase F), so the list below is the fixed set of `SIM-*`
 * sites the simulator writes; the detail view arrives with the endpoint.
 */
export function SitiosPage() {
  return (
    <section className="flex flex-col gap-4">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Sitios</h1>
        <p className="text-xs text-muted-foreground">
          Sitios de monitoreo disponibles. Los valores se muestran en UTC y se leen en
          America/Santiago.
        </p>
      </header>

      <div className="flex items-start gap-2 rounded-md bg-info-soft p-3 text-info-soft-foreground">
        <MapPin aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
        <p className="text-xs">
          La lista completa llegará con <span className="font-mono">GET /api/v1/sites</span> (Fase
          F). Mientras tanto se muestran los sitios del simulador que alimentan la demostración.
        </p>
      </div>

      {DEMO_SITES.length === 0 ? (
        <Card className="items-center p-8 text-center">
          <MapPin aria-hidden="true" className="size-6 text-muted-foreground" />
          <p className="text-sm font-medium">Aún no hay sitios cargados</p>
          <p className="max-w-md text-xs text-muted-foreground">
            Ejecuta <span className="font-mono">scripts/seed_demo.sh</span> para cargar los datos de
            demostración y luego revisa las series.
          </p>
          <Button asChild variant="outline" size="sm">
            <Link to="/series">Ir a Series</Link>
          </Button>
        </Card>
      ) : (
        <ul className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {DEMO_SITES.map((site) => (
            <li key={site.id}>
              <Card className="h-full gap-2 p-4">
                <CardHeader className="p-0">
                  <CardTitle>
                    <h2 className="font-mono text-sm font-semibold">{site.code}</h2>
                  </CardTitle>
                  <p className="text-sm">{site.name}</p>
                </CardHeader>
                <CardContent className="flex flex-col gap-2 p-0">
                  <p className="text-xs text-muted-foreground">
                    {WATER_BODY_LABELS[site.waterBodyType]}
                  </p>
                  <Button asChild variant="ghost" size="sm" className="self-start">
                    <Link to={`/series?site=${site.code}`}>Ver series</Link>
                  </Button>
                </CardContent>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
