"use client";

import { useMemo, useState } from "react";
import { Controller, useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ChevronDown, Rocket } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import { gpus, models, servers } from "@/mocks/data";
import { cn } from "@/lib/utils";
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
    modelId: z.string().min(1),
    serverId: z.string().min(1),
    selectionMode: z.enum(["automatic", "manual"]),
    gpuIds: z.array(z.string()),
    backend: z.enum(["vLLM", "Ollama"]),
    port: z.number().int().min(1024).max(65535),
    tensorParallelSize: z.number().int().min(1).max(8),
    gpuMemoryUtilization: z.number().min(0.1).max(1),
    maxModelLength: z.number().int().min(1024),
    dataType: z.enum(["auto", "float16", "bfloat16"]),
    trustRemoteCode: z.boolean(),
    extraArguments: z.string(),
  })
  .refine(
    (value) => value.selectionMode === "automatic" || value.gpuIds.length > 0,
    { message: "Select at least one GPU.", path: ["gpuIds"] },
  );

type DeployValues = z.infer<typeof deploySchema>;

export function DeployModelDialog({
  defaultModelId,
}: {
  defaultModelId?: string;
}) {
  const [open, setOpen] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const onlineServers = servers.filter((server) => server.status === "online");
  const {
    control,
    register,
    handleSubmit,
    reset,
    setValue,
    formState: { errors },
  } = useForm<DeployValues>({
    resolver: zodResolver(deploySchema),
    defaultValues: {
      modelId: defaultModelId ?? models[0].id,
      serverId: onlineServers[0].id,
      selectionMode: "automatic",
      gpuIds: [],
      backend: "vLLM",
      port: 8000,
      tensorParallelSize: 1,
      gpuMemoryUtilization: 0.9,
      maxModelLength: 32768,
      dataType: "auto",
      trustRemoteCode: false,
      extraArguments: "",
    },
  });
  const serverId = useWatch({ control, name: "serverId" });
  const selectionMode = useWatch({ control, name: "selectionMode" });
  const selectedGpus = useWatch({ control, name: "gpuIds" });
  const serverGpus = useMemo(
    () => gpus.filter((gpu) => gpu.serverId === serverId),
    [serverId],
  );

  const submit = (values: DeployValues) => {
    const model = models.find((item) => item.id === values.modelId);
    const server = servers.find((item) => item.id === values.serverId);
    toast.success("Deployment request created", {
      description: `${model?.displayName} -> ${server?.name}:${values.port}`,
    });
    setOpen(false);
    reset();
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
            Choose model placement, runtime backend, port, and capacity limits.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(submit)} className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label>Model</Label>
              <Controller
                control={control}
                name="modelId"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {models.map((model) => (
                        <SelectItem key={model.id} value={model.id}>
                          {model.displayName} / {model.parameters}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
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
                      setValue("gpuIds", []);
                    }}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {onlineServers.map((server) => (
                        <SelectItem key={server.id} value={server.id}>
                          {server.name} / {server.gpuCount}x {server.gpuModel}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label>GPU selection</Label>
            <div className="grid grid-cols-2 rounded-md bg-muted p-1">
              {(["automatic", "manual"] as const).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => setValue("selectionMode", mode)}
                  className={cn(
                    "h-8 rounded-sm text-sm font-medium capitalize text-muted-foreground",
                    selectionMode === mode &&
                      "bg-background text-foreground shadow-sm",
                  )}
                >
                  {mode}
                </button>
              ))}
            </div>
            {selectionMode === "automatic" ? (
              <div className="rounded-md border bg-muted/20 p-3 text-sm text-muted-foreground">
                Automatic selection ranks GPUs by free VRAM, then utilization,
                while keeping the deployment on one server.
              </div>
            ) : (
              <Controller
                control={control}
                name="gpuIds"
                render={({ field }) => (
                  <div className="grid gap-2 sm:grid-cols-2">
                    {serverGpus.map((gpu) => {
                      const unavailable = gpu.status === "unavailable";
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
                              field.onChange(
                                next
                                  ? [...field.value, gpu.id]
                                  : field.value.filter((id) => id !== gpu.id),
                              );
                            }}
                          />
                          <span className="min-w-0">
                            <span className="block font-medium">
                              GPU {gpu.index} / {gpu.name}
                            </span>
                            <span className="block truncate font-mono text-[11px] text-muted-foreground">
                              {gpu.memoryUsedGb ?? "--"} / {gpu.memoryTotalGb} GB
                              / {gpu.status}
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
              <Controller
                control={control}
                name="backend"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="vLLM">vLLM</SelectItem>
                      <SelectItem value="Ollama">Ollama</SelectItem>
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="deploy-port">Port</Label>
              <Input
                id="deploy-port"
                type="number"
                {...register("port", { valueAsNumber: true })}
              />
              {errors.port && (
                <p className="text-xs text-destructive">{errors.port.message}</p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="tensor-parallel">Tensor parallel</Label>
              <Input
                id="tensor-parallel"
                type="number"
                min={1}
                max={Math.max(selectedGpus.length, 1)}
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
              <ChevronDown
                className={cn(
                  "size-4 transition-transform",
                  advancedOpen && "rotate-180",
                )}
              />
            </button>
            {advancedOpen && (
              <div className="grid gap-4 border-t p-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="gpu-memory-utilization">
                    GPU memory utilization
                  </Label>
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
                        <SelectTrigger className="w-full">
                          <SelectValue />
                        </SelectTrigger>
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
                    <p className="text-[11px] text-muted-foreground">
                      Allow custom model code.
                    </p>
                  </div>
                  <Controller
                    control={control}
                    name="trustRemoteCode"
                    render={({ field }) => (
                      <Switch
                        checked={field.value}
                        onCheckedChange={field.onChange}
                      />
                    )}
                  />
                </div>
                <div className="space-y-1.5 sm:col-span-2">
                  <Label htmlFor="extra-arguments">Extra arguments</Label>
                  <Input
                    id="extra-arguments"
                    className="font-mono"
                    placeholder="--enable-prefix-caching"
                    {...register("extraArguments")}
                  />
                </div>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit">
              <Rocket /> Create deployment
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
