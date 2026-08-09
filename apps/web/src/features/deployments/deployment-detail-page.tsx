"use client";

import { Copy, ExternalLink } from "lucide-react";
import { toast } from "sonner";

import { useDeployment } from "@/hooks/use-deployments";
import { useSession } from "@/hooks/use-infrastructure";
import { formatBytes, formatDateTime } from "@/lib/format";
import { DeploymentLogViewer } from "@/components/deployment/deployment-log-viewer";
import { DeploymentMetrics } from "@/components/deployment/deployment-metrics";
import { DeploymentPrimaryActions } from "@/components/deployment/deployment-actions";
import { PageContainer } from "@/components/layout/page-container";
import { ErrorState } from "@/components/shared/error-state";
import { PageLoadingSkeleton } from "@/components/shared/loading-skeleton";
import { PageHeader } from "@/components/shared/page-header";
import { SectionPanel } from "@/components/shared/section-panel";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

function ConfigItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-b py-3 last:border-b-0 sm:grid sm:grid-cols-[210px_1fr] sm:gap-4">
      <dt className="text-xs font-medium text-muted-foreground">{label}</dt>
      <dd className="mt-1 min-w-0 break-all font-mono text-xs sm:mt-0">{value}</dd>
    </div>
  );
}

function uptimeLabel(seconds: number | null) {
  if (seconds === null) return "--";
  const days = Math.floor(seconds / 86_400);
  const hours = Math.floor((seconds % 86_400) / 3_600);
  const minutes = Math.floor((seconds % 3_600) / 60);
  return days > 0 ? `${days}d ${hours}h` : `${hours}h ${minutes}m`;
}

