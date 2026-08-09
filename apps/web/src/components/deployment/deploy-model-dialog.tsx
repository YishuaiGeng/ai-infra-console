"use client";

import { useEffect, useMemo, useState } from "react";
import { Controller, useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ChevronDown, LoaderCircle, Rocket, ShieldAlert } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import { useCreateDeployment, useDeploymentTargets } from "@/hooks/use-deployments";
import { formatBytes } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";

const deploySchema = z
  .object({
    name: z
      .string()
      .min(3, "Use at least 3 characters.")
      .max(128)
      .regex(
        /^[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9]$/,
        "Use letters, numbers, dots, underscores, or dashes and end alphanumeric.",
      ),
    serverId: z.string().min(1, "Select a server."),
    modelFileId: z.string().min(1, "Select an installed model."),
    selectionMode: z.enum(["automatic", "manual"]),
    gpuIds: z.array(z.string()),
    port: z.number().int().min(1024).max(65535),
    tensorParallelSize: z.number().int().min(1).max(8),
    gpuMemoryUtilization: z.number().min(0.1).max(1),
    maxModelLength: z.number().int().min(1024).max(1_048_576),
    dataType: z.enum(["auto", "float16", "bfloat16"]),
    trustRemoteCode: z.boolean(),
    enablePrefixCaching: z.boolean(),
    disableLogRequests: z.boolean(),
    enforceEager: z.boolean(),
    enableChunkedPrefill: z.boolean(),
    limitSequences: z.boolean(),
    maxNumSeqs: z.number().int().min(1).max(65_536),
  })
  .refine(
    (value) => value.selectionMode === "automatic" || value.gpuIds.length > 0,
    { message: "Select at least one GPU.", path: ["gpuIds"] },
  )
  .refine(
    (value) =>
      value.selectionMode === "automatic" ||
      value.gpuIds.length === value.tensorParallelSize,
    {
      message: "Manual GPU count must match tensor parallel size.",
      path: ["gpuIds"],
    },
  );

type DeployValues = z.infer<typeof deploySchema>;

const defaults: DeployValues = {
  name: "",
  serverId: "",
  modelFileId: "",
  selectionMode: "automatic",
  gpuIds: [],
  port: 8001,
  tensorParallelSize: 1,
  gpuMemoryUtilization: 0.9,
  maxModelLength: 32768,
  dataType: "auto",
  trustRemoteCode: false,
  enablePrefixCaching: false,
  disableLogRequests: false,
  enforceEager: false,
  enableChunkedPrefill: false,
  limitSequences: false,
  maxNumSeqs: 256,
};

function extraArguments(values: DeployValues) {
  const result: string[] = [];
  if (values.enablePrefixCaching) result.push("--enable-prefix-caching");
  if (values.disableLogRequests) result.push("--disable-log-requests");
  if (values.enforceEager) result.push("--enforce-eager");
  if (values.enableChunkedPrefill) result.push("--enable-chunked-prefill");
  if (values.limitSequences) result.push("--max-num-seqs", String(values.maxNumSeqs));
  return result;
}

