import Link from "next/link";
import {
  Boxes,
  Download,
  HardDrive,
  Server as ServerIcon,
  Waypoints,
} from "lucide-react";

import {
  deployments,
  downloadTasks,
  getModel,
  getServer,
  gpus,
  servers,
} from "@/mocks/data";
import { formatNumber, formatPercent } from "@/lib/format";
import { PageContainer } from "@/components/layout/page-container";
import { MetricCard } from "@/components/metrics/metric-card";
import { GPUResourceTable } from "@/components/gpu/gpu-resource-table";
import { PageHeader } from "@/components/shared/page-header";
import { SectionPanel } from "@/components/shared/section-panel";
import { StatusBadge } from "@/components/shared/status-badge";
import { buttonVariants } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export function DashboardPage() {
  const onlineServers = servers.filter((server) => server.status === "online");
  const availableGpus = gpus.filter((gpu) => gpu.status === "available");
  const runningDeployments = deployments.filter(
    (deployment) => deployment.status === "running",
  );
  const activeDownloads = downloadTasks.filter(
    (task) => task.status === "downloading" || task.status === "queued",
  );
  const usedMemory = gpus.reduce(
    (sum, gpu) => sum + (gpu.memoryUsedGb ?? 0),
    0,
  );
  const totalMemory = gpus.reduce((sum, gpu) => sum + gpu.memoryTotalGb, 0);

  const prioritizedGpus = [...gpus].sort((a, b) => {
    const rank = { available: 0, active: 1, "high-load": 2, "memory-full": 3, unavailable: 4 };
    return rank[a.status] - rank[b.status];
  });

  return (
    <PageContainer>
      <PageHeader
        title="Infrastructure overview"
        description="Unified status for servers, GPU capacity, model runtimes, and transfer activity."
        actions={
          <Link href="/gpus" className={buttonVariants({ variant: "outline" })}>
            <Boxes /> Inspect all GPUs
          </Link>
        }
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <MetricCard
          label="Servers"
          value={servers.length}
          detail={`${onlineServers.length} online / ${servers.length - onlineServers.length} offline`}
          icon={ServerIcon}
        />
        <MetricCard
          label="GPUs"
          value={gpus.length}
          detail={`${availableGpus.length} available now`}
          icon={Boxes}
          accent="green"
        />
        <MetricCard
          label="GPU Memory"
          value={`${formatNumber(usedMemory, 0)} GB`}
          detail={`${formatPercent((usedMemory / totalMemory) * 100)} of ${totalMemory} GB`}
          icon={HardDrive}
          accent="yellow"
        />
        <MetricCard
          label="Running Models"
          value={runningDeployments.length}
          detail={`${runningDeployments.filter((item) => item.backend === "vLLM").length} vLLM runtimes`}
          icon={Waypoints}
          accent="blue"
        />
        <MetricCard
          label="Download Tasks"
          value={activeDownloads.length}
          detail={`${downloadTasks.filter((item) => item.status === "downloading").length} transferring`}
          icon={Download}
        />
      </div>

      <div className="mt-4">
        <SectionPanel
          title="GPU Resource Overview"
          description={`${availableGpus.length} GPUs ready to schedule across ${onlineServers.length} online servers`}
          action={
            <Link
              href="/gpus"
              className={buttonVariants({ variant: "ghost", size: "sm" })}
            >
              View inventory
            </Link>
          }
        >
          <GPUResourceTable data={prioritizedGpus} />
        </SectionPanel>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1.05fr_1fr]">
        <SectionPanel
          title="Server Status"
          description="Agent heartbeat and host resource summary"
        >
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Server</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>GPU</TableHead>
                  <TableHead>CPU</TableHead>
                  <TableHead>RAM</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {servers.map((server) => (
                  <TableRow key={server.id}>
                    <TableCell>
                      <Link
                        href={`/servers/${server.id}`}
                        className="font-medium hover:underline"
                      >
                        {server.name}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={server.status} />
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-xs">
                      {server.gpuCount}x {server.gpuModel}
                    </TableCell>
                    <TableCell className="numeric font-mono text-xs">
                      {formatPercent(server.cpuUsage)}
                    </TableCell>
                    <TableCell className="numeric font-mono text-xs">
                      {server.ramUsedGb === null
                        ? "--"
                        : formatPercent(
                            (server.ramUsedGb / server.ramTotalGb) * 100,
                          )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </SectionPanel>

        <SectionPanel
          title="Running Models"
          description="Healthy OpenAI-compatible runtimes"
        >
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Model</TableHead>
                  <TableHead>Server / GPU</TableHead>
                  <TableHead>Backend</TableHead>
                  <TableHead>Endpoint</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {runningDeployments.map((deployment) => {
                  const model = getModel(deployment.modelId);
                  const server = getServer(deployment.serverId);
                  return (
                    <TableRow key={deployment.id}>
                      <TableCell>
                        <Link
                          href={`/deployments/${deployment.id}`}
                          className="font-medium hover:underline"
                        >
                          {model?.displayName}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <div className="text-xs">{server?.name}</div>
                        <div className="font-mono text-[11px] text-muted-foreground">
                          {deployment.gpuIds
                            .map(
                              (id) =>
                                `GPU ${gpus.find((gpu) => gpu.id === id)?.index}`,
                            )
                            .join(", ")}
                        </div>
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {deployment.backend}
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        :{deployment.port}
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={deployment.status} />
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </SectionPanel>
      </div>
    </PageContainer>
  );
}
