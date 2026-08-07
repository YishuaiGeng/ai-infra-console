import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

export function MetricCard({
  label,
  value,
  detail,
  icon: Icon,
  accent = "default",
}: {
  label: string;
  value: string | number;
  detail: string;
  icon: LucideIcon;
  accent?: "default" | "green" | "blue" | "yellow";
}) {
  const iconClass = {
    default: "bg-muted text-muted-foreground",
    green:
      "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/50 dark:text-emerald-300",
    blue: "bg-blue-50 text-blue-600 dark:bg-blue-950/50 dark:text-blue-300",
    yellow:
      "bg-amber-50 text-amber-600 dark:bg-amber-950/50 dark:text-amber-300",
  }[accent];

  return (
    <div className="min-w-0 rounded-md border bg-card p-3.5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[11px] font-semibold uppercase text-muted-foreground">
            {label}
          </div>
          <div className="numeric mt-1 text-2xl font-semibold">{value}</div>
          <div className="mt-0.5 truncate text-xs text-muted-foreground">
            {detail}
          </div>
        </div>
        <span className={cn("flex size-8 items-center justify-center rounded-md", iconClass)}>
          <Icon className="size-4" />
        </span>
      </div>
    </div>
  );
}