export function DeployModelDialog({ defaultModelId }: { defaultModelId?: string }) {
  const [open, setOpen] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const targetsQuery = useDeploymentTargets();
  const createDeployment = useCreateDeployment();
  const {
    control,
    register,
    handleSubmit,
    reset,
    setValue,
    formState: { errors },
  } = useForm<DeployValues>({
    resolver: zodResolver(deploySchema),
    defaultValues: defaults,
  });
  const serverId = useWatch({ control, name: "serverId" });
  const modelFileId = useWatch({ control, name: "modelFileId" });
  const selectionMode = useWatch({ control, name: "selectionMode" });
  const selectedGpus = useWatch({ control, name: "gpuIds" });
  const trustRemoteCode = useWatch({ control, name: "trustRemoteCode" });
  const limitSequences = useWatch({ control, name: "limitSequences" });
  const targets = useMemo(() => targetsQuery.data ?? [], [targetsQuery.data]);
  const target = useMemo(
    () => targets.find((item) => item.server.id === serverId),
    [serverId, targets],
  );
  const selectedModel = target?.modelFiles.find((model) => model.modelFileId === modelFileId);

  useEffect(() => {
    if (!open || targets.length === 0 || serverId) return;
    const preferred = defaultModelId
      ? targets.find((item) =>
          item.modelFiles.some(
            (model) => model.modelFileId === defaultModelId || model.id === defaultModelId,
          ),
        )
      : undefined;
    const initial = preferred ?? targets[0];
    setValue("serverId", initial.server.id);
    setValue(
      "modelFileId",
      initial.modelFiles.find(
        (model) => model.modelFileId === defaultModelId || model.id === defaultModelId,
      )?.modelFileId ?? initial.modelFiles[0]?.modelFileId ?? "",
    );
  }, [defaultModelId, open, serverId, setValue, targets]);

  const submit = async (values: DeployValues) => {
    try {
      const deployment = await createDeployment.mutateAsync({
        name: values.name,
        modelFileId: values.modelFileId,
        selectionMode: values.selectionMode,
        gpuIds: values.selectionMode === "manual" ? values.gpuIds : [],
        port: values.port,
        tensorParallelSize: values.tensorParallelSize,
        gpuMemoryUtilization: values.gpuMemoryUtilization,
        maxModelLength: values.maxModelLength,
        dataType: values.dataType,
        trustRemoteCode: values.trustRemoteCode,
        extraArguments: extraArguments(values),
      });
      toast.success("Deployment request created", {
        description: `${deployment.model.displayName} -> ${deployment.server.name}:${deployment.port}`,
      });
      setOpen(false);
      reset(defaults);
    } catch (error) {
      toast.error("Deployment request failed", {
        description: error instanceof Error ? error.message : "The request failed.",
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button />}>
        <Rocket /> Deploy model
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Deploy model</DialogTitle>
          <DialogDescription>
            Configure a managed vLLM runtime on an eligible model server.
          </DialogDescription>
        </DialogHeader>

        {targetsQuery.isError ? (
          <Alert variant="destructive">
            <ShieldAlert />
            <AlertTitle>Deployment targets unavailable</AlertTitle>
            <AlertDescription>{targetsQuery.error.message}</AlertDescription>
          </Alert>
        ) : targetsQuery.isLoading ? (
          <div className="flex min-h-36 items-center justify-center text-sm text-muted-foreground">
            <LoaderCircle className="mr-2 size-4 animate-spin" /> Loading targets
          </div>
        ) : targets.length === 0 ? (
          <Alert>
            <ShieldAlert />
            <AlertTitle>No eligible deployment targets</AlertTitle>
            <AlertDescription>
              No online mutable Agent currently reports Docker, a supported model, and an available GPU.
            </AlertDescription>
          </Alert>
        ) : (
          <form onSubmit={handleSubmit(submit)} className="space-y-5">
            <div className="space-y-1.5">
              <Label htmlFor="deployment-name">Deployment name</Label>
              <Input
                id="deployment-name"
                placeholder="qwen3-8b-prod"
                autoComplete="off"
                {...register("name")}
              />
              {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label>Server</Label>
                <Controller
                  control={control}
                  name="serverId"
                  render={({ field }) => (
                    <Select
                      value={field.value}
                      onValueChange={(value) => {
                        field.onChange(value);
                        const next = targets.find((item) => item.server.id === value);
                        setValue("modelFileId", next?.modelFiles[0]?.modelFileId ?? "");
                        setValue("gpuIds", []);
                      }}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue>
                          {target
                            ? `${target.server.name} / ${target.gpus.length} GPU`
                            : "Select a server"}
                        </SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        {targets.map((item) => (
                          <SelectItem key={item.server.id} value={item.server.id}>
                            {item.server.name} / {item.gpus.length} GPU / Docker {item.dockerVersion ?? "ready"}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>
              <div className="space-y-1.5">
                <Label>Installed model</Label>
                <Controller
                  control={control}
                  name="modelFileId"
                  render={({ field }) => (
                    <Select value={field.value} onValueChange={field.onChange}>
                      <SelectTrigger className="w-full">
                        <SelectValue>
                          {selectedModel
                            ? `${selectedModel.displayName} / ${selectedModel.format ?? "unknown"}`
                            : "Select an installed model"}
                        </SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        {(target?.modelFiles ?? []).map((model) => (
                          <SelectItem key={model.modelFileId} value={model.modelFileId}>
                            {model.displayName} / {model.format ?? "unknown"}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
                {errors.modelFileId && (
                  <p className="text-xs text-destructive">{errors.modelFileId.message}</p>
                )}
              </div>
            </div>

            <div className="space-y-2">
              <Label>GPU placement</Label>
              <div className="grid grid-cols-2 rounded-md bg-muted p-1">
                {(["automatic", "manual"] as const).map((mode) => (
                  <button
                    key={mode}
                    type="button"
                    onClick={() => {
                      setValue("selectionMode", mode);
                      setValue("gpuIds", []);
                    }}
                    className={cn(
                      "h-8 rounded-sm text-sm font-medium capitalize text-muted-foreground",
                      selectionMode === mode && "bg-background text-foreground shadow-sm",
                    )}
                  >
                    {mode}
                  </button>
                ))}
              </div>
              {selectionMode === "automatic" ? (
                <div className="rounded-md border bg-muted/20 p-3 text-sm text-muted-foreground">
                  Central ranks fresh GPUs on this server by free VRAM and utilization.
                </div>
              ) : (
                <Controller
                  control={control}
                  name="gpuIds"
                  render={({ field }) => (
                    <div className="grid gap-2 sm:grid-cols-2">
                      {(target?.gpus ?? []).map((gpu) => {
                        const unavailable = gpu.status !== "available";
                        const checked = field.value.includes(gpu.id);
                        return (
                          <label
                            key={gpu.id}
                            className={cn(
                              "flex items-center gap-3 rounded-md border p-3 text-sm",
                              checked && "border-foreground/40 bg-muted/40",
                              unavailable && "cursor-not-allowed opacity-50",
                            )}
                          >
                            <Checkbox
                              checked={checked}
                              disabled={unavailable}
                              onCheckedChange={(next) => {
                                const ids = next
                                  ? [...field.value, gpu.id]
                                  : field.value.filter((id) => id !== gpu.id);
                                field.onChange(ids);
                                if (ids.length > 0) setValue("tensorParallelSize", ids.length);
                              }}
                            />
                            <span className="min-w-0">
                              <span className="block font-medium">GPU {gpu.index} / {gpu.name}</span>
                              <span className="block truncate font-mono text-[11px] text-muted-foreground">
                                {formatBytes(gpu.memoryUsed)} / {formatBytes(gpu.memoryTotal)} / {gpu.status}
                              </span>
                            </span>
                          </label>
                        );
                      })}
                    </div>
                  )}
                />
              )}
              {errors.gpuIds && (
                <p className="text-xs text-destructive">{errors.gpuIds.message}</p>
              )}
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <div className="space-y-1.5">
                <Label>Backend</Label>
                <Input value="vLLM" readOnly aria-readonly="true" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="deploy-port">Port</Label>
                <Input id="deploy-port" type="number" {...register("port", { valueAsNumber: true })} />
                {errors.port && <p className="text-xs text-destructive">{errors.port.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="tensor-parallel">Tensor parallel</Label>
                <Input
                  id="tensor-parallel"
                  type="number"
                  min={1}
                  max={Math.max(target?.gpus.length ?? 1, selectedGpus.length, 1)}
                  readOnly={selectionMode === "manual"}
                  {...register("tensorParallelSize", { valueAsNumber: true })}
                />
              </div>
            </div>

            <div className="rounded-md border">
              <button
                type="button"
                className="flex h-10 w-full items-center justify-between px-3 text-sm font-medium"
                onClick={() => setAdvancedOpen((value) => !value)}
                aria-expanded={advancedOpen}
              >
                Advanced options
                <ChevronDown className={cn("size-4 transition-transform", advancedOpen && "rotate-180")} />
              </button>
              {advancedOpen && (
                <div className="grid gap-4 border-t p-3 sm:grid-cols-2">
                  <div className="space-y-1.5">
                    <Label htmlFor="gpu-memory-utilization">GPU memory utilization</Label>
                    <Input
                      id="gpu-memory-utilization"
                      type="number"
                      step="0.05"
                      min="0.1"
                      max="1"
                      {...register("gpuMemoryUtilization", { valueAsNumber: true })}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="max-model-length">Max model length</Label>
                    <Input
                      id="max-model-length"
                      type="number"
                      step="1024"
                      {...register("maxModelLength", { valueAsNumber: true })}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Data type</Label>
                    <Controller
                      control={control}
                      name="dataType"
                      render={({ field }) => (
                        <Select value={field.value} onValueChange={field.onChange}>
                          <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="auto">Auto</SelectItem>
                            <SelectItem value="float16">float16</SelectItem>
                            <SelectItem value="bfloat16">bfloat16</SelectItem>
                          </SelectContent>
                        </Select>
                      )}
                    />
                  </div>
                  <div className="flex items-center justify-between gap-3 rounded-md border px-3 py-2">
                    <div>
                      <Label>Trust remote code</Label>
                      <p className="text-[11px] text-muted-foreground">Run model-provided Python code.</p>
                    </div>
                    <Controller
                      control={control}
                      name="trustRemoteCode"
                      render={({ field }) => (
                        <Switch checked={field.value} onCheckedChange={field.onChange} />
                      )}
                    />
                  </div>
                  {trustRemoteCode && (
                    <Alert variant="destructive" className="sm:col-span-2">
                      <ShieldAlert />
                      <AlertTitle>Model code will execute inside the runtime</AlertTitle>
                      <AlertDescription>Enable this only for a model revision you trust.</AlertDescription>
                    </Alert>
                  )}
                  <div className="space-y-3 sm:col-span-2">
                    <Label>Allowed vLLM options</Label>
                    <div className="grid gap-2 sm:grid-cols-2">
                      {[
                        ["enablePrefixCaching", "Enable prefix caching"],
                        ["disableLogRequests", "Disable request logging"],
                        ["enforceEager", "Enforce eager execution"],
                        ["enableChunkedPrefill", "Enable chunked prefill"],
                        ["limitSequences", "Limit concurrent sequences"],
                      ].map(([name, label]) => (
                        <Controller
                          key={name}
                          control={control}
                          name={name as keyof DeployValues}
                          render={({ field }) => (
                            <label className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm">
                              <Checkbox
                                checked={Boolean(field.value)}
                                onCheckedChange={field.onChange}
                              />
                              {label}
                            </label>
                          )}
                        />
                      ))}
                    </div>
                    {limitSequences && (
                      <div className="max-w-52 space-y-1.5">
                        <Label htmlFor="max-num-seqs">Maximum sequences</Label>
                        <Input
                          id="max-num-seqs"
                          type="number"
                          {...register("maxNumSeqs", { valueAsNumber: true })}
                        />
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={createDeployment.isPending}>
                {createDeployment.isPending ? <LoaderCircle className="animate-spin" /> : <Rocket />}
                Create deployment
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
