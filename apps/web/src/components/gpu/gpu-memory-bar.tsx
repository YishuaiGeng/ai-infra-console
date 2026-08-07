import { cn } from "@/lib/utils";
import { formatMemory } from "@/lib/format";

export function GPUMemoryBar({
  used,
  total,
  compact = false,
}: {
  used: number | null;
  total: number;
  compact?: boolean;
}) {
  const percent = used === null ? 0 : Math.min((used / total) * 100, 100);
  const tone =
    used === null
      ? "bg-muted-foreground/30"
      : percent >= 90
        ? "bg-amber-500"
        : percent >= 60
          ? "bg-blue-500"
          : "bg-emerald-500";

  return (
    <div className={cn("min-w-28", compact && "min-w-20")}>
      <div className="mb-1 flex items-center justify-between gap-2 font-mono text-[11px]">
        <span className="numeric whitespace-nowrap">
          {formatMemory(used, total)}
        </span>
        {!compact && (
          <span className="numeric text-muted-foreground">
            {used === null ? "--" : `${Math.round(percent)}%`}
          </span>
        )}
      </div>
      <div className="h-1.5 overflow-hidden rounded-sm bg-muted">
        <div
          className={cn("h-full rounded-sm transition-[width]", tone)}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
