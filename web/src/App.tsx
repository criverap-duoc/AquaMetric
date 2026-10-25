import { Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/layout/AppShell";
import { AjustesPage } from "@/pages/AjustesPage";
import { ControlPage } from "@/pages/ControlPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { PipelinePage } from "@/pages/PipelinePage";
import { ResumenPage } from "@/pages/ResumenPage";
import { ScreeningPage } from "@/pages/ScreeningPage";
import { SeriesPage } from "@/pages/SeriesPage";
import { SitiosPage } from "@/pages/SitiosPage";

export default function App() {
  return (
    <AppShell>
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
    </AppShell>
  );
}
