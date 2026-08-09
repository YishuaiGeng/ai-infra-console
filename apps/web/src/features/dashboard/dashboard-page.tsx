"use client";

import Link from "next/link";
import {
  Boxes,
  Download,
  HardDrive,
  Server as ServerIcon,
  Waypoints,
} from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip as ChartTooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  useGpus,
  useInfrastructureSummary,
  useServers,
} from "@/hooks/use-infrastructure";
import { useDeployments } from "@/hooks/use-deployments";
import { useDownloads } from "@/hooks/use-downloads";
import { useMetricsHistory } from "@/hooks/use-monitoring";
import { bytesToGiB } from "@/lib/api/infrastructure";
import { formatNumber, formatPercent } from "@/lib/format";
import { PageContainer } from "@/components/layout/page-container";
import { MetricCard } from "@/components/metrics/metric-card";
import { GPUResourceTable } from "@/components/gpu/gpu-resource-table";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { PageLoadingSkeleton } from "@/components/shared/loading-skeleton";
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
  const summaryQuery = useInfrastructureSummary();
  const serversQuery = useServers();
  const gpusQuery = useGpus();
  const deploymentsQuery = useDeployments();
  const downloadsQuery = useDownloads();
  const metricsHistoryQuery = useMetricsHistory(24);

  if (
    summaryQuery.isPending ||
    serversQuery.isPending ||
    gpusQuery.isPending ||
    deploymentsQuery.isPending ||
    downloadsQuery.isPending
  ) {
    return <PageLoadingSkeleton />;
  }
  const failed =
    summaryQuery.error ??
    serversQuery.error ??
    gpusQuery.error ??
    deploymentsQuery.error ??
    downloadsQuery.error;
  if (failed) {
    return (
      <PageContainer>
        <PageHeader
          title="Infrastructure overview"
          description="Unified status for servers and current GPU capacity."
        />
        <ErrorState
          title="Infrastructure data unavailable"
          message={failed.message}
          onRetry={() => {
            void summaryQuery.refetch();
            void serversQuery.refetch();
            void gpusQuery.refetch();
            void deploymentsQuery.refetch();
            void downloadsQuery.refetch();
          }}
        />
      </PageContainer>
    );
  }
  if (
    !summaryQuery.data ||
    !serversQuery.data ||
    !gpusQuery.data ||
    !deploymentsQuery.data ||
    !downloadsQuery.data
  ) {
    return <PageLoadingSkeleton />;
  }

  const summary = summaryQuery.data;
  const servers = serversQuery.data;
  const gpus = gpusQuery.data;
  const deployments = deploymentsQuery.data;
  const runningDeployments = deployments.filter((item) => item.status === "running");
  const activeDownloads = downloadsQuery.data.filter((item) =>
    ["queued", "downloading", "cancelling"].includes(item.status),
  );
  const usedMemory = bytesToGiB(summary.gpu_memory_used) ?? 0;
  const totalMemory = bytesToGiB(summary.gpu_memory_total) ?? 0;
  const memoryPercent = totalMemory > 0 ? (usedMemory / totalMemory) * 100 : 0;
  const prioritizedGpus = [...gpus].sort((a, b) => {
    const rank = {
      available: 0,
      active: 1,
      "high-load": 2,
      "memory-full": 3,
      unavailable: 4,
    };
    return rank[a.status] - rank[b.status];
  });
  const chartBuckets = new Map<
    string,
    {
      time: string;
      cpuValues: number[];
      gpuValues: number[];
      tempValues: number[];
    }
  >();
  for (const point of metricsHistoryQuery.data?.serverPoints ?? []) {
    const key = new Date(point.collectedAt).toISOString().slice(0, 16);
    const bucket =
      chartBuckets.get(key) ??
      { time: key, cpuValues: [], gpuValues: [], tempValues: [] };
    if (point.cpuUtilization !== null) bucket.cpuValues.push(point.cpuUtilization);
    chartBuckets.set(key, bucket);
  }
  for (const point of metricsHistoryQuery.data?.gpuPoints ?? []) {
    const key = new Date(point.collectedAt).toISOString().slice(0, 16);
    const bucket =
      chartBuckets.get(key) ??
      { time: key, cpuValues: [], gpuValues: [], tempValues: [] };
    if (point.utilization !== null) bucket.gpuValues.push(point.utilization);
    if (point.temperature !== null) bucket.tempValues.push(point.temperature);
    chartBuckets.set(key, bucket);
  }
  const trendData = [...chartBuckets.values()]
    .sort((a, b) => a.time.localeCompare(b.time))
    .slice(-48)
    .map((bucket) => ({
      time: new Date(bucket.time).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
      cpu:
        bucket.cpuValues.length > 0
          ? Math.round(
              bucket.cpuValues.reduce((sum, value) => sum + value, 0) /
                bucket.cpuValues.length,
            )
          : null,
      gpu:
        bucket.gpuValues.length > 0
          ? Math.round(
              bucket.gpuValues.reduce((sum, value) => sum + value, 0) /
                bucket.gpuValues.length,
            )
          : null,
      temperature:
        bucket.tempValues.length > 0
          ? Math.round(Math.max(...bucket.tempValues))
          : null,
    }));

  return (
    <PageContainer>
      <PageHeader
        title="Infrastructure overview"
        description="Unified status for servers and current GPU capacity."
        actions={
          <Link href="/gpus" className={buttonVariants({ variant: "outline" })}>
            <Boxes /> Inspect all GPUs
          </Link>
        }
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <MetricCard
          label="Servers"
          value={summary.server_count}
          detail={`${summary.online_server_count} online / ${summary.offline_server_count} offline`}
          icon={ServerIcon}
        />
        <MetricCard
          label="GPUs"
          value={summary.gpu_count}
          detail={`${summary.available_gpu_count} available now`}
          icon={Boxes}
          accent="green"
        />
        <MetricCard
          label="GPU Memory"
          value={`${formatNumber(usedMemory, 0)} GB`}
          detail={`${formatPercent(memoryPercent)} of ${formatNumber(totalMemory, 0)} GB`}
          icon={HardDrive}
          accent="yellow"
        />
        <MetricCard
          label="Running Models"
          value={runningDeployments.length}
          detail={`${deployments.length} configured`}
          icon={Waypoints}
          accent="blue"
        />
        <MetricCard
          label="Download Tasks"
          value={activeDownloads.length}
          detail={`${downloadsQuery.data.length} recorded`}
          icon={Download}
        />
      </div>

      <div className="mt-4">
        <SectionPanel
          title="GPU Resource Overview"
          description={`${summary.available_gpu_count} GPUs ready to schedule across ${summary.online_server_count} online servers`}
          action={
            <Link
              href="/gpus"
              className={buttonVariants({ variant: "ghost", size: "sm" })}
            >
              View inventory
            </Link>
          }
        >
          {prioritizedGpus.length ? (
            <GPUResourceTable data={prioritizedGpus} />
          ) : (
            <EmptyState
              icon={Boxes}
              title="No GPUs reported"
              message="CPU-only servers remain visible below. GPU inventory appears after an Agent reports a device."
            />
          )}
        </SectionPanel>
      </div>

      <div className="mt-4">
        <SectionPanel
          title="Recent resource trends"
          description="Last 24 hours from Agent metric samples"
        >
          {metricsHistoryQuery.isLoading ? (
            <div className="h-72 p-4 text-sm text-muted-foreground">Loading trends...</div>
          ) : trendData.length >= 2 ? (
            <div className="h-72 p-4">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="time" tick={{ fontSize: 11 }} minTickGap={24} />
                  <YAxis tick={{ fontSize: 11 }} width={34} domain={[0, 100]} />
                  <ChartTooltip
                    contentStyle={{
                      borderRadius: 6,
                      border: "1px solid hsl(var(--border))",
                      background: "hsl(var(--popover))",
                      color: "hsl(var(--popover-foreground))",
                      fontSize: 12,
                    }}
                  />
                  <Line type="monotone" dataKey="gpu" name="GPU util %" stroke="#2563eb" strokeWidth={2} dot={false} connectNulls />
                  <Line type="monotone" dataKey="cpu" name="CPU util %" stroke="#16a34a" strokeWidth={2} dot={false} connectNulls />
                  <Line type="monotone" dataKey="temperature" name="Max GPU temp C" stroke="#f59e0b" strokeWidth={2} dot={false} connectNulls />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState
              icon={HardDrive}
              title="Not enough metric history"
              message="Trends appear after Agents have reported at least two metric samples."
            />
          )}
        </SectionPanel>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1.05fr_1fr]">
        <SectionPanel
          title="Server Status"
          description="Agent heartbeat and host resource summary"
        >
          {servers.length ? (
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
                        {server.gpuCount > 0
                          ? `${server.gpuCount}x ${server.gpuModel}`
                          : "CPU only"}
                      </TableCell>
                      <TableCell className="numeric font-mono text-xs">
                        {formatPercent(server.cpuUsage)}
                      </TableCell>
                      <TableCell className="numeric font-mono text-xs">
                        {server.ramUsedGb === null || server.ramTotalGb === 0
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
          ) : (
            <EmptyState
              icon={ServerIcon}
              title="No servers registered"
              message="Create a server registration to begin receiving Agent heartbeats."
            />
          )}
        </SectionPanel>

        <SectionPanel
          title="Running Models"
          description="Deployment runtime records"
        >
          {runningDeployments.length ? (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Deployment</TableHead>
                    <TableHead>Server</TableHead>
                    <TableHead>Health</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {runningDeployments.map((deployment) => (
                    <TableRow key={deployment.id}>
                      <TableCell>
                        <Link
                          href={`/deployments/${deployment.id}`}
                          className="font-medium hover:underline"
                        >
                          {deployment.name}
                        </Link>
                        <div className="max-w-48 truncate text-[11px] text-muted-foreground">
                          {deployment.model.displayName}
                        </div>
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {deployment.server.name}
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={deployment.healthStatus} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <EmptyState
              icon={Waypoints}
              title="No model runtimes"
              message="Running deployments will appear here after a runtime becomes healthy."
            />
          )}
        </SectionPanel>
      </div>
    </PageContainer>
  );
}
