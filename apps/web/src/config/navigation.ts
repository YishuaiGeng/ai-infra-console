import {
  Activity,
  Boxes,
  Download,
  Gauge,
  HardDrive,
  Library,
  Server,
  Settings,
  Waypoints,
  type LucideIcon,
} from "lucide-react";

export interface NavigationItem {
  label: string;
  href: string;
  icon: LucideIcon;
  match?: string[];
}

export interface NavigationGroup {
  label: string;
  items: NavigationItem[];
}

export const navigation: NavigationGroup[] = [
  {
    label: "Overview",
    items: [{ label: "Dashboard", href: "/dashboard", icon: Gauge }],
  },
  {
    label: "Infrastructure",
    items: [
      {
        label: "Servers",
        href: "/servers",
        icon: Server,
        match: ["/servers"],
      },
      { label: "GPUs", href: "/gpus", icon: Boxes },
    ],
  },
  {
    label: "Models",
    items: [
      { label: "Model Library", href: "/models/library", icon: Library },
      { label: "Installed Models", href: "/models", icon: HardDrive },
      {
        label: "Deployments",
        href: "/deployments",
        icon: Waypoints,
        match: ["/deployments"],
      },
      { label: "Downloads", href: "/downloads", icon: Download },
    ],
  },
  {
    label: "Services",
    items: [{ label: "API Endpoints", href: "/apis", icon: Waypoints }],
  },
  {
    label: "System",
    items: [
      { label: "Activity", href: "/activity", icon: Activity },
      { label: "Settings", href: "/settings", icon: Settings },
    ],
  },
];

export const breadcrumbLabels: Record<string, string> = {
  dashboard: "Dashboard",
  servers: "Servers",
  gpus: "GPUs",
  models: "Installed Models",
  library: "Model Library",
  deployments: "Deployments",
  downloads: "Downloads",
  apis: "API Endpoints",
  activity: "Activity",
  settings: "Settings",
};
