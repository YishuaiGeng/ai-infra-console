"use client";

import { useEffect } from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTheme } from "next-themes";
import { toast } from "sonner";
import { z } from "zod";

import type { SystemSettings } from "@/types";
import { useSystemSettings, useUpdateSystemSettings } from "@/hooks/use-settings";
import { cn } from "@/lib/utils";
import { PageContainer } from "@/components/layout/page-container";
import { ErrorState } from "@/components/shared/error-state";
import { PageLoadingSkeleton } from "@/components/shared/loading-skeleton";
import { PageHeader } from "@/components/shared/page-header";
import { SectionPanel } from "@/components/shared/section-panel";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const settingsSchema = z.object({
  consoleName: z.string().min(2),
  timezone: z.string().min(2),
  language: z.string().min(2),
  heartbeatInterval: z.number().int().min(5).max(300),
  offlineThreshold: z.number().int().min(10).max(900),
  metricsRetentionDays: z.number().int().min(1).max(3650),
  defaultModelDirectory: z.string().startsWith("/"),
  defaultBackend: z.enum(["vLLM", "Ollama"]),
  defaultPort: z.number().int().min(1024).max(65535),
  defaultGpuMemoryUtilization: z.number().min(0.1).max(1),
  requireDeleteConfirmation: z.boolean(),
  auditLogRetentionDays: z.number().int().min(1).max(3650),
});
type SettingsValues = z.infer<typeof settingsSchema>;

const fallbackSettings: SystemSettings = {
  consoleName: "AI Infra Console",
  timezone: "Asia/Shanghai",
  language: "English",
  heartbeatInterval: 10,
  offlineThreshold: 30,
  metricsRetentionDays: 14,
  defaultModelDirectory: "/data/models",
  defaultBackend: "vLLM",
  defaultPort: 8000,
  defaultGpuMemoryUtilization: 0.9,
  requireDeleteConfirmation: true,
  auditLogRetentionDays: 90,
};

function Field({ label, id, children, hint }: { label: string; id: string; children: React.ReactNode; hint?: string }) {
  return (
    <div className="grid gap-2 border-b py-4 last:border-b-0 sm:grid-cols-[220px_1fr] sm:gap-6">
      <div><Label htmlFor={id}>{label}</Label>{hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}</div>
      <div className="max-w-md">{children}</div>
    </div>
  );
}

