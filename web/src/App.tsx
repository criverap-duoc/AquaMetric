import { lazy, Suspense } from "react";
import { Route, Routes, useLocation } from "react-router-dom";

import { ErrorBoundary } from "@/components/domain/ErrorBoundary";
import { AppShell } from "@/components/layout/AppShell";
import { Skeleton } from "@/components/ui/skeleton";
import { ResumenPage } from "@/features/resumen/ResumenPage";
import { SitiosPage } from "@/features/sitios/SitiosPage";
import { NotFoundPage } from "@/pages/NotFoundPage";

// Recharts and TanStack Table only serve the data screens, so they load on demand: the first
// paint of the dashboard stays light.
const SeriesPage = lazy(() =>
  import("@/features/series/SeriesPage").then((module) => ({ default: module.SeriesPage })),
);

const ControlPage = lazy(() =>
  import("@/features/control/ControlPage").then((module) => ({ default: module.ControlPage })),
);

const ScreeningPage = lazy(() =>
  import("@/features/screening/ScreeningPage").then((module) => ({
    default: module.ScreeningPage,
  })),
);

const PipelinePage = lazy(() =>
  import("@/features/pipeline/PipelinePage").then((module) => ({ default: module.PipelinePage })),
);

const AjustesPage = lazy(() =>
  import("@/features/ajustes/AjustesPage").then((module) => ({ default: module.AjustesPage })),
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
  const location = useLocation();

  return (
    <AppShell>
      {/* Keyed by path so navigating away from a crashed screen resets the boundary. */}
      <ErrorBoundary key={location.pathname}>
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
      </ErrorBoundary>
    </AppShell>
  );
}
