import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/layout/AppShell";
import { Skeleton } from "@/components/ui/skeleton";
import { ResumenPage } from "@/features/resumen/ResumenPage";
import { SitiosPage } from "@/features/sitios/SitiosPage";
import { AjustesPage } from "@/pages/AjustesPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { PipelinePage } from "@/pages/PipelinePage";
import { ScreeningPage } from "@/pages/ScreeningPage";

// Recharts and TanStack Table only serve the data screens, so they load on demand: the first
// paint of the dashboard stays light.
const SeriesPage = lazy(() =>
  import("@/features/series/SeriesPage").then((module) => ({ default: module.SeriesPage })),
);

const ControlPage = lazy(() =>
  import("@/features/control/ControlPage").then((module) => ({ default: module.ControlPage })),
);

function PageFallback() {
  return (
    <div className="flex flex-col gap-2" aria-busy="true">
      <Skeleton className="h-8 w-40" />
      <Skeleton className="h-64 w-full" />
      <span className="sr-only">Cargando la pantalla…</span>
    </div>
  );
}

export default function App() {
  return (
    <AppShell>
      <Suspense fallback={<PageFallback />}>
        <Routes>
          <Route path="/" element={<ResumenPage />} />
          <Route path="/sitios" element={<SitiosPage />} />
          <Route path="/series" element={<SeriesPage />} />
          <Route path="/control" element={<ControlPage />} />
          <Route path="/screening" element={<ScreeningPage />} />
          <Route path="/pipeline" element={<PipelinePage />} />
          <Route path="/ajustes" element={<AjustesPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Suspense>
    </AppShell>
  );
}
