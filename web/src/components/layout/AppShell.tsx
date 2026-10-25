import { Menu } from "lucide-react";
import { useState, type ReactNode } from "react";
import { useLocation } from "react-router-dom";

import { NAV_ITEMS } from "@/components/layout/nav-items";
import { Sidebar } from "@/components/layout/Sidebar";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";

interface AppShellProps {
  children: ReactNode;
}

const DEFAULT_SECTION_LABEL = "Resumen";

function getSectionLabel(pathname: string): string {
  const section = NAV_ITEMS.filter((item) => !item.end).find((item) =>
    pathname.startsWith(item.to),
  );
  return section?.label ?? DEFAULT_SECTION_LABEL;
}

export function AppShell({ children }: AppShellProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);
  const { pathname } = useLocation();
  const sectionLabel = getSectionLabel(pathname);

  return (
    <div className="flex min-h-svh bg-background text-foreground">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:rounded-md focus:bg-card focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:shadow-pop focus:ring-2 focus:ring-ring focus:outline-none"
      >
        Saltar al contenido
      </a>

      <Sidebar
        isCollapsed={isCollapsed}
        onToggleCollapse={() => setIsCollapsed((previous) => !previous)}
        className="sticky top-0 hidden h-svh shrink-0 lg:flex"
      />

      <Sheet open={isMobileNavOpen} onOpenChange={setIsMobileNavOpen}>
        <SheetContent side="left" className="w-60 p-0">
          <SheetHeader className="sr-only">
            <SheetTitle>Navegación</SheetTitle>
          </SheetHeader>
          <Sidebar onNavigate={() => setIsMobileNavOpen(false)} className="w-full border-r-0" />
        </SheetContent>
      </Sheet>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center gap-2 border-b border-border bg-background/95 px-4 backdrop-blur sm:px-6 lg:px-8">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="lg:hidden"
            aria-label="Abrir menú de navegación"
            onClick={() => setIsMobileNavOpen(true)}
          >
            <Menu aria-hidden="true" />
          </Button>
          <nav aria-label="Ubicación actual" className="flex min-w-0 items-center gap-2">
            <span className="truncate text-sm font-semibold tracking-tight">AquaMetric</span>
            <span aria-hidden="true" className="text-muted-foreground">
              /
            </span>
            <span className="truncate text-sm text-muted-foreground">{sectionLabel}</span>
          </nav>
        </header>

        <main id="main" className="mx-auto w-full max-w-[1440px] px-4 py-6 sm:px-6 lg:px-8">
          {children}
        </main>
      </div>
    </div>
  );
}
