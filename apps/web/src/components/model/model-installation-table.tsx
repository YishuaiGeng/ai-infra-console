"use client";

import { useState } from "react";
import { createColumnHelper } from "@tanstack/react-table";

import type { ModelInstallation } from "@/types";
import { formatBytes, formatDateTime } from "@/lib/format";
import {
  DataTable,
  dataTableFeatures,
  type DataTableColumn,
} from "@/components/shared/data-table";
import { StatusBadge } from "@/components/shared/status-badge";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ModelDetailsDialog } from "@/components/model/model-details-dialog";
import { ModelDeleteDialog } from "@/components/model/model-delete-dialog";

const helper = createColumnHelper<typeof dataTableFeatures, ModelInstallation>();

function modelColumns(
  isAdmin: boolean,
  mutableServerIds: readonly string[],
): DataTableColumn<ModelInstallation>[] {
  return helper.columns([
  helper.accessor("displayName", {
    id: "Model",
    header: "Model",
    cell: ({ row }) => (
      <div className="min-w-40">
        <div className="font-medium">{row.original.displayName}</div>
        <div className="break-all font-mono text-[11px] text-muted-foreground">
          {row.original.sourceId}
        </div>
      </div>
    ),
    sortFn: "text",
  }),
  helper.accessor("server.name", {
    id: "Server",
    header: "Server",
    cell: ({ row }) => (
      <div>
        <div className="font-mono text-xs">{row.original.server.name}</div>
        <div className="text-[11px] text-muted-foreground">
          {row.original.server.status}
        </div>
      </div>
    ),
    sortFn: "text",
  }),
  helper.accessor("sizeBytes", {
    id: "Size",
    header: "Size",
    cell: ({ getValue }) => (
      <span className="whitespace-nowrap font-mono text-xs">
        {formatBytes(getValue())}
      </span>
    ),
    sortFn: "basic",
  }),
  helper.accessor("format", {
    header: "Format",
    cell: ({ getValue }) => (
      <Badge variant="outline" className="rounded-sm uppercase">
        {getValue()}
      </Badge>
    ),
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
      <span
        className="block max-w-80 truncate font-mono text-xs"
        title={getValue()}
      >
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
  helper.accessor("lastSeenAt", {
    id: "Freshness",
    header: "Freshness",
    cell: ({ getValue }) => (
      <span className="whitespace-nowrap text-xs text-muted-foreground">
        {getValue() ? formatDateTime(getValue() as string) : "Not reported"}
      </span>
    ),
    sortFn: "text",
  }),
  helper.display({
    id: "actions",
    header: "",
    enableHiding: false,
    cell: ({ row }) => (
      <div className="flex items-center gap-1">
        <ModelDetailsDialog modelId={row.original.modelId} />
        {isAdmin &&
          row.original.status === "discovered" &&
          row.original.directoryId !== null &&
          mutableServerIds.includes(row.original.server.id) && (
          <ModelDeleteDialog model={row.original} />
        )}
      </div>
    ),
  }),
  ]);
}

export function ModelInstallationTable({
  data,
  isAdmin = false,
  mutableServerIds = [],
}: {
  data: ModelInstallation[];
  isAdmin?: boolean;
  mutableServerIds?: readonly string[];
}) {
  const [source, setSource] = useState("all");
  const [format, setFormat] = useState("all");
  const [status, setStatus] = useState("all");
  const sources = [...new Set(data.map((item) => item.source))].sort();
  const formats = [...new Set(data.map((item) => item.format))].sort();
  const filtered = data.filter(
    (item) =>
      (source === "all" || item.source === source) &&
      (format === "all" || item.format === format) &&
      (status === "all" || item.status === status),
  );

  return (
    <DataTable
      data={filtered}
      columns={modelColumns(isAdmin, mutableServerIds)}
      searchText={(item) =>
        `${item.name} ${item.displayName} ${item.sourceId} ${item.server.name} ${item.path}`
      }
      searchPlaceholder="Search model, server, or path..."
      toolbar={
        <div className="flex flex-wrap gap-2">
          <Select value={source} onValueChange={(value) => value && setSource(value)}>
            <SelectTrigger size="sm" className="w-36"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All sources</SelectItem>
              {sources.map((value) => <SelectItem key={value} value={value}>{value}</SelectItem>)}
            </SelectContent>
          </Select>
          <Select value={format} onValueChange={(value) => value && setFormat(value)}>
            <SelectTrigger size="sm" className="w-36"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All formats</SelectItem>
              {formats.map((value) => <SelectItem key={value} value={value}>{value}</SelectItem>)}
            </SelectContent>
          </Select>
          <Select value={status} onValueChange={(value) => value && setStatus(value)}>
            <SelectTrigger size="sm" className="w-36"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="discovered">Discovered</SelectItem>
              <SelectItem value="stale">Stale</SelectItem>
              <SelectItem value="missing">Missing</SelectItem>
              <SelectItem value="error">Error</SelectItem>
            </SelectContent>
          </Select>
        </div>
      }
      emptyTitle="No model installations match"
      emptyMessage="Clear one or more inventory filters to show physical locations."
    />
  );
}
