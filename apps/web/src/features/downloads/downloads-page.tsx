"use client";

import { createColumnHelper } from "@tanstack/react-table";
import { Ban, RotateCcw } from "lucide-react";
import { toast } from "sonner";

import type { DownloadTask } from "@/types";
import { downloadTasks, getModel, getServer } from "@/mocks/data";
import { formatDateTime, formatNumber } from "@/lib/format";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/shared/page-header";
import { SectionPanel } from "@/components/shared/section-panel";
import { StatusBadge } from "@/components/shared/status-badge";
import { DataTable, dataTableFeatures, type DataTableColumn } from "@/components/shared/data-table";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

const helper = createColumnHelper<typeof dataTableFeatures, DownloadTask>();
const columns: DataTableColumn<DownloadTask>[] = helper.columns([
  helper.accessor("modelId", {
    id: "Model",
    header: "Model",
    cell: ({ getValue }) => (
      <div>
        <div className="font-medium">{getModel(getValue())?.displayName}</div>
        <div className="font-mono text-[11px] text-muted-foreground">{getModel(getValue())?.name}</div>
      </div>
    ),
    sortFn: "text",
  }),
  helper.accessor("serverId", {
    id: "Server",
    header: "Server",
    cell: ({ getValue }) => <span className="font-mono text-xs">{getServer(getValue())?.name}</span>,
    sortFn: "text",
  }),
  helper.accessor("progress", {
    header: "Progress",
    cell: ({ row }) => (
      <div className="min-w-40">
        <div className="mb-1 flex justify-between font-mono text-[11px]">
          <span>{row.original.progress}%</span>
          <span className="text-muted-foreground">
            {formatNumber(row.original.downloadedGb)} / {formatNumber(row.original.totalGb)} GB
          </span>
        </div>
        <Progress value={row.original.progress} className="h-1.5" />
      </div>
    ),
    sortFn: "basic",
  }),
  helper.accessor("speedMbps", {
    id: "Speed",
    header: "Speed",
    cell: ({ getValue }) => (
      <span className="numeric whitespace-nowrap font-mono text-xs">
        {getValue() ? `${formatNumber(getValue())} MB/s` : "--"}
      </span>
    ),
    sortFn: "basic",
  }),
  helper.accessor("status", {
    header: "Status",
    cell: ({ getValue }) => <StatusBadge status={getValue()} />,
    sortFn: "text",
  }),
  helper.accessor("startedAt", {
    id: "Started",
    header: "Started",
    cell: ({ getValue }) => <span className="whitespace-nowrap text-xs text-muted-foreground">{formatDateTime(getValue())}</span>,
    sortFn: "text",
  }),
  helper.accessor("targetDirectory", {
    id: "Target",
    header: "Target",
    cell: ({ getValue }) => <span className="block max-w-xs truncate font-mono text-xs">{getValue()}</span>,
    sortFn: "text",
  }),
  helper.display({
    id: "actions",
    header: "",
    enableHiding: false,
    cell: ({ row }) => {
      const retryable = row.original.status === "failed" || row.original.status === "cancelled";
      const cancellable = row.original.status === "queued" || row.original.status === "downloading";
      if (!retryable && !cancellable) return null;
      return (
        <Button
          variant="ghost"
          size="sm"
          onClick={() =>
            toast.success(retryable ? "Retry queued" : "Download cancelled", {
              description: `${getModel(row.original.modelId)?.displayName} task state updated locally.`,
            })
          }
        >
          {retryable ? <RotateCcw /> : <Ban />}
          {retryable ? "Retry" : "Cancel"}
        </Button>
      );
    },
  }),
]);

export function DownloadsPage() {
  return (
    <PageContainer>
      <PageHeader
        title="Downloads"
        description="Track model transfers, throughput, target directories, and task failures."
      />
      <SectionPanel
        title="Transfer queue"
        description={`${downloadTasks.filter((task) => task.status === "downloading").length} active transfer`}
      >
        <DataTable
          data={downloadTasks}
          columns={columns}
          searchText={(task) => `${getModel(task.modelId)?.name} ${getServer(task.serverId)?.name} ${task.targetDirectory}`}
          searchPlaceholder="Search transfer tasks..."
          emptyTitle="No download tasks"
          emptyMessage="Start a model download from the library to populate the transfer queue."
        />
      </SectionPanel>
    </PageContainer>
  );
}