export function DeploymentDetailPage({ deploymentId }: { deploymentId: string }) {
  const deploymentQuery = useDeployment(deploymentId);
  const sessionQuery = useSession();
  if (deploymentQuery.isLoading) return <PageLoadingSkeleton />;
  if (deploymentQuery.isError || !deploymentQuery.data) {
    return (
      <PageContainer>
        <ErrorState
          title="Deployment unavailable"
          message={deploymentQuery.error?.message ?? "The deployment could not be loaded."}
          onRetry={() => void deploymentQuery.refetch()}
        />
      </PageContainer>
    );
  }

  const deployment = deploymentQuery.data;
  const operation = deployment.currentOperation;
  const isAdmin = sessionQuery.data?.role === "admin";

  return (
    <PageContainer>
      <PageHeader
        title={deployment.name}
        description={`${deployment.model.displayName} on ${deployment.server.name} via vLLM`}
        eyebrow={
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={deployment.status} />
            <StatusBadge status={deployment.healthStatus} />
            <span className="font-mono text-xs text-muted-foreground">{deployment.id}</span>
          </div>
        }
        actions={<DeploymentPrimaryActions deployment={deployment} isAdmin={isAdmin} />}
      />

      <div className="mb-5 grid overflow-hidden rounded-md border bg-card sm:grid-cols-2 xl:grid-cols-5">
        {[
          ["Model", deployment.model.displayName],
          ["Server", deployment.server.name],
          ["GPU", deployment.gpus.map((gpu) => `GPU ${gpu.index}`).join(", ") || "--"],
          ["Endpoint", `:${deployment.port}/v1`],
          ["Uptime", uptimeLabel(deployment.uptimeSeconds)],
        ].map(([label, value]) => (
          <div
            key={label}
            className="min-w-0 border-b p-3 last:border-b-0 sm:border-b-0 sm:border-r sm:last:border-r-0"
          >
            <div className="text-[10px] font-semibold uppercase text-muted-foreground">{label}</div>
            <div className="mt-1 truncate font-mono text-sm font-medium" title={value}>{value}</div>
          </div>
        ))}
      </div>

      <Tabs defaultValue="overview">
        <TabsList variant="line" className="w-full justify-start overflow-x-auto border-b">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="health">Health</TabsTrigger>
          <TabsTrigger value="logs">Logs</TabsTrigger>
          <TabsTrigger value="configuration">Configuration</TabsTrigger>
        </TabsList>
        <TabsContent value="overview" className="mt-4">
          <div className="grid gap-4 xl:grid-cols-2">
            <SectionPanel title="Runtime" contentClassName="px-4">
              <dl>
                <ConfigItem label="Deployment ID" value={deployment.id} />
                <ConfigItem label="Generation" value={String(deployment.generation)} />
                <ConfigItem label="Desired state" value={deployment.desiredState} />
                <ConfigItem label="Placement" value={deployment.selectionMode} />
                <ConfigItem label="Created" value={formatDateTime(deployment.createdAt)} />
              </dl>
            </SectionPanel>
            <SectionPanel title="API endpoint" contentClassName="p-4">
              <div className="rounded-md border bg-muted/25 p-3">
                <div className="text-xs text-muted-foreground">OpenAI-compatible base URL</div>
                <div className="mt-2 flex items-center gap-2">
                  <code className="min-w-0 flex-1 truncate text-xs" title={deployment.endpoint}>
                    {deployment.endpoint}
                  </code>
                  <Button
                    variant="outline"
                    size="icon-sm"
                    aria-label="Copy endpoint"
                    onClick={() => {
                      void navigator.clipboard.writeText(deployment.endpoint);
                      toast.success("Endpoint copied");
                    }}
                  >
                    <Copy />
                  </Button>
                  <a
                    href={deployment.endpoint}
                    target="_blank"
                    rel="noreferrer"
                    className={buttonVariants({ variant: "outline", size: "icon-sm" })}
                    aria-label="Open endpoint"
                  >
                    <ExternalLink />
                  </a>
                </div>
              </div>
              {operation && (
                <div className="mt-3 rounded-md border p-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-xs font-semibold">Current operation</span>
                    <StatusBadge status={operation.status} />
                  </div>
                  <div className="mt-2 font-mono text-xs text-muted-foreground">
                    {operation.action} / generation {operation.generation} / attempt {operation.attemptCount}
                  </div>
                </div>
              )}
              {deployment.errorMessage && (
                <div className="mt-3 rounded-md border border-red-200 bg-red-50 p-3 text-xs text-red-700 dark:border-red-950 dark:bg-red-950/20 dark:text-red-300">
                  {deployment.errorCode ? `${deployment.errorCode}: ` : ""}{deployment.errorMessage}
                </div>
              )}
            </SectionPanel>
          </div>
        </TabsContent>
        <TabsContent value="health" className="mt-4">
          <SectionPanel title="Runtime health" description="Latest Agent probe and reconciliation state">
            <DeploymentMetrics deployment={deployment} />
          </SectionPanel>
        </TabsContent>
        <TabsContent value="logs" className="mt-4">
          <DeploymentLogViewer deploymentId={deployment.id} />
        </TabsContent>
        <TabsContent value="configuration" className="mt-4">
          <SectionPanel title="Effective configuration" contentClassName="px-4">
            <dl>
              <ConfigItem label="Model path" value={deployment.model.path} />
              <ConfigItem label="Model size" value={formatBytes(deployment.model.sizeBytes)} />
              <ConfigItem label="Tensor parallel size" value={String(deployment.config.tensorParallelSize)} />
              <ConfigItem label="GPU memory utilization" value={String(deployment.config.gpuMemoryUtilization)} />
              <ConfigItem label="Max model length" value={String(deployment.config.maxModelLength)} />
              <ConfigItem label="Data type" value={deployment.config.dataType} />
              <ConfigItem label="Trust remote code" value={String(deployment.config.trustRemoteCode)} />
              <ConfigItem
                label="Extra arguments"
                value={deployment.config.extraArguments.join(" ") || "--"}
              />
            </dl>
          </SectionPanel>
        </TabsContent>
      </Tabs>
    </PageContainer>
  );
}
