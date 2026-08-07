"use client";

import { createColumnHelper } from "@tanstack/react-table";
import { Ban, LoaderCircle, RotateCcw } from "lucide-react";
import { toast } from "sonner";

import type { ModelDownloadTask } from "@/types";
import {
  useCancelDownload,
  useDownloads,
  useRetryDownload,
} from "@/hooks/use-downloads";
import { useSession } from "@/hooks/use-infrastructure";
import { pendingDownloadTaskId } from "@/lib/api/downloads";
import { formatBytes, formatDateTime } from "@/lib/format";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/shared/page-header";
import { ErrorState } from "@/components/shared/error-state";
import { SectionPanel } from "@/components/shared/section-panel";
import { StatusBadge } from "@/components/shared/status-badge";
import {
  DataTable,
  dataTableFeatures,
  type DataTableColumn,
} from "@/components/shared/data-table";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

const helper = createColumnHelper<typeof dataTableFeatures, ModelDownloadTask>();

function taskColumns({
  isAdmin,
  busyTaskId,
  onAction,
}: {
  isAdmin: boolean;
  busyTaskId: string | null;
  onAction: (task: ModelDownloadTask, action: "cancel" | "retry") => void;
}): DataTableColumn<ModelDownloadTask>[] {
  return helper.columns([
    helper.accessor("sourceId", {
      id: "Model",
      header: "Model",
      cell: ({ row }) => (
        <div className="min-w-40 max-w-64">
          <div className="break-all font-medium">{row.original.sourceId}</div>
          <div
            className="truncate font-mono text-[11px] text-muted-foreground"
            title={`${row.original.provider} / ${row.original.revision}`}
          >
            {row.original.provider} / {row.original.revision}
          </div>
          <div
            className="truncate font-mono text-[11px] text-muted-foreground"
            title={row.original.targetPath}
          >
            {row.original.targetPath}
          </div>
        </div>
      ),
      sortFn: "text",
    }),
    helper.accessor("server.name", {
      id: "Server",
      header: "Server",
      cell: ({ row }) => (
        <span className="font-mono text-xs">{row.original.server.name}</span>
      ),
      sortFn: "text",
    }),
    helper.accessor("progress", {
      header: "Progress",
      cell: ({ row }) => {
        const task = row.original;
        const value = task.progress ?? (task.status === "completed" ? 100 : 0);
        return (
          <div className="min-w-40">
            <div className="mb-1 flex justify-between gap-3 font-mono text-[11px]">
              <span className="whitespace-nowrap">
                {task.progress === null ? "--" : `${Math.round(task.progress)}%`}
                <span className="text-muted-foreground">
                  {` / ${
                    task.speedBytesPerSecond === null
                      ? "--"
                      : `${formatBytes(task.speedBytesPerSecond)}/s`
                  }`}
                </span>
              </span>
              <span className="whitespace-nowrap text-muted-foreground">
                {formatBytes(task.downloadedSize)} / {formatBytes(task.totalSize)}
              </span>
            </div>
            <Progress value={value} className="h-1.5" />
          </div>
        );
      },
      sortFn: "basic",
    }),
    helper.accessor("status", {
      header: "Status",
      cell: ({ row }) => (
        <div>
          <StatusBadge status={row.original.status} />
          {row.original.errorMessage && (
            <div
              className="mt-1 max-w-56 truncate text-[11px] text-destructive"
              title={row.original.errorMessage}
            >
              {row.original.errorCode
                ? `${row.original.errorCode}: ${row.original.errorMessage}`
                : row.original.errorMessage}
            </div>
          )}
        </div>
      ),
      sortFn: "text",
    }),
    helper.accessor("createdAt", {
      id: "Run",
      header: "Run",
      cell: ({ row }) => (
        <div className="whitespace-nowrap text-xs">
          <div className="font-mono">Attempt {row.original.attemptCount}</div>
          <div className="text-[11px] text-muted-foreground">
            {formatDateTime(row.original.createdAt)}
          </div>
        </div>
      ),
      sortFn: "basic",
    }),
    helper.display({
      id: "actions",
      header: "",
      enableHiding: false,
      cell: ({ row }) => {
        if (!isAdmin) return null;
        const retryable = ["failed", "cancelled"].includes(row.original.status);
        const cancellable = ["queued", "downloading"].includes(row.original.status);
        if (!retryable && !cancellable) return null;
        const action = retryable ? "retry" : "cancel";
        return (
          <Button
            variant="ghost"
            size="icon-xs"
            onClick={() => onAction(row.original, action)}
            disabled={busyTaskId === row.original.id}
            aria-label={`${retryable ? "Retry" : "Cancel"} ${row.original.sourceId}`}
          >
            {busyTaskId === row.original.id ? (
              <LoaderCircle className="animate-spin" />
            ) : retryable ? (
              <RotateCcw />
            ) : (
              <Ban />
            )}
          </Button>
        );
      },
    }),
  ]);
}

export function DownloadsPage() {
  const downloadsQuery = useDownloads();
  const sessionQuery = useSession();
  const cancelDownload = useCancelDownload();
  const retryDownload = useRetryDownload();
  const tasks = downloadsQuery.data ?? [];
  const busyTaskId = pendingDownloadTaskId(
    cancelDownload.isPending,
    cancelDownload.variables,
    retryDownload.isPending,
    retryDownload.variables,
  );
  const activeCount = tasks.filter((task) =>
    ["queued", "downloading", "cancelling"].includes(task.status),
  ).length;

  const act = async (task: ModelDownloadTask, action: "cancel" | "retry") => {
    try {
      const updated = await (action === "cancel"
        ? cancelDownload.mutateAsync(task.id)
        : retryDownload.mutateAsync(task.id));
      toast.success(action === "cancel" ? "Cancellation requested" : "Download requeued", {
        description: `${updated.sourceId} / ${updated.status}`,
      });
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Task update failed.");
    }
  };

  return (
    <PageContainer>
      <PageHeader
        title="Downloads"
        description="Track model transfers, throughput, target directories, and task failures."
      />
      {downloadsQuery.isError ? (
        <ErrorState
          title="Download queue unavailable"
          message={downloadsQuery.error.message}
          onRetry={() => void downloadsQuery.refetch()}
        />
      ) : (
        <SectionPanel
          title="Transfer queue"
          description={
            downloadsQuery.isPending
              ? "Loading transfer tasks"
              : `${activeCount} active ${activeCount === 1 ? "transfer" : "transfers"}`
          }
        >
          {downloadsQuery.isPending ? (
            <div className="flex min-h-48 items-center justify-center text-muted-foreground">
              <LoaderCircle className="size-5 animate-spin" />
            </div>
          ) : (
            <DataTable
              data={tasks}
              columns={taskColumns({
                isAdmin: sessionQuery.data?.role === "admin",
                busyTaskId,
                onAction: (task, action) => void act(task, action),
              })}
              searchText={(task) =>
                `${task.sourceId} ${task.provider} ${task.server.name} ${task.targetPath} ${task.status}`
              }
              searchPlaceholder="Search transfer tasks..."
              emptyTitle="No download tasks"
              emptyMessage="Start a model download from the library to populate the transfer queue."
            />
          )}
        </SectionPanel>
      )}
    </PageContainer>
  );
}
