"use client";

import { createColumnHelper } from "@tanstack/react-table";

import type { ActivityLog } from "@/types";
import { activityLogs, getServer } from "@/mocks/data";
import { formatDateTime } from "@/lib/format";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/shared/page-header";
import { SectionPanel } from "@/components/shared/section-panel";
import { StatusBadge } from "@/components/shared/status-badge";
import { DataTable, dataTableFeatures, type DataTableColumn } from "@/components/shared/data-table";

const helper = createColumnHelper<typeof dataTableFeatures, ActivityLog>();
const columns: DataTableColumn<ActivityLog>[] = helper.columns([
  helper.accessor("time", {
    header: "Time",
    cell: ({ getValue }) => <span className="whitespace-nowrap font-mono text-xs text-muted-foreground">{formatDateTime(getValue())}</span>,
    sortFn: "text",
  }),
  helper.accessor("user", { header: "User", sortFn: "text" }),
  helper.accessor("action", {
    header: "Action",
    cell: ({ getValue }) => <span className="font-mono text-xs font-medium">{getValue()}</span>,
    sortFn: "text",
  }),
  helper.accessor("resource", { header: "Resource", sortFn: "text" }),
  helper.accessor("serverId", {
    id: "Server",
    header: "Server",
    cell: ({ getValue }) => <span className="font-mono text-xs">{getValue() ? getServer(getValue() as string)?.name : "--"}</span>,
    sortFn: "text",
  }),
  helper.accessor("status", {
    header: "Status",
    cell: ({ getValue }) => <StatusBadge status={getValue()} />,
    sortFn: "text",
  }),
  helper.accessor("detail", {
    header: "Detail",
    cell: ({ getValue }) => <span className="block max-w-md truncate text-xs text-muted-foreground" title={getValue()}>{getValue()}</span>,
    sortFn: "text",
  }),
]);

export function ActivityPage() {
  return (
    <PageContainer>
      <PageHeader
        title="Activity"
        description="Audit trail for infrastructure, model transfer, and deployment lifecycle events."
      />
      <SectionPanel title="Audit log" description={`${activityLogs.length} recent events`}>
        <DataTable
          data={activityLogs}
          columns={columns}
          searchText={(log) => `${log.user} ${log.action} ${log.resource} ${log.detail} ${log.serverId ? getServer(log.serverId)?.name : ""}`}
          searchPlaceholder="Search audit events..."
          emptyTitle="No activity recorded"
          emptyMessage="Infrastructure and model operations will appear here."
        />
      </SectionPanel>
    </PageContainer>
  );
}
