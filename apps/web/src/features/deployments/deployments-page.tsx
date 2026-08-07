"use client";

import Link from "next/link";
import { createColumnHelper } from "@tanstack/react-table";
import { ExternalLink } from "lucide-react";

import type { Deployment } from "@/types";
import { deployments, getGpu, getModel, getServer } from "@/mocks/data";
import { DeployModelDialog } from "@/components/deployment/deploy-model-dialog";
import { DeploymentActions } from "@/components/deployment/deployment-actions";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/shared/page-header";
import { SectionPanel } from "@/components/shared/section-panel";
import { StatusBadge } from "@/components/shared/status-badge";
import { DataTable, dataTableFeatures, type DataTableColumn } from "@/components/shared/data-table";
import { buttonVariants } from "@/components/ui/button";

const helper = createColumnHelper<typeof dataTableFeatures, Deployment>();
const columns: DataTableColumn<Deployment>[] = helper.columns([
  helper.accessor("name", {
    header: "Deployment",
    cell: ({ row }) => (
      <div>
        <Link href={`/deployments/${row.original.id}`} className="font-medium hover:underline">
          {row.original.name}
        </Link>
        <div className="font-mono text-[11px] text-muted-foreground">{row.original.id}</div>
      </div>
    ),
    sortFn: "text",
  }),
  helper.accessor("modelId", {
    id: "Model",
    header: "Model",
    cell: ({ getValue }) => <span className="text-xs font-medium">{getModel(getValue())?.displayName}</span>,
    sortFn: "text",
  }),
  helper.accessor("serverId", {
    id: "Server",
    header: "Server",
    cell: ({ getValue }) => <span className="font-mono text-xs">{getServer(getValue())?.name}</span>,
    sortFn: "text",
  }),
  helper.accessor("gpuIds", {
    id: "GPU",
    header: "GPU",
    cell: ({ getValue }) => (
      <span className="whitespace-nowrap font-mono text-xs">
        {getValue().map((id) => `GPU ${getGpu(id)?.index}`).join(", ")}
      </span>
    ),
    enableSorting: false,
  }),
  helper.accessor("backend", { header: "Backend", sortFn: "text" }),
  helper.accessor("port", {
    header: "Port",
    cell: ({ getValue }) => <span className="numeric font-mono text-xs">{getValue()}</span>,
    sortFn: "basic",
  }),
  helper.accessor("status", {
    header: "Status",
    cell: ({ getValue }) => <StatusBadge status={getValue()} />,
    sortFn: "text",
  }),
  helper.accessor("uptime", {
    header: "Uptime",
    cell: ({ getValue }) => <span className="numeric font-mono text-xs">{getValue()}</span>,
    sortFn: "text",
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
    cell: ({ row }) => <DeploymentActions deployment={row.original} />,
  }),
]);

export function DeploymentsPage() {
  return (
    <PageContainer>
      <PageHeader
        title="Deployments"
        description="Control model runtime configurations, GPU placement, ports, and lifecycle state."
        actions={<DeployModelDialog />}
      />
      <SectionPanel
        title="Runtime inventory"
        description={`${deployments.filter((item) => item.status === "running").length} running / ${deployments.length} configured`}
      >
        <DataTable
          data={deployments}
          columns={columns}
          searchText={(deployment) => `${deployment.name} ${getModel(deployment.modelId)?.name} ${getServer(deployment.serverId)?.name} ${deployment.backend}`}
          searchPlaceholder="Search deployments..."
          emptyTitle="No deployments"
          emptyMessage="Create a runtime from an installed model to expose an API endpoint."
        />
      </SectionPanel>
    </PageContainer>
  );
}
