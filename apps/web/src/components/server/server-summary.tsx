import { Cpu, Database, HardDrive, MemoryStick, Network } from "lucide-react";

import type { Server } from "@/types";
import { formatNumber, formatPercent } from "@/lib/format";

function SummaryItem({
  label,
  value,
  detail,
  icon: Icon,
}: {
  label: string;
  value: string;
  detail: string;
  icon: typeof Cpu;
}) {
  return (
    <div className="border-b p-4 last:border-b-0 sm:border-b-0 sm:border-r sm:last:border-r-0">
      <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
        <Icon className="size-3.5" /> {label}
      </div>
      <div className="numeric mt-2 text-lg font-semibold">{value}</div>
      <div className="mt-0.5 truncate text-xs text-muted-foreground">{detail}</div>
    </div>
  );
}

export function ServerSummary({ server }: { server: Server }) {
  const ramPercent =
    server.ramUsedGb === null || server.ramTotalGb === 0
      ? null
      : (server.ramUsedGb / server.ramTotalGb) * 100;
  const diskPercent =
    server.diskUsedGb === null || server.diskTotalGb === 0
      ? null
      : (server.diskUsedGb / server.diskTotalGb) * 100;

  return (
    <div className="grid overflow-hidden rounded-md border bg-card sm:grid-cols-2 xl:grid-cols-5">
      <SummaryItem
        icon={Cpu}
        label="CPU"
        value={formatPercent(server.cpuUsage)}
        detail={`${server.cpuCores} cores / ${server.cpuModel}`}
      />
      <SummaryItem
        icon={MemoryStick}
        label="Memory"
        value={formatPercent(ramPercent)}
        detail={
          server.ramUsedGb === null
            ? `${server.ramTotalGb} GB total`
            : `${server.ramUsedGb} / ${server.ramTotalGb} GB`
        }
      />
      <SummaryItem
        icon={HardDrive}
        label="Disk"
        value={formatPercent(diskPercent)}
        detail={
          server.diskUsedGb === null
            ? `${server.diskTotalGb} GB total`
            : `${formatNumber(server.diskUsedGb)} / ${formatNumber(server.diskTotalGb)} GB`
        }
      />
      <SummaryItem
        icon={Database}
        label="Models"
        value={`${server.modelCount}`}
        detail={`${server.runningCount} running deployment${server.runningCount === 1 ? "" : "s"}`}
      />
      <SummaryItem
        icon={Network}
        label="Network"
        value={
          server.networkRxMbps === null ? "--" : `${server.networkRxMbps} Mbps`
        }
        detail={
          server.networkTxMbps === null
            ? "Agent offline"
            : `${server.networkTxMbps} Mbps outbound`
        }
      />
    </div>
  );
}
