"use client";

import { Copy, ExternalLink, Play, RotateCcw, Square } from "lucide-react";
import { toast } from "sonner";

import type { Deployment } from "@/types";
import { getGpu, getModel, getServer } from "@/mocks/data";
import { DeploymentLogViewer } from "@/components/deployment/deployment-log-viewer";
import { DeploymentMetrics } from "@/components/deployment/deployment-metrics";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/shared/page-header";
import { SectionPanel } from "@/components/shared/section-panel";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";

function ConfigItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-b py-3 last:border-b-0 sm:grid sm:grid-cols-[210px_1fr] sm:gap-4">
      <dt className="text-xs font-medium text-muted-foreground">{label}</dt>
      <dd className="mt-1 break-all font-mono text-xs sm:mt-0">{value}</dd>
    </div>
  );
}

export function DeploymentDetailPage({ deployment }: { deployment: Deployment }) {
  const model = getModel(deployment.modelId);
  const server = getServer(deployment.serverId);
  const action = (label: string) =>
    toast.success(`${label} requested`, {
      description: "Lifecycle request recorded for this runtime.",
    });

  return (
    <PageContainer>
      <PageHeader
        title={deployment.name}
        description={`${model?.displayName} on ${server?.name} via ${deployment.backend}`}
        eyebrow={
          <div className="flex items-center gap-2">
            <StatusBadge status={deployment.status} />
            <span className="font-mono text-xs text-muted-foreground">{deployment.id}</span>
          </div>
        }
        actions={
          <>
            <Button variant="outline" onClick={() => action("Start")}>
              <Play /> Start
            </Button>
            <Button variant="outline" onClick={() => action("Stop")}>
              <Square /> Stop
            </Button>
            <Button variant="outline" onClick={() => action("Restart")}>
              <RotateCcw /> Restart
            </Button>
          </>
        }
      />

      <div className="mb-5 grid overflow-hidden rounded-md border bg-card sm:grid-cols-2 xl:grid-cols-5">
        {[
          ["Model", model?.displayName ?? "--"],
          ["Server", server?.name ?? "--"],
          ["GPU", deployment.gpuIds.map((id) => `GPU ${getGpu(id)?.index}`).join(", ")],
          ["Endpoint", `:${deployment.port}/v1`],
          ["Uptime", deployment.uptime],
        ].map(([label, value]) => (
          <div key={label} className="border-b p-3 last:border-b-0 sm:border-b-0 sm:border-r sm:last:border-r-0">
            <div className="text-[10px] font-semibold uppercase text-muted-foreground">{label}</div>
            <div className="mt-1 truncate font-mono text-sm font-medium">{value}</div>
          </div>
        ))}
      </div>

      <Tabs defaultValue="overview">
        <TabsList variant="line" className="w-full justify-start border-b">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="metrics">Metrics</TabsTrigger>
          <TabsTrigger value="logs">Logs</TabsTrigger>
          <TabsTrigger value="configuration">Configuration</TabsTrigger>
        </TabsList>
        <TabsContent value="overview" className="mt-4">
          <div className="grid gap-4 xl:grid-cols-2">
            <SectionPanel title="Runtime" contentClassName="px-4">
              <dl>
                <ConfigItem label="Deployment ID" value={deployment.id} />
                <ConfigItem label="Backend" value={deployment.backend} />
                <ConfigItem label="Model" value={model?.name ?? "--"} />
                <ConfigItem label="Server" value={server?.name ?? "--"} />
                <ConfigItem label="Created" value={deployment.createdAt} />
              </dl>
            </SectionPanel>
            <SectionPanel title="API endpoint" contentClassName="p-4">
              <div className="rounded-md border bg-muted/25 p-3">
                <div className="text-xs text-muted-foreground">OpenAI-compatible base URL</div>
                <div className="mt-2 flex items-center gap-2">
                  <code className="min-w-0 flex-1 truncate text-xs">{deployment.endpoint}</code>
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
                  <Button variant="outline" size="icon-sm" aria-label="Open API page">
                    <ExternalLink />
                  </Button>
                </div>
              </div>
              {deployment.errorMessage && (
                <div className="mt-3 rounded-md border border-red-200 bg-red-50 p-3 text-xs text-red-700 dark:border-red-950 dark:bg-red-950/20 dark:text-red-300">
                  {deployment.errorMessage}
                </div>
              )}
            </SectionPanel>
          </div>
        </TabsContent>
        <TabsContent value="metrics" className="mt-4">
          <SectionPanel title="Runtime metrics" description="Throughput and latency for the last hour">
            <DeploymentMetrics />
          </SectionPanel>
        </TabsContent>
        <TabsContent value="logs" className="mt-4">
          <DeploymentLogViewer />
        </TabsContent>
        <TabsContent value="configuration" className="mt-4">
          <SectionPanel title="Effective configuration" contentClassName="px-4">
            <dl>
              <ConfigItem label="Tensor parallel size" value={String(deployment.config.tensorParallelSize)} />
              <ConfigItem label="GPU memory utilization" value={String(deployment.config.gpuMemoryUtilization)} />
              <ConfigItem label="Max model length" value={String(deployment.config.maxModelLength)} />
              <ConfigItem label="Data type" value={deployment.config.dataType} />
              <ConfigItem label="Trust remote code" value={String(deployment.config.trustRemoteCode)} />
              <ConfigItem label="Extra arguments" value={deployment.config.extraArguments || "--"} />
            </dl>
          </SectionPanel>
        </TabsContent>
      </Tabs>
    </PageContainer>
  );
}
