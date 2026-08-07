import { Activity, Flame, Gauge, Zap } from "lucide-react";

import type { GPU } from "@/types";
import { getServer } from "@/mocks/data";
import { GPUMemoryBar } from "@/components/gpu/gpu-memory-bar";
import { GPUStatusBadge } from "@/components/gpu/gpu-status-badge";

export function GPUCard({ gpu }: { gpu: GPU }) {
  const server = getServer(gpu.serverId);

  return (
    <article className="overflow-hidden rounded-md border bg-card">
      <div className="flex items-start justify-between gap-3 border-b px-4 py-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs text-muted-foreground">
              GPU {gpu.index}
            </span>
            <GPUStatusBadge status={gpu.status} />
          </div>
          <h3 className="mt-1 truncate text-sm font-semibold">{gpu.name}</h3>
          <p className="mt-0.5 truncate font-mono text-[11px] text-muted-foreground">
            {server?.name}
          </p>
        </div>
        <Activity className="size-4 text-muted-foreground" />
      </div>
      <div className="space-y-4 p-4">
        <GPUMemoryBar used={gpu.memoryUsedGb} total={gpu.memoryTotalGb} />
        <div className="grid grid-cols-3 gap-2 text-xs">
          <div>
            <div className="flex items-center gap-1 text-muted-foreground">
              <Gauge className="size-3" /> Util
            </div>
            <div className="numeric mt-1 font-mono font-medium">
              {gpu.utilization === null ? "--" : `${gpu.utilization}%`}
            </div>
          </div>
          <div>
            <div className="flex items-center gap-1 text-muted-foreground">
              <Flame className="size-3" /> Temp
            </div>
            <div className="numeric mt-1 font-mono font-medium">
              {gpu.temperatureC === null ? "--" : `${gpu.temperatureC} C`}
            </div>
          </div>
          <div>
            <div className="flex items-center gap-1 text-muted-foreground">
              <Zap className="size-3" /> Power
            </div>
            <div className="numeric mt-1 font-mono font-medium">
              {gpu.powerWatts === null ? "--" : `${gpu.powerWatts} W`}
            </div>
          </div>
        </div>
      </div>
      <div className="border-t bg-muted/25 px-4 py-2.5">
        <div className="text-[10px] font-semibold uppercase text-muted-foreground">
          Current workload
        </div>
        <div className="mt-0.5 truncate text-xs font-medium">
          {gpu.workload ??
            (gpu.status === "available"
              ? "Available for scheduling"
              : "Agent unavailable")}
        </div>
      </div>
    </article>
  );
}
