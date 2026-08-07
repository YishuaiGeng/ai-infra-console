"use client";

import { useMemo, useState } from "react";
import { createColumnHelper } from "@tanstack/react-table";
import { Grid2X2, List, Thermometer, Zap } from "lucide-react";

import type { GPU } from "@/types";
import { getServer, gpus, servers } from "@/mocks/data";
import { cn } from "@/lib/utils";
import { DataTable, dataTableFeatures, type DataTableColumn } from "@/components/shared/data-table";
import { GPUCard } from "@/components/gpu/gpu-card";
import { GPUMemoryBar } from "@/components/gpu/gpu-memory-bar";
import { GPUStatusBadge } from "@/components/gpu/gpu-status-badge";
import { GPUUtilization } from "@/components/gpu/gpu-utilization";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/shared/page-header";
import { SectionPanel } from "@/components/shared/section-panel";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";

const helper = createColumnHelper<typeof dataTableFeatures, GPU>();

const columns: DataTableColumn<GPU>[] = helper.columns([
  helper.accessor("serverId", {
    id: "Server",
    header: "Server",
    cell: ({ getValue }) => {
      const server = getServer(getValue());
      return (
        <div>
          <div className="font-medium">{server?.name}</div>
          <div className="font-mono text-[11px] text-muted-foreground">
            {server?.type} / {server?.ip}
          </div>
        </div>
      );
    },
    sortFn: "text",
  }),
  helper.accessor("index", {
    id: "GPU",
    header: "GPU",
    cell: ({ row }) => (
      <div className="whitespace-nowrap">
        <div className="font-mono text-xs">GPU {row.original.index}</div>
        <div className="text-[11px] text-muted-foreground">{row.original.name}</div>
      </div>
    ),
    sortFn: "basic",
  }),
  helper.accessor("status", {
    header: "Status",
    cell: ({ getValue }) => <GPUStatusBadge status={getValue()} />,
    sortFn: "text",
  }),
  helper.accessor("utilization", {
    header: "Utilization",
    cell: ({ getValue }) => <GPUUtilization value={getValue()} />,
    sortFn: "basic",
  }),
  helper.accessor("memoryUsedGb", {
    id: "VRAM",
    header: "VRAM",
    cell: ({ row }) => (
      <GPUMemoryBar
        used={row.original.memoryUsedGb}
        total={row.original.memoryTotalGb}
      />
    ),
    sortFn: "basic",
  }),
  helper.accessor("temperatureC", {
    id: "Temperature",
    header: "Temperature",
    cell: ({ getValue }) => (
      <span className="numeric flex items-center gap-1 font-mono text-xs">
        <Thermometer className="size-3 text-muted-foreground" />
        {getValue() === null ? "--" : `${getValue()} C`}
      </span>
    ),
    sortFn: "basic",
  }),
  helper.accessor("powerWatts", {
    id: "Power",
    header: "Power",
    cell: ({ row }) => (
      <span className="numeric flex items-center gap-1 whitespace-nowrap font-mono text-xs">
        <Zap className="size-3 text-muted-foreground" />
        {row.original.powerWatts === null
          ? "--"
          : `${row.original.powerWatts} / ${row.original.powerLimitWatts} W`}
      </span>
    ),
    sortFn: "basic",
  }),
  helper.accessor("workload", {
    header: "Workload",
    cell: ({ getValue }) =>
      getValue() ? (
        <span className="text-xs font-medium">{getValue()}</span>
      ) : (
        <span className="text-xs text-emerald-600 dark:text-emerald-400">
          Available
        </span>
      ),
    sortFn: "text",
  }),
]);

export function GpusPage() {
  const [view, setView] = useState<"table" | "card">("table");
  const [serverId, setServerId] = useState("all");
  const [gpuModel, setGpuModel] = useState("all");
  const [status, setStatus] = useState("all");
  const [type, setType] = useState("all");
  const [availableOnly, setAvailableOnly] = useState(false);
  const gpuModels = [...new Set(gpus.map((gpu) => gpu.name))];
  const filtered = useMemo(
    () =>
      gpus.filter((gpu) => {
        const server = getServer(gpu.serverId);
        return (
          (serverId === "all" || gpu.serverId === serverId) &&
          (gpuModel === "all" || gpu.name === gpuModel) &&
          (status === "all" || gpu.status === status) &&
          (type === "all" || server?.type === type) &&
          (!availableOnly || gpu.status === "available")
        );
      }),
    [availableOnly, gpuModel, serverId, status, type],
  );

  const filters = (
    <div className="flex flex-wrap items-center gap-2">
      <Select value={serverId} onValueChange={(value) => value && setServerId(value)}>
        <SelectTrigger size="sm" className="w-40">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All servers</SelectItem>
          {servers.map((server) => (
            <SelectItem key={server.id} value={server.id}>{server.name}</SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select value={gpuModel} onValueChange={(value) => value && setGpuModel(value)}>
        <SelectTrigger size="sm" className="w-36">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All GPU models</SelectItem>
          {gpuModels.map((model) => (
            <SelectItem key={model} value={model}>{model}</SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select value={status} onValueChange={(value) => value && setStatus(value)}>
        <SelectTrigger size="sm" className="w-36">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All statuses</SelectItem>
          <SelectItem value="available">Available</SelectItem>
          <SelectItem value="active">Active</SelectItem>
          <SelectItem value="high-load">High Load</SelectItem>
          <SelectItem value="memory-full">Memory Full</SelectItem>
          <SelectItem value="unavailable">Unavailable</SelectItem>
        </SelectContent>
      </Select>
      <Select value={type} onValueChange={(value) => value && setType(value)}>
        <SelectTrigger size="sm" className="w-28">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All types</SelectItem>
          <SelectItem value="local">Local</SelectItem>
          <SelectItem value="cloud">Cloud</SelectItem>
        </SelectContent>
      </Select>
      <label className="flex h-8 items-center gap-2 rounded-md border px-2.5 text-xs font-medium">
        <Switch checked={availableOnly} onCheckedChange={setAvailableOnly} />
        Available only
      </label>
    </div>
  );

  return (
    <PageContainer>
      <PageHeader
        title="GPU inventory"
        description="Compare utilization, memory pressure, temperature, and current workloads across every server."
        actions={
          <div className="flex rounded-md border bg-background p-0.5">
            <Button
              variant="ghost"
              size="icon-sm"
              className={cn(view === "table" && "bg-muted")}
              onClick={() => setView("table")}
              aria-label="Table view"
            >
              <List />
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              className={cn(view === "card" && "bg-muted")}
              onClick={() => setView("card")}
              aria-label="Card view"
            >
              <Grid2X2 />
            </Button>
          </div>
        }
      />

      {view === "table" ? (
        <SectionPanel
          title="GPU resources"
          description={`${filtered.length} of ${gpus.length} devices visible`}
        >
          <DataTable
            data={filtered}
            columns={columns}
            searchText={(gpu) => `${getServer(gpu.serverId)?.name} ${gpu.name} ${gpu.workload ?? "available"}`}
            searchPlaceholder="Search GPU or workload..."
            toolbar={filters}
            emptyTitle="No GPUs match"
            emptyMessage="Clear one or more infrastructure filters to show devices."
          />
        </SectionPanel>
      ) : (
        <div>
          <div className="mb-3 rounded-md border bg-card p-3">{filters}</div>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
            {filtered.map((gpu) => (
              <GPUCard key={gpu.id} gpu={gpu} />
            ))}
          </div>
        </div>
      )}
    </PageContainer>
  );
}
