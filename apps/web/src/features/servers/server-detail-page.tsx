"use client";

import { useState } from "react";
import {
  Box,
  Check,
  Copy,
  Cpu,
  KeyRound,
  RefreshCw,
  Server as ServerIcon,
  ShieldOff,
} from "lucide-react";
import { toast } from "sonner";

import {
  useRevokeAgentToken,
  useRotateAgentToken,
  useServer,
  useSession,
} from "@/hooks/use-infrastructure";
import { formatDateTime } from "@/lib/format";
import { PageContainer } from "@/components/layout/page-container";
import { GPUCard } from "@/components/gpu/gpu-card";
import { GPUProcessTable } from "@/components/gpu/gpu-process-table";
import { ModelDirectoryPanel } from "@/components/model/model-directory-panel";
import { ModelInstallationTable } from "@/components/model/model-installation-table";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { PageLoadingSkeleton } from "@/components/shared/loading-skeleton";
import { PageHeader } from "@/components/shared/page-header";
import { SectionPanel } from "@/components/shared/section-panel";
import { StatusBadge } from "@/components/shared/status-badge";
import { ServerSummary } from "@/components/server/server-summary";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

function DetailItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-b py-3 last:border-b-0 sm:grid sm:grid-cols-[160px_1fr] sm:gap-4">
      <dt className="text-xs font-medium text-muted-foreground">{label}</dt>
      <dd className="mt-1 break-all font-mono text-xs sm:mt-0">{value}</dd>
    </div>
  );
}

