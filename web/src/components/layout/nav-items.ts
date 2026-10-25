import {
  Activity,
  Cloud,
  Home,
  LineChart,
  MapPin,
  Settings,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  /** Only "/" needs exact matching; the other routes are flat prefixes. */
  end?: boolean;
}

/** Single source for the sidebar links and the breadcrumb label in the app shell. */
export const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Resumen", icon: Home, end: true },
  { to: "/sitios", label: "Sitios", icon: MapPin },
  { to: "/series", label: "Series", icon: LineChart },
  { to: "/control", label: "Control (SPC)", icon: Activity },
  { to: "/screening", label: "Screening", icon: ShieldCheck },
  { to: "/pipeline", label: "Pipeline", icon: Cloud },
  { to: "/ajustes", label: "Ajustes", icon: Settings },
];
