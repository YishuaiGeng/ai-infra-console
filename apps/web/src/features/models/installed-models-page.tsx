"use client";

import { createColumnHelper } from "@tanstack/react-table";

import type { ModelFile } from "@/types";
import { getModel, getServer, modelFiles } from "@/mocks/data";
import { formatNumber } from "@/lib/format";
import { DeployModelDialog } from "@/components/deployment/deploy-model-dialog";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/shared/page-header";
import { SectionPanel } from "@/components/shared/section-panel";
import { StatusBadge } from "@/components/shared/status-badge";
import { DataTable, dataTableFeatures, type DataTableColumn } from "@/components/shared/data-table";

const helper = createColumnHelper<typeof dataTableFeatures, ModelFile>();
const columns: DataTableColumn<ModelFile>[] = helper.columns([
  helper.accessor("modelId", {
    id: "Model",
    header: "Model",
    cell: ({ getValue }) => {
      const model = getModel(getValue());
      return (
        <div>
          <div className="font-medium">{model?.displayName}</div>
          <div className="font-mono text-[11px] text-muted-foreground">
            {model?.parameters} / {model?.type}
          </div>
        </div>
      );
    },
    sortFn: "text",
  }),
  helper.accessor("serverId", {
    id: "Server",
    header: "Server",
    cell: ({ getValue }) => (
      <span className="font-mono text-xs">{getServer(getValue())?.name}</span>
    ),
    sortFn: "text",
  }),
  helper.accessor("sizeGb", {
    id: "Size",
    header: "Size",
    cell: ({ getValue }) => (
      <span className="numeric font-mono text-xs">{formatNumber(getValue())} GB</span>
    ),
    sortFn: "basic",
  }),
  helper.accessor("format", {
    header: "Format",
    sortFn: "text",
  }),
  helper.accessor("quantization", {
    header: "Quantization",
    cell: ({ getValue }) => <span className="font-mono text-xs">{getValue()}</span>,
    sortFn: "text",
  }),
  helper.accessor("path", {
    header: "Path",
    cell: ({ getValue }) => (
      <span className="block max-w-sm truncate font-mono text-xs" title={getValue()}>
        {getValue()}
      </span>
    ),
    sortFn: "text",
  }),
  helper.accessor("status", {
    header: "Status",
    cell: ({ getValue }) => <StatusBadge status={getValue()} />,
    sortFn: "text",
  }),
  helper.accessor("deployments", {
    header: "Deployments",
    cell: ({ getValue }) => <span className="numeric">{getValue()}</span>,
    sortFn: "basic",
  }),
  helper.display({
    id: "actions",
    header: "",
    enableHiding: false,
    cell: ({ row }) => <DeployModelDialog defaultModelId={row.original.modelId} />,
  }),
]);

export function InstalledModelsPage() {
  return (
    <PageContainer>
      <PageHeader
        title="Installed models"
        description="Track every physical model location, format, revision, and active deployment across servers."
        actions={<DeployModelDialog />}
      />
      <SectionPanel
        title="Model file inventory"
        description={`${modelFiles.length} installations across multiple server paths`}
      >
        <DataTable
          data={modelFiles}
          columns={columns}
          searchText={(file) => `${getModel(file.modelId)?.name} ${getServer(file.serverId)?.name} ${file.path} ${file.format}`}
          searchPlaceholder="Search model, server, or path..."
          emptyTitle="No installed models"
          emptyMessage="Download a model definition to an online server to create an installation."
        />
      </SectionPanel>
    </PageContainer>
  );
}
