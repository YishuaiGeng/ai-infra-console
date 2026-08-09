"use client";

import { Copy, Gauge, Network } from "lucide-react";
import { toast } from "sonner";

import type { Deployment } from "@/types";
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

function endpointPath(endpoint: string, path: string) {
  return `${endpoint.replace(/\/$/, "")}${path}`;
}

function EndpointMetadata({ deployment }: { deployment: Deployment }) {
  const checkedAt = deployment.lastHealthCheckedAt ?? deployment.updatedAt;

  return (
    <div className="grid gap-3 border-t bg-muted/20 p-4 text-xs md:grid-cols-[1.2fr_1fr]">
      <div className="min-w-0 space-y-2">
        <div className="flex items-center gap-2 font-medium text-foreground">
          <Network className="size-3.5 text-muted-foreground" />
          OpenAI-compatible paths
        </div>
        <div className="grid gap-1.5 font-mono text-[11px] text-muted-foreground">
          <code className="break-all rounded-sm bg-background/70 px-2 py-1">
            {endpointPath(deployment.endpoint, "/models")}
          </code>
          <code className="break-all rounded-sm bg-background/70 px-2 py-1">
            {endpointPath(deployment.endpoint, "/chat/completions")}
          </code>
        </div>
      </div>
      <dl className="grid min-w-0 grid-cols-2 gap-x-4 gap-y-2 md:grid-cols-3">
        <div className="min-w-0">
          <dt className="text-muted-foreground">Model</dt>
          <dd className="mt-0.5 truncate font-mono" title={deployment.model.sourceId}>
            {deployment.model.sourceId}
          </dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Health</dt>
          <dd className="mt-0.5">
            <StatusBadge status={deployment.healthStatus} />
          </dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Latency</dt>
          <dd className="numeric mt-0.5 font-mono">
            {deployment.healthLatencyMs === null
              ? "--"
              : `${Math.round(deployment.healthLatencyMs)} ms`}
          </dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Status</dt>
          <dd className="mt-0.5">
            <StatusBadge status={deployment.status} />
          </dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Last checked</dt>
          <dd className="mt-0.5 font-mono">{formatDateTime(checkedAt)}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Generation</dt>
          <dd className="numeric mt-0.5 font-mono">{deployment.generation}</dd>
        </div>
      </dl>
    </div>
  );
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
                <div className="grid gap-4 p-4 xl:grid-cols-[1fr_auto_auto] xl:items-center">
                  <div className="flex min-w-0 gap-3">
                    <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
                      <Network className="size-4" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <h2 className="min-w-0 truncate text-sm font-semibold">
                          {deployment.model.displayName}
                        </h2>
                        <StatusBadge status={deployment.healthStatus} />
                      </div>
                      <div className="mt-1 flex min-w-0 items-start gap-2">
                        <code className="min-w-0 break-all text-xs text-muted-foreground">
                          {deployment.endpoint}
                        </code>
                        <Button
                          variant="ghost"
                          size="icon-xs"
                          onClick={() => copy(deployment.endpoint, "URL")}
                          aria-label={`Copy endpoint URL for ${deployment.name}`}
                        >
                          <Copy />
                        </Button>
                      </div>
                    </div>
                  </div>
                  <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-xs sm:grid-cols-4 xl:min-w-[500px]">
                    <div className="min-w-0">
                      <dt className="text-muted-foreground">Server</dt>
                      <dd className="mt-0.5 truncate font-mono" title={deployment.server.name}>
                        {deployment.server.name}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-muted-foreground">Backend</dt>
                      <dd className="mt-0.5 font-mono">{deployment.backend}</dd>
                    </div>
                    <div>
                      <dt className="text-muted-foreground">Port</dt>
                      <dd className="numeric mt-0.5 font-mono">{deployment.port}</dd>
                    </div>
                    <div>
                      <dt className="text-muted-foreground">Health source</dt>
                      <dd className="mt-0.5 flex items-center gap-1 font-mono">
                        <Gauge className="size-3 text-muted-foreground" />
                        Agent
                      </dd>
                    </div>
                  </dl>
                  <div className="flex shrink-0 flex-wrap items-center gap-2 xl:justify-end">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => copy(deployment.model.sourceId, "Model name")}
                    >
                      <Copy /> Model name
                    </Button>
                    <ApiTestDialog deployment={deployment} />
                  </div>
                </div>
                <EndpointMetadata deployment={deployment} />
              </article>
            );
          })}
        </div>
      )}
    </PageContainer>
  );
}