export function ServerDetailPage({ serverId }: { serverId: string }) {
  const detailQuery = useServer(serverId);
  const sessionQuery = useSession();
  const rotateToken = useRotateAgentToken(serverId);
  const revokeToken = useRevokeAgentToken(serverId);
  const [registrationToken, setRegistrationToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  if (detailQuery.isPending) return <PageLoadingSkeleton />;
  if (detailQuery.isError) {
    return (
      <PageContainer>
        <ErrorState
          title="Server unavailable"
          message={detailQuery.error.message}
          onRetry={() => void detailQuery.refetch()}
        />
      </PageContainer>
    );
  }

  const { server, gpus, processes, models, modelDirectories } = detailQuery.data;
  const isAdmin = sessionQuery.data?.role === "admin";

  const rotate = async () => {
    try {
      const result = await rotateToken.mutateAsync();
      setRegistrationToken(result.registration_token);
      setCopied(false);
      toast.success("Agent token rotated");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Token rotation failed.");
    }
  };

  const revoke = async () => {
    if (!window.confirm("Revoke this Agent token? The Agent will stop reporting.")) {
      return;
    }
    try {
      await revokeToken.mutateAsync();
      setRegistrationToken(null);
      toast.success("Agent token revoked");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Token revocation failed.");
    }
  };

  const copyToken = async () => {
    if (!registrationToken) return;
    await navigator.clipboard.writeText(registrationToken);
    setCopied(true);
    toast.success("Agent token copied");
  };

  return (
    <PageContainer>
      <PageHeader
        title={server.name}
        description={server.description}
        eyebrow={
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={server.status} />
            <span className="font-mono text-xs text-muted-foreground">
              {server.hostname} / {server.os} / agent {server.agentVersion}
            </span>
          </div>
        }
        actions={
          <Button
            variant="outline"
            onClick={() => void detailQuery.refetch()}
            disabled={detailQuery.isFetching}
          >
            <RefreshCw className={detailQuery.isFetching ? "animate-spin" : undefined} />
            Refresh
          </Button>
        }
      />

      <ServerSummary server={server} />

      <Tabs defaultValue="overview" className="mt-5">
        <TabsList variant="line" className="w-full justify-start overflow-x-auto border-b">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="gpus">GPUs ({gpus.length})</TabsTrigger>
          <TabsTrigger value="models">Models ({models.length})</TabsTrigger>
          <TabsTrigger value="processes">Processes ({processes.length})</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-4">
          <div className="grid gap-4 xl:grid-cols-[1fr_1.35fr]">
            <SectionPanel title="Host details" contentClassName="px-4">
              <dl>
                <DetailItem label="Hostname" value={server.hostname} />
                <DetailItem label="Host address" value={server.ip} />
                <DetailItem label="Operating system" value={server.os} />
                <DetailItem label="Kernel" value={server.kernel} />
                <DetailItem label="Uptime" value={server.uptime} />
                <DetailItem label="Agent version" value={server.agentVersion} />
                <DetailItem label="Last seen" value={formatDateTime(server.lastSeen)} />
              </dl>
            </SectionPanel>
            <SectionPanel title="GPU overview" description={`${gpus.length} devices detected`}>
              {gpus.length ? (
                <div className="grid gap-3 p-3 sm:grid-cols-2">
                  {gpus.map((gpu) => (
                    <GPUCard key={gpu.id} gpu={gpu} />
                  ))}
                </div>
              ) : (
                <EmptyState
                  icon={Cpu}
                  title="CPU-only server"
                  message="This Agent is healthy and currently reports no GPU devices."
                />
              )}
            </SectionPanel>
          </div>
        </TabsContent>

        <TabsContent value="gpus" className="mt-4">
          {gpus.length ? (
            <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-3">
              {gpus.map((gpu) => (
                <GPUCard key={gpu.id} gpu={gpu} />
              ))}
            </div>
          ) : (
            <SectionPanel title="GPU inventory">
              <EmptyState
                icon={Cpu}
                title="No GPUs detected"
                message="The server remains available for CPU workloads and model storage."
              />
            </SectionPanel>
          )}
        </TabsContent>

        <TabsContent value="models" className="mt-4 space-y-4">
          <ModelDirectoryPanel
            serverId={server.id}
            directories={modelDirectories}
            isAdmin={isAdmin}
          />
          <SectionPanel
            title="Installed model files"
            description={`${models.length} physical locations reported by this Agent`}
          >
            {models.length ? (
              <ModelInstallationTable data={models} />
            ) : (
              <EmptyState
                icon={Box}
                title="No models discovered"
                message="The configured roots are empty or have not completed a successful scan."
              />
            )}
          </SectionPanel>
        </TabsContent>

        <TabsContent value="processes" className="mt-4">
          <SectionPanel title="GPU processes" description="Read-only process visibility">
            <GPUProcessTable processes={processes} />
          </SectionPanel>
        </TabsContent>

        <TabsContent value="settings" className="mt-4">
          <div className="grid gap-4 xl:grid-cols-2">
            <SectionPanel title="Agent connection" contentClassName="p-4">
              {registrationToken && (
                <div className="mb-4 flex items-center gap-2">
                  <Input
                    value={registrationToken}
                    readOnly
                    className="font-mono text-xs"
                    aria-label="New Agent token"
                  />
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={copyToken}
                    aria-label="Copy new Agent token"
                  >
                    {copied ? <Check /> : <Copy />}
                  </Button>
                </div>
              )}
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  onClick={rotate}
                  disabled={!isAdmin || rotateToken.isPending}
                >
                  <KeyRound /> Rotate token
                </Button>
                <Button
                  variant="destructive"
                  onClick={revoke}
                  disabled={!isAdmin || revokeToken.isPending}
                >
                  <ShieldOff /> Revoke token
                </Button>
              </div>
              <p className="mt-3 text-xs leading-5 text-muted-foreground">
                {isAdmin
                  ? "A rotated token is shown once. Revocation blocks the next Agent report."
                  : "Viewer accounts can inspect connection state but cannot change Agent credentials."}
              </p>
            </SectionPanel>
            <SectionPanel title="Runtime summary" contentClassName="p-4">
              <div className="flex items-center gap-3">
                <ServerIcon className="size-5 text-muted-foreground" />
                <div>
                  <div className="text-sm font-medium">
                    {server.agentVersion === "Not connected"
                      ? "Awaiting first Agent report"
                      : `Agent ${server.agentVersion}`}
                  </div>
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    {server.tags.length ? (
                      server.tags.map((tag) => (
                        <Badge key={tag} variant="secondary" className="rounded-sm">
                          {tag}
                        </Badge>
                      ))
                    ) : (
                      <span className="text-xs text-muted-foreground">No tags</span>
                    )}
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
