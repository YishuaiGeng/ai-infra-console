"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { createColumnHelper } from "@tanstack/react-table";
import { ExternalLink } from "lucide-react";

import type { Server } from "@/types";
import { formatDateTime, formatPercent } from "@/lib/format";
import { buttonVariants } from "@/components/ui/button";
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

const helper = createColumnHelper<typeof dataTableFeatures, Server>();

const columns: DataTableColumn<Server>[] = helper.columns([
  helper.accessor("name", {
    header: "Server",
    cell: ({ row }) => (
      <div>
        <Link
          href={`/servers/${row.original.id}`}
          className="font-medium hover:underline"
        >
          {row.original.name}
        </Link>
        <div className="font-mono text-[11px] text-muted-foreground">
          {row.original.ip}
        </div>
      </div>
    ),
    sortFn: "text",
  }),
  helper.accessor("status", {
    header: "Status",
    cell: ({ getValue }) => <StatusBadge status={getValue()} />,
    sortFn: "text",
  }),
  helper.accessor("type", {
    header: "Type",
    cell: ({ getValue }) => (
      <Badge variant="outline" className="rounded-sm capitalize">
        {getValue()}
      </Badge>
    ),
    sortFn: "text",
  }),
  helper.accessor("host", {
    header: "Host",
    cell: ({ getValue }) => (
      <span className="font-mono text-xs">{getValue()}</span>
    ),
    sortFn: "text",
  }),
  helper.accessor("gpuModel", {
    header: "GPU",
    cell: ({ row }) =>
      row.original.gpuCount === 0 ? (
        <span className="text-xs text-muted-foreground">CPU only</span>
      ) : (
        <div className="whitespace-nowrap">
          <span className="font-medium">{row.original.gpuCount}x</span>{" "}
          <span className="text-xs text-muted-foreground">
            {row.original.gpuModel}
          </span>
        </div>
      ),
    sortFn: "text",
  }),
  helper.accessor("gpuMemoryTotalGb", {
    header: "GPU Memory",
    cell: ({ getValue }) => (
      <span className="numeric font-mono text-xs">{getValue()} GB</span>
    ),
    sortFn: "basic",
  }),
  helper.accessor("cpuUsage", {
    header: "CPU",
    cell: ({ getValue }) => (
      <span className="numeric font-mono text-xs">
        {formatPercent(getValue())}
      </span>
    ),
    sortFn: "basic",
  }),
  helper.accessor("ramUsedGb", {
    id: "RAM",
    header: "RAM",
    cell: ({ row }) => (
      <span className="numeric whitespace-nowrap font-mono text-xs">
        {row.original.ramUsedGb === null
          ? "--"
          : `${row.original.ramUsedGb} / ${row.original.ramTotalGb} GB`}
      </span>
    ),
    sortFn: "basic",
  }),
  helper.accessor("modelCount", {
    header: "Models",
    cell: ({ getValue }) => <span className="numeric">{getValue()}</span>,
    sortFn: "basic",
  }),
  helper.accessor("runningCount", {
    header: "Running",
    cell: ({ getValue }) => <span className="numeric">{getValue()}</span>,
    sortFn: "basic",
  }),
  helper.accessor("lastSeen", {
    header: "Last seen",
    cell: ({ row }) => (
      <span className="whitespace-nowrap text-xs text-muted-foreground">
        {formatDateTime(row.original.lastSeen)}
      </span>
    ),
    sortFn: "text",
  }),
  helper.display({
    id: "actions",
    header: "",
    enableHiding: false,
    cell: ({ row }) => (
      <Link
        href={`/servers/${row.original.id}`}
        className={buttonVariants({ variant: "ghost", size: "icon-xs" })}
        aria-label={`Open ${row.original.name}`}
      >
        <ExternalLink />
      </Link>
    ),
  }),
]);

export function ServerTable({ data }: { data: Server[] }) {
  const [status, setStatus] = useState("all");
  const [type, setType] = useState("all");
  const filtered = useMemo(
    () =>
      data.filter(
        (server) =>
          (status === "all" || server.status === status) &&
          (type === "all" || server.type === type),
      ),
    [data, status, type],
  );

  return (
    <DataTable
      data={filtered}
      columns={columns}
      searchText={(server) =>
        [
          server.name,
          server.host,
          server.ip,
          server.gpuModel,
          server.tags.join(" "),
        ].join(" ")
      }
      searchPlaceholder="Search servers..."
      toolbar={
        <div className="flex gap-2">
          <Select value={status} onValueChange={(value) => value && setStatus(value)}>
            <SelectTrigger size="sm" className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="online">Online</SelectItem>
              <SelectItem value="offline">Offline</SelectItem>
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
        </div>
      }
      emptyTitle="No servers match"
      emptyMessage="Adjust the server name, host, or status filters."
    />
  );
}
