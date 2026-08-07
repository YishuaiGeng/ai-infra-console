"use client";

import { Box, Copy, MoreHorizontal, RefreshCw, Server as ServerIcon } from "lucide-react";
import { toast } from "sonner";

import type { Server } from "@/types";
import { deployments, getModel, gpus, modelFiles } from "@/mocks/data";
import { formatDateTime, formatNumber } from "@/lib/format";
import { PageContainer } from "@/components/layout/page-container";
import { GPUCard } from "@/components/gpu/gpu-card";
import { GPUProcessTable } from "@/components/gpu/gpu-process-table";
import { PageHeader } from "@/components/shared/page-header";
import { SectionPanel } from "@/components/shared/section-panel";
import { StatusBadge } from "@/components/shared/status-badge";
import { ServerSummary } from "@/components/server/server-summary";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

function DetailItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-b py-3 last:border-b-0 sm:grid sm:grid-cols-[160px_1fr] sm:gap-4">
      <dt className="text-xs font-medium text-muted-foreground">{label}</dt>
      <dd className="mt-1 break-all font-mono text-xs sm:mt-0">{value}</dd>
    </div>
  );
}

export function ServerDetailPage({ server }: { server: Server }) {
  const serverGpus = gpus.filter((gpu) => gpu.serverId === server.id);
  const files = modelFiles.filter((file) => file.serverId === server.id);
  const serverDeployments = deployments.filter(
    (deployment) => deployment.serverId === server.id,
  );

  return (
    <PageContainer>
      <PageHeader
        title={server.name}
        description={server.description}
        eyebrow={
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={server.status} />
            <span className="font-mono text-xs text-muted-foreground">
              {server.ip} / {server.os} / agent {server.agentVersion}
            </span>
          </div>
        }
        actions={
          <>
            <Button variant="outline" onClick={() => toast.info("Mock refresh complete")}>
              <RefreshCw /> Refresh
            </Button>
            <Button variant="outline" size="icon" aria-label="More server actions">
              <MoreHorizontal />
            </Button>
          </>
        }
      />

      <ServerSummary server={server} />

      <Tabs defaultValue="overview" className="mt-5">
        <TabsList variant="line" className="w-full justify-start overflow-x-auto border-b">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="gpus">GPUs ({serverGpus.length})</TabsTrigger>
          <TabsTrigger value="models">Models ({files.length})</TabsTrigger>
          <TabsTrigger value="processes">Processes</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-4">
          <div className="grid gap-4 xl:grid-cols-[1fr_1.35fr]">
            <SectionPanel title="Host details" contentClassName="px-4">
              <dl>
                <DetailItem label="Hostname" value={server.hostname} />
                <DetailItem label="IP address" value={server.ip} />
                <DetailItem label="Operating system" value={server.os} />
                <DetailItem label="Kernel" value={server.kernel} />
                <DetailItem label="Uptime" value={server.uptime} />
                <DetailItem label="Agent version" value={server.agentVersion} />
                <DetailItem label="Last seen" value={formatDateTime(server.lastSeen)} />
              </dl>
            </SectionPanel>
            <SectionPanel title="GPU overview" description={`${serverGpus.length} devices detected`}>
              <div className="grid gap-3 p-3 sm:grid-cols-2">
                {serverGpus.map((gpu) => (
                  <GPUCard key={gpu.id} gpu={gpu} />
                ))}
              </div>
            </SectionPanel>
          </div>
        </TabsContent>

        <TabsContent value="gpus" className="mt-4">
          <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-3">
            {serverGpus.map((gpu) => (
              <GPUCard key={gpu.id} gpu={gpu} />
            ))}
          </div>
        </TabsContent>

        <TabsContent value="models" className="mt-4">
          <SectionPanel title="Installed model files">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Model</TableHead>
                    <TableHead>Format</TableHead>
                    <TableHead>Quantization</TableHead>
                    <TableHead>Size</TableHead>
                    <TableHead>Path</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {files.map((file) => (
                    <TableRow key={file.id}>
                      <TableCell className="font-medium">
                        {getModel(file.modelId)?.displayName}
                      </TableCell>
                      <TableCell>{file.format}</TableCell>
                      <TableCell className="font-mono text-xs">
                        {file.quantization}
                      </TableCell>
                      <TableCell className="numeric font-mono text-xs">
                        {formatNumber(file.sizeGb)} GB
                      </TableCell>
                      <TableCell className="max-w-md truncate font-mono text-xs">
                        {file.path}
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={file.status} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </SectionPanel>
        </TabsContent>

        <TabsContent value="processes" className="mt-4">
          <SectionPanel title="GPU processes" description="Read-only process visibility">
            <GPUProcessTable serverId={server.id} />
          </SectionPanel>
        </TabsContent>

        <TabsContent value="settings" className="mt-4">
          <div className="grid gap-4 xl:grid-cols-2">
            <SectionPanel title="Agent connection" contentClassName="p-4">
              <div className="flex items-center gap-3 rounded-md border bg-muted/20 p-3">
                <ServerIcon className="size-5 text-muted-foreground" />
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-medium">Registration token</div>
                  <div className="truncate font-mono text-xs text-muted-foreground">
                    aic_preview_********************************
                  </div>
                </div>
                <Button variant="outline" size="icon-sm" aria-label="Copy token">
                  <Copy />
                </Button>
              </div>
              <p className="mt-3 text-xs leading-5 text-muted-foreground">
                Token generation and revocation become active with the Agent phase.
              </p>
            </SectionPanel>
            <SectionPanel title="Runtime summary" contentClassName="p-4">
              <div className="flex items-center gap-3">
                <Box className="size-5 text-muted-foreground" />
                <div>
                  <div className="text-sm font-medium">
                    {serverDeployments.length} configured runtimes
                  </div>
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    {server.tags.map((tag) => (
                      <Badge key={tag} variant="secondary" className="rounded-sm">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>
            </SectionPanel>
          </div>
        </TabsContent>
      </Tabs>
    </PageContainer>
  );
}
