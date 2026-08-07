import { cn } from "@/lib/utils";
import { formatPercent } from "@/lib/format";

export function GPUUtilization({ value }: { value: number | null }) {
  const tone =
    value === null
      ? "bg-muted-foreground/30"
      : value >= 90
        ? "bg-amber-500"
        : value >= 50
          ? "bg-blue-500"
          : "bg-emerald-500";

  return (
    <div className="flex min-w-24 items-center gap-2">
      <div className="h-1.5 flex-1 overflow-hidden rounded-sm bg-muted">
        <div
          className={cn("h-full rounded-sm", tone)}
          style={{ width: `${value ?? 0}%` }}
        />
      </div>
      <span className="numeric w-8 text-right font-mono text-xs">
        {formatPercent(value)}
      </span>
    </div>
  );
}
