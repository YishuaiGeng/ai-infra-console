import { Circle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { titleCase } from "@/lib/format";

type Tone = "green" | "blue" | "yellow" | "red" | "gray";

const toneClasses: Record<Tone, string> = {
  green:
    "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/70 dark:bg-emerald-950/45 dark:text-emerald-300",
  blue: "border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-900/70 dark:bg-blue-950/45 dark:text-blue-300",
  yellow:
    "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900/70 dark:bg-amber-950/45 dark:text-amber-300",
  red: "border-red-200 bg-red-50 text-red-700 dark:border-red-900/70 dark:bg-red-950/45 dark:text-red-300",
  gray: "border-border bg-muted/70 text-muted-foreground",
};

const statusTone: Record<string, Tone> = {
  online: "green",
  healthy: "green",
  available: "green",
  installed: "green",
  discovered: "green",
  completed: "green",
  success: "green",
  active: "blue",
  running: "blue",
  starting: "blue",
  downloading: "blue",
  deleting: "blue",
  cancelling: "yellow",
  queued: "yellow",
  warning: "yellow",
  verifying: "yellow",
  stale: "yellow",
  degraded: "yellow",
  "high-load": "yellow",
  "memory-full": "yellow",
  failed: "red",
  offline: "red",
  error: "red",
  critical: "red",
  unavailable: "red",
  missing: "red",
  stopped: "gray",
  stopping: "gray",
  unknown: "gray",
  cancelled: "gray",
};

export function StatusBadge({
  status,
  label,
  className,
}: {
  status: string;
  label?: string;
  className?: string;
}) {
  const tone = statusTone[status] ?? "gray";

  return (
    <Badge
      variant="outline"
      className={cn(
        "h-5 gap-1 rounded-sm px-1.5 text-[11px] font-medium",
        toneClasses[tone],
        className,
      )}
    >
      <Circle className="size-1.5 fill-current" />
      {label ?? titleCase(status)}
    </Badge>
  );
}
