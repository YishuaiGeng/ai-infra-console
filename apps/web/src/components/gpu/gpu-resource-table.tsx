import { Cpu, ExternalLink } from "lucide-react";
import Link from "next/link";

import type { GPU } from "@/types";
import { buttonVariants } from "@/components/ui/button";
import { GPUMemoryBar } from "@/components/gpu/gpu-memory-bar";
import { GPUStatusBadge } from "@/components/gpu/gpu-status-badge";
import { GPUUtilization } from "@/components/gpu/gpu-utilization";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export function GPUResourceTable({ data }: { data: GPU[] }) {
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Server / GPU</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Utilization</TableHead>
            <TableHead>VRAM</TableHead>
            <TableHead>Temp</TableHead>
            <TableHead>Current workload</TableHead>
            <TableHead className="w-10" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((gpu) => (
              <TableRow key={gpu.id}>
                <TableCell>
                  <div className="flex items-center gap-2.5">
                    <span className="flex size-7 items-center justify-center rounded-md bg-muted text-muted-foreground">
                      <Cpu className="size-3.5" />
                    </span>
                    <div>
                      <div className="text-xs font-medium">
                        {gpu.serverName ?? "Unknown server"}
                      </div>
                      <div className="font-mono text-[11px] text-muted-foreground">
                        GPU {gpu.index} / {gpu.name}
                      </div>
                    </div>
                  </div>
                </TableCell>
                <TableCell>
                  <GPUStatusBadge status={gpu.status} />
                </TableCell>
                <TableCell>
                  <GPUUtilization value={gpu.utilization} />
                </TableCell>
                <TableCell>
                  <GPUMemoryBar
                    used={gpu.memoryUsedGb}
                    total={gpu.memoryTotalGb}
                    compact
                  />
                </TableCell>
                <TableCell className="numeric font-mono text-xs">
                  {gpu.temperatureC === null ? "--" : `${gpu.temperatureC} C`}
                </TableCell>
                <TableCell>
                  {gpu.workload ? (
                    <span className="text-xs font-medium">{gpu.workload}</span>
                  ) : gpu.status === "available" ? (
                    <span className="text-xs text-emerald-600 dark:text-emerald-400">
                      Ready to schedule
                    </span>
                  ) : (
                    <span className="text-xs text-muted-foreground">
                      Agent unavailable
                    </span>
                  )}
                </TableCell>
                <TableCell>
                  <Link
                    href={`/servers/${gpu.serverId}`}
                    className={buttonVariants({
                      variant: "ghost",
                      size: "icon-xs",
                    })}
                    aria-label={`Open ${gpu.serverName ?? "server"}`}
                  >
                    <ExternalLink />
                  </Link>
                </TableCell>
              </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
