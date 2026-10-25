import { PanelLeftClose, PanelLeftOpen, Waves } from "lucide-react";
import { NavLink } from "react-router-dom";

import { NAV_ITEMS } from "@/components/layout/nav-items";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface SidebarProps {
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
  onNavigate?: () => void;
  className?: string;
}

export function Sidebar({
  isCollapsed = false,
  onToggleCollapse,
  onNavigate,
  className,
}: SidebarProps) {
  return (
    <nav
      aria-label="Navegación principal"
      className={cn(
        "flex h-full flex-col gap-4 border-r border-sidebar-border bg-sidebar py-2",
        isCollapsed ? "w-14 px-2" : "w-60 px-2",
        className,
      )}
    >
      <div
        className={cn(
          "flex h-12 items-center gap-2 px-2",
          isCollapsed && "justify-center px-0",
        )}
      >
        <Waves aria-hidden="true" className="size-5 shrink-0 text-sidebar-primary" />
        <span
          className={cn(
            "truncate text-sm font-semibold tracking-tight text-sidebar-foreground",
            isCollapsed && "sr-only",
          )}
        >
          AquaMetric
        </span>
      </div>

      <ul className="flex flex-1 flex-col gap-1">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <li key={to}>
            {/* NavLink sets aria-current="page" on the active link. */}
            <NavLink
              to={to}
              end={end}
              onClick={onNavigate}
              title={isCollapsed ? label : undefined}
              className={({ isActive }) =>
                cn(
                  "flex h-9 items-center gap-2 rounded-md px-2 text-sm transition-colors focus-visible:ring-2 focus-visible:ring-sidebar-ring focus-visible:ring-offset-2 focus-visible:outline-none",
                  isActive
                    ? "bg-sidebar-accent font-medium text-sidebar-accent-foreground"
                    : "text-sidebar-foreground hover:bg-sidebar-accent/60",
                  isCollapsed && "justify-center",
                )
              }
            >
              <Icon aria-hidden="true" className="size-4 shrink-0" />
              <span className={cn("truncate", isCollapsed && "sr-only")}>{label}</span>
            </NavLink>
          </li>
        ))}
      </ul>

      {onToggleCollapse ? (
        <div className="border-t border-sidebar-border pt-2">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={onToggleCollapse}
            aria-expanded={!isCollapsed}
            aria-label={isCollapsed ? "Expandir menú lateral" : "Contraer menú lateral"}
            className="w-full"
          >
            {isCollapsed ? (
              <PanelLeftOpen aria-hidden="true" className="size-4" />
            ) : (
              <PanelLeftClose aria-hidden="true" className="size-4" />
            )}
          </Button>
        </div>
      ) : null}
    </nav>
  );
}
