"use client";

import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Download } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import type { ModelDefinition } from "@/types";
import { servers } from "@/mocks/data";
import { Button } from "@/components/ui/button";
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

const downloadSchema = z.object({
  serverId: z.string().min(1),
  targetDirectory: z.string().startsWith("/", "Use an absolute path."),
  revision: z.string().min(1),
});

type DownloadValues = z.infer<typeof downloadSchema>;

export function ModelDownloadDialog({ model }: { model: ModelDefinition }) {
  const [open, setOpen] = useState(false);
  const onlineServers = servers.filter((server) => server.status === "online");
  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<DownloadValues>({
    resolver: zodResolver(downloadSchema),
    defaultValues: {
      serverId: onlineServers[0]?.id ?? "",
      targetDirectory: "/data/models",
      revision: "main",
    },
  });

  const onSubmit = (values: DownloadValues) => {
    const server = servers.find((item) => item.id === values.serverId);
    toast.success("Download task created", {
      description: `${model.displayName} queued for ${server?.name ?? "server"}.`,
    });
    setOpen(false);
    reset();
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button size="sm" />}>
        <Download /> Download
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Download model</DialogTitle>
          <DialogDescription>
            Choose the destination and revision for {model.name}.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="rounded-md border bg-muted/30 p-3">
            <div className="text-xs font-medium text-muted-foreground">Model</div>
            <div className="mt-1 text-sm font-semibold">{model.displayName}</div>
            <div className="mt-0.5 font-mono text-xs text-muted-foreground">
              {model.provider} / {model.parameters}
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>Target server</Label>
            <Controller
              name="serverId"
              control={control}
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
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
          <div className="space-y-1.5">
            <Label htmlFor={`directory-${model.id}`}>Target directory</Label>
            <Input
              id={`directory-${model.id}`}
              className="font-mono"
              {...register("targetDirectory")}
            />
            {errors.targetDirectory && (
              <p className="text-xs text-destructive">
                {errors.targetDirectory.message}
              </p>
            )}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor={`revision-${model.id}`}>Revision</Label>
            <Input
              id={`revision-${model.id}`}
              className="font-mono"
              {...register("revision")}
            />
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit">Create task</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