export function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const settingsQuery = useSystemSettings();
  const updateSettings = useUpdateSystemSettings();
  const { register, handleSubmit, control, setValue, reset } = useForm<SettingsValues>({
    resolver: zodResolver(settingsSchema),
    defaultValues: fallbackSettings,
  });
  useEffect(() => {
    if (settingsQuery.data) reset(settingsQuery.data);
  }, [reset, settingsQuery.data]);
  const requireDeleteConfirmation = useWatch({
    control,
    name: "requireDeleteConfirmation",
  });
  const defaultBackend = useWatch({ control, name: "defaultBackend" });
  const save = async (values: SettingsValues) => {
    await updateSettings.mutateAsync(values);
    toast.success("Settings saved");
  };

  if (settingsQuery.isLoading) return <PageLoadingSkeleton />;
  if (settingsQuery.isError) {
    return (
      <PageContainer>
        <PageHeader title="Settings" description="Console defaults for monitoring, model storage, deployment, and security." />
        <ErrorState
          title="Settings unavailable"
          message={settingsQuery.error.message}
          onRetry={() => void settingsQuery.refetch()}
        />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader title="Settings" description="Console defaults for monitoring, model storage, deployment, and security." />
      <form onSubmit={handleSubmit(save)}>
        <Tabs defaultValue="general">
          <TabsList variant="line" className="w-full justify-start overflow-x-auto border-b">
            <TabsTrigger value="general">General</TabsTrigger>
            <TabsTrigger value="monitoring">Monitoring</TabsTrigger>
            <TabsTrigger value="models">Models</TabsTrigger>
            <TabsTrigger value="deployment">Deployment</TabsTrigger>
            <TabsTrigger value="security">Security</TabsTrigger>
          </TabsList>
          <TabsContent value="general" className="mt-4">
            <SectionPanel title="General settings" contentClassName="px-4">
              <Field label="Console name" id="console-name"><Input id="console-name" {...register("consoleName")} /></Field>
              <Field label="Timezone" id="timezone"><Input id="timezone" className="font-mono" {...register("timezone")} /></Field>
              <Field label="Theme" id="theme">
                <div id="theme" className="grid grid-cols-3 rounded-md bg-muted p-1">
                  {["light", "dark", "system"].map((value) => (
                    <button
                      key={value}
                      type="button"
                      suppressHydrationWarning
                      onClick={() => setTheme(value)}
                      className={cn(
                        "h-8 rounded-sm text-sm capitalize text-muted-foreground",
                        theme === value &&
                          "bg-background text-foreground shadow-sm",
                      )}
                    >
                      {value}
                    </button>
                  ))}
                </div>
              </Field>
            </SectionPanel>
          </TabsContent>
          <TabsContent value="monitoring" className="mt-4">
            <SectionPanel title="Monitoring settings" contentClassName="px-4">
              <Field label="Heartbeat interval" id="heartbeat" hint="Seconds between agent heartbeats"><Input id="heartbeat" type="number" {...register("heartbeatInterval", { valueAsNumber: true })} /></Field>
              <Field label="Offline threshold" id="offline-threshold" hint="Seconds without a heartbeat"><Input id="offline-threshold" type="number" {...register("offlineThreshold", { valueAsNumber: true })} /></Field>
              <Field label="Metrics retention" id="metrics-retention"><Input id="metrics-retention" type="number" {...register("metricsRetentionDays", { valueAsNumber: true })} /></Field>
            </SectionPanel>
          </TabsContent>
          <TabsContent value="models" className="mt-4">
            <SectionPanel title="Model settings" contentClassName="px-4">
              <Field label="Default model directory" id="model-directory"><Input id="model-directory" className="font-mono" {...register("defaultModelDirectory")} /></Field>
              <Field label="Hugging Face endpoint" id="hf-endpoint"><Input id="hf-endpoint" className="font-mono" defaultValue="https://huggingface.co" /></Field>
              <Field label="ModelScope endpoint" id="ms-endpoint"><Input id="ms-endpoint" className="font-mono" defaultValue="https://modelscope.cn" /></Field>
            </SectionPanel>
          </TabsContent>
          <TabsContent value="deployment" className="mt-4">
            <SectionPanel title="Deployment defaults" contentClassName="px-4">
              <Field label="Default port" id="default-port"><Input id="default-port" type="number" {...register("defaultPort", { valueAsNumber: true })} /></Field>
              <Field label="GPU memory utilization" id="default-gpu-memory"><Input id="default-gpu-memory" type="number" min="0.1" max="1" step="0.05" {...register("defaultGpuMemoryUtilization", { valueAsNumber: true })} /></Field>
              <Field label="Default backend" id="default-backend"><Input id="default-backend" value={defaultBackend} readOnly {...register("defaultBackend")} /></Field>
            </SectionPanel>
          </TabsContent>
          <TabsContent value="security" className="mt-4">
            <SectionPanel title="Security settings" contentClassName="px-4">
              <Field label="Confirm model deletion" id="delete-confirmation" hint="Require explicit confirmation before destructive model operations">
                <Switch id="delete-confirmation" checked={requireDeleteConfirmation} onCheckedChange={(value) => setValue("requireDeleteConfirmation", value)} />
              </Field>
              <Field label="Audit log retention" id="audit-retention"><Input id="audit-retention" type="number" {...register("auditLogRetentionDays", { valueAsNumber: true })} /></Field>
              <Field label="Agent action policy" id="agent-policy"><Input id="agent-policy" value="Allowlisted operations only" readOnly /></Field>
            </SectionPanel>
          </TabsContent>
        </Tabs>
        <div className="mt-4 flex justify-end">
          <Button type="submit" disabled={updateSettings.isPending}>
            {updateSettings.isPending ? "Saving..." : "Save settings"}
          </Button>
        </div>
      </form>
    </PageContainer>
  );
}
