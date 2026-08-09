"use client";

import { Copy, Network } from "lucide-react";
import { toast } from "sonner";

import { useDeployments } from "@/hooks/use-deployments";
import { formatDateTime } from "@/lib/format";
import { ApiTestDialog } from "@/components/deployment/api-test-dialog";
import { PageContainer } from "@/components/layout/page-container";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { TableLoadingSkeleton } from "@/components/shared/loading-skeleton";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";

function copy(value: string, label: string) {
  void navigator.clipboard.writeText(value);
  toast.success(`${label} copied`);
}

export function ApiEndpointsPage() {
  const deploymentsQuery = useDeployments();
  const deployments = (deploymentsQuery.data ?? []).filter(
    (deployment) => deployment.status === "running",
  );

  return (
    <PageContainer>
      <PageHeader
        title="API endpoints"
        description="OpenAI-compatible base URLs exposed by running model deployments."
      />
      {deploymentsQuery.isLoading ? (
        <TableLoadingSkeleton />
      ) : deploymentsQuery.isError ? (
        <ErrorState
          title="API endpoints unavailable"
          message={deploymentsQuery.error.message}
          onRetry={() => void deploymentsQuery.refetch()}
        />
      ) : deployments.length === 0 ? (
        <EmptyState
          icon={Network}
          title="No running API endpoints"
          message="Start a deployment to expose an OpenAI-compatible base URL."
        />
      ) : (
      <div className="space-y-3">
        {deployments.map((deployment) => {
          return (
            <article key={deployment.id} className="overflow-hidden rounded-md border bg-card">
              <div className="flex flex-col gap-4 p-4 lg:flex-row lg:items-center">
                <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
                  <Network className="size-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-sm font-semibold">{deployment.model.displayName}</h2>
                    <StatusBadge status={deployment.healthStatus} />
                  </div>
                  <div className="mt-1 flex min-w-0 items-center gap-2">
                    <code className="truncate text-xs text-muted-foreground">{deployment.endpoint}</code>
                    <Button variant="ghost" size="icon-xs" onClick={() => copy(deployment.endpoint, "URL")} aria-label="Copy endpoint URL">
                      <Copy />
                    </Button>
                  </div>
                </div>
                <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-xs sm:grid-cols-4 lg:min-w-[470px]">
                  <div><dt className="text-muted-foreground">Server</dt><dd className="mt-0.5 font-mono">{deployment.server.name}</dd></div>
                  <div><dt className="text-muted-foreground">Backend</dt><dd className="mt-0.5 font-mono">{deployment.backend}</dd></div>
                  <div><dt className="text-muted-foreground">Port</dt><dd className="numeric mt-0.5 font-mono">{deployment.port}</dd></div>
                  <div><dt className="text-muted-foreground">Latency</dt><dd className="numeric mt-0.5 font-mono">{deployment.healthLatencyMs ?? "--"} ms</dd></div>
                </dl>
                <div className="flex shrink-0 flex-wrap items-center gap-2">
                  <Button variant="outline" size="sm" onClick={() => copy(deployment.model.sourceId, "Model name")}>
                    <Copy /> Model name
                  </Button>
                  <ApiTestDialog deployment={deployment} />
                </div>
              </div>
              <div className="border-t bg-muted/20 px-4 py-1.5 text-right font-mono text-[10px] text-muted-foreground">
                Last checked {formatDateTime(deployment.lastHealthCheckedAt ?? deployment.updatedAt)}
              </div>
            </article>
          );
        })}
      </div>
      )}
    </PageContainer>
  );
}
