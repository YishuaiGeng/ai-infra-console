"use client";

import { Server } from "lucide-react";

import { useServers } from "@/hooks/use-infrastructure";
import { AddServerDialog } from "@/components/server/add-server-dialog";
import { ServerTable } from "@/components/server/server-table";
import { PageContainer } from "@/components/layout/page-container";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { TableLoadingSkeleton } from "@/components/shared/loading-skeleton";
import { PageHeader } from "@/components/shared/page-header";
import { SectionPanel } from "@/components/shared/section-panel";

export function ServersPage() {
  const serversQuery = useServers();
  const servers = serversQuery.data ?? [];

  return (
    <PageContainer>
      <PageHeader
        title="Servers"
        description="Manage local lab nodes and cloud GPU hosts from one inventory."
        actions={<AddServerDialog />}
      />
      <SectionPanel
        title="Server inventory"
        description="Search, filter, sort, and inspect registered infrastructure"
      >
        {serversQuery.isPending ? (
          <TableLoadingSkeleton />
        ) : serversQuery.isError ? (
          <ErrorState
            title="Server inventory unavailable"
            message={serversQuery.error.message}
            onRetry={() => void serversQuery.refetch()}
          />
        ) : servers.length === 0 ? (
          <EmptyState
            icon={Server}
            title="No servers registered"
            message="Create a registration, then start the Agent on the target host."
            action={<AddServerDialog />}
          />
        ) : (
          <ServerTable data={servers} />
        )}
      </SectionPanel>
    </PageContainer>
  );
}
