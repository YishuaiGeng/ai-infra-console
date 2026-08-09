"use client";

import Link from "next/link";
import { createColumnHelper } from "@tanstack/react-table";
import { ExternalLink } from "lucide-react";

import type { Deployment } from "@/types";
import { useDeployments } from "@/hooks/use-deployments";
import { useSession } from "@/hooks/use-infrastructure";
import { DeployModelDialog } from "@/components/deployment/deploy-model-dialog";
import { DeploymentActions } from "@/components/deployment/deployment-actions";
import { PageContainer } from "@/components/layout/page-container";
import { ErrorState } from "@/components/shared/error-state";
import { PageHeader } from "@/components/shared/page-header";
import { SectionPanel } from "@/components/shared/section-panel";
import { StatusBadge } from "@/components/shared/status-badge";
import { TableLoadingSkeleton } from "@/components/shared/loading-skeleton";
import {
  DataTable,
  dataTableFeatures,
  type DataTableColumn,
} from "@/components/shared/data-table";
import { buttonVariants } from "@/components/ui/button";

const helper = createColumnHelper<typeof dataTableFeatures, Deployment>();

function uptimeLabel(seconds: number | null) {
  if (seconds === null) return "--";
  const days = Math.floor(seconds / 86_400);
  const hours = Math.floor((seconds % 86_400) / 3_600);
  const minutes = Math.floor((seconds % 3_600) / 60);
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

function deploymentColumns(isAdmin: boolean): DataTableColumn<Deployment>[] {
  return helper.columns([
    helper.accessor("name", {
      header: "Deployment",
      cell: ({ row }) => (
        <div className="min-w-44 max-w-64">
          <Link href={`/deployments/${row.original.id}`} className="font-medium hover:underline">
            {row.original.name}
          </Link>
          <div className="truncate font-mono text-[11px] text-muted-foreground">
            {row.original.id}
          </div>
        </div>
      ),
      sortFn: "text",
    }),
    helper.accessor("model.displayName", {
      id: "Model",
      header: "Model",
      cell: ({ row }) => (
        <div className="min-w-36 max-w-56">
          <div className="truncate text-xs font-medium" title={row.original.model.displayName}>
            {row.original.model.displayName}
          </div>
          <div className="truncate font-mono text-[11px] text-muted-foreground">
            {row.original.model.revision ?? "unknown revision"}
          </div>
        </div>
      ),
      sortFn: "text",
    }),
    helper.accessor("server.name", {
      id: "Server",
      header: "Server",
      cell: ({ row }) => <span className="font-mono text-xs">{row.original.server.name}</span>,
      sortFn: "text",
    }),
    helper.accessor("gpus", {
      id: "GPU",
      header: "GPU",
      cell: ({ getValue }) => (
        <span className="whitespace-nowrap font-mono text-xs">
          {getValue().map((gpu) => `GPU ${gpu.index}`).join(", ") || "--"}
        </span>
      ),
      enableSorting: false,
    }),
    helper.accessor("port", {
      header: "Port",
      cell: ({ getValue }) => <span className="numeric font-mono text-xs">{getValue()}</span>,
      sortFn: "basic",
    }),
    helper.accessor("status", {
      header: "State",
      cell: ({ row }) => (
        <div className="flex flex-wrap gap-1">
          <StatusBadge status={row.original.status} />
          <StatusBadge status={row.original.healthStatus} />
        </div>
      ),
      sortFn: "text",
    }),
    helper.accessor("uptimeSeconds", {
      header: "Uptime",
      cell: ({ getValue }) => (
        <span className="numeric whitespace-nowrap font-mono text-xs">{uptimeLabel(getValue())}</span>
      ),
      sortFn: "basic",
    }),
    helper.display({
      id: "open",
      header: "",
      enableHiding: false,
      cell: ({ row }) => (
        <Link
          href={`/deployments/${row.original.id}`}
          className={buttonVariants({ variant: "ghost", size: "icon-xs" })}
          aria-label={`Open ${row.original.name}`}
        >
          <ExternalLink />
        </Link>
      ),
    }),
    helper.display({
      id: "actions",
      header: "",
      enableHiding: false,
      cell: ({ row }) => (
        <DeploymentActions deployment={row.original} isAdmin={isAdmin} />
      ),
    }),
  ]);
}

export function DeploymentsPage() {
  const deploymentsQuery = useDeployments();
  const sessionQuery = useSession();
  const deployments = deploymentsQuery.data ?? [];
  const isAdmin = sessionQuery.data?.role === "admin";

  return (
    <PageContainer>
      <PageHeader
        title="Deployments"
        description="Control model runtime placement, health, ports, and lifecycle state."
        actions={isAdmin ? <DeployModelDialog /> : undefined}
      />
      <SectionPanel
        title="Runtime inventory"
        description={`${deployments.filter((item) => item.status === "running").length} running / ${deployments.length} configured`}
      >
        {deploymentsQuery.isLoading ? (
          <TableLoadingSkeleton />
        ) : deploymentsQuery.isError ? (
          <ErrorState
            title="Deployments unavailable"
            message={deploymentsQuery.error.message}
            onRetry={() => void deploymentsQuery.refetch()}
          />
        ) : (
          <DataTable
            data={deployments}
            columns={deploymentColumns(isAdmin)}
            searchText={(deployment) =>
              `${deployment.name} ${deployment.model.displayName} ${deployment.model.sourceId} ${deployment.server.name} ${deployment.backend}`
            }
            searchPlaceholder="Search deployments..."
            emptyTitle="No deployments"
            emptyMessage="Create a runtime from an installed model to expose an API endpoint."
          />
        )}
      </SectionPanel>
    </PageContainer>
  );
}
