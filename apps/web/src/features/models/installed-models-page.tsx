"use client";

import { Box } from "lucide-react";

import {
  useModelInstallations,
  useModelInventorySummary,
} from "@/hooks/use-model-inventory";
import { useSession } from "@/hooks/use-infrastructure";
import { useDownloadTargets } from "@/hooks/use-downloads";
import { formatBytes } from "@/lib/format";
import { ModelInstallationTable } from "@/components/model/model-installation-table";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { TableLoadingSkeleton } from "@/components/shared/loading-skeleton";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/shared/page-header";
import { SectionPanel } from "@/components/shared/section-panel";

export function InstalledModelsPage() {
  const modelsQuery = useModelInstallations();
  const summaryQuery = useModelInventorySummary();
  const sessionQuery = useSession();
  const targetsQuery = useDownloadTargets();

  return (
    <PageContainer>
      <PageHeader
        title="Installed models"
        description="Track every physical model location, format, revision, and scan state across servers."
      />
      {modelsQuery.isPending || summaryQuery.isPending ? (
        <SectionPanel title="Model file inventory" description="Loading Agent scans">
          <TableLoadingSkeleton />
        </SectionPanel>
      ) : modelsQuery.isError || summaryQuery.isError ? (
        <ErrorState
          title="Model inventory unavailable"
          message={(modelsQuery.error ?? summaryQuery.error)?.message ?? "The request failed."}
          onRetry={() => {
            void modelsQuery.refetch();
            void summaryQuery.refetch();
          }}
        />
      ) : modelsQuery.data.length === 0 ? (
        <SectionPanel title="Model file inventory" description="No Agent models reported">
          <EmptyState
            icon={Box}
            title="No installed models"
            message="Configure an allowed model directory on an Agent or start a local Ollama service."
          />
        </SectionPanel>
      ) : (
        <SectionPanel
          title="Model file inventory"
          description={`${summaryQuery.data.model_count} logical models / ${summaryQuery.data.installation_count} locations / ${formatBytes(summaryQuery.data.total_size)}`}
        >
          <ModelInstallationTable
            data={modelsQuery.data}
            isAdmin={sessionQuery.data?.role === "admin"}
            mutableServerIds={(targetsQuery.data ?? []).map((target) => target.server.id)}
          />
        </SectionPanel>
      )}
    </PageContainer>
  );
}
