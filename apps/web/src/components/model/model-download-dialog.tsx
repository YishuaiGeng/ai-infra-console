"use client";

import { useEffect, useMemo, useState } from "react";
import { Controller, useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Download, LoaderCircle } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import type { CatalogModel } from "@/types";
import { useCreateDownload, useDownloadTargets } from "@/hooks/use-downloads";
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
} from "@/components/ui/select";

const downloadSchema = z.object({
  serverId: z.string().min(1, "Choose a target server."),
  directoryId: z.string().min(1, "Choose a target directory."),
  revision: z.string().trim().min(1, "Revision is required.").max(128),
});

type DownloadValues = z.infer<typeof downloadSchema>;

export function ModelDownloadDialog({ model }: { model: CatalogModel }) {
  const [open, setOpen] = useState(false);
  const targetsQuery = useDownloadTargets();
  const createDownload = useCreateDownload();
  const targets = useMemo(() => targetsQuery.data ?? [], [targetsQuery.data]);
  const {
    register,
    control,
    handleSubmit,
    reset,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<DownloadValues>({
    resolver: zodResolver(downloadSchema),
    defaultValues: { serverId: "", directoryId: "", revision: model.revision },
  });
  const serverId = useWatch({ control, name: "serverId" });
  const directoryId = useWatch({ control, name: "directoryId" });
  const selectedTarget = targets.find((target) => target.server.id === serverId);
  const selectedDirectory = selectedTarget?.directories.find(
    (directory) => directory.id === directoryId,
  );

  useEffect(() => {
    if (!open || targets.length === 0) return;
    const target = targets[0];
    reset({
      serverId: target.server.id,
      directoryId:
        target.directories.find((directory) => directory.isDefault)?.id ??
        target.directories[0]?.id ??
        "",
      revision: model.revision,
    });
  }, [model.revision, open, reset, targets]);

  const changeServer = (value: string | null) => {
    const nextTarget = targets.find((target) => target.server.id === value);
    setValue("serverId", value ?? "", { shouldValidate: true });
    setValue(
      "directoryId",
      nextTarget?.directories.find((directory) => directory.isDefault)?.id ??
        nextTarget?.directories[0]?.id ??
        "",
      { shouldValidate: true },
    );
  };

  const close = () => {
    setOpen(false);
    createDownload.reset();
  };

  const onSubmit = async (values: DownloadValues) => {
    try {
      const task = await createDownload.mutateAsync({
        provider: model.provider,
        sourceId: model.sourceId,
        revision: values.revision,
        serverId: values.serverId,
        directoryId: values.directoryId,
      });
      toast.success("Download queued", {
        description: `${task.sourceId} on ${task.server.name} / task ${task.id.slice(0, 8)}`,
      });
      close();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Download could not be queued.");
    }
  };

  return (
    <Dialog open={open} onOpenChange={(next) => (next ? setOpen(true) : close())}>
      <DialogTrigger render={<Button size="sm" />}>
        <Download /> Download
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Download model</DialogTitle>
          <DialogDescription className="break-all">
            Choose an Agent-approved destination for {model.sourceId}.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="rounded-md border bg-muted/30 p-3">
            <div className="text-xs font-medium text-muted-foreground">Model</div>
            <div className="mt-1 break-words text-sm font-semibold">{model.displayName}</div>
            <div className="mt-0.5 break-all font-mono text-xs text-muted-foreground">
              {model.providerLabel} / {model.sourceId}
            </div>
          </div>

          {targetsQuery.isPending ? (
            <div className="flex min-h-28 items-center justify-center text-muted-foreground">
              <LoaderCircle className="size-5 animate-spin" />
            </div>
          ) : targetsQuery.isError ? (
            <p className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
              {targetsQuery.error.message}
            </p>
          ) : targets.length === 0 ? (
            <p className="rounded-md border bg-muted/30 p-3 text-sm text-muted-foreground">
              No online, allowlisted Agent destination is currently available.
            </p>
          ) : (
            <>
              <div className="space-y-1.5">
                <Label>Target server</Label>
                <Controller
                  name="serverId"
                  control={control}
                  render={({ field }) => (
                    <Select value={field.value} onValueChange={changeServer}>
                      <SelectTrigger className="w-full">
                        <span className="truncate">
                          {selectedTarget
                            ? `${selectedTarget.server.name} / ${selectedTarget.server.host}`
                            : "Choose a server"}
                        </span>
                      </SelectTrigger>
                      <SelectContent>
                        {targets.map((target) => (
                          <SelectItem key={target.server.id} value={target.server.id}>
                            {target.server.name} / {target.server.host}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
                {errors.serverId && (
                  <p className="text-xs text-destructive">{errors.serverId.message}</p>
                )}
              </div>
              <div className="space-y-1.5">
                <Label>Target directory</Label>
                <Controller
                  name="directoryId"
                  control={control}
                  render={({ field }) => (
                    <Select value={field.value} onValueChange={field.onChange}>
                      <SelectTrigger className="w-full font-mono">
                        <span className="truncate" title={selectedDirectory?.path}>
                          {selectedDirectory?.path ?? "Choose a directory"}
                        </span>
                      </SelectTrigger>
                      <SelectContent>
                        {(selectedTarget?.directories ?? []).map((directory) => (
                          <SelectItem key={directory.id} value={directory.id}>
                            {directory.path}{directory.isDefault ? " / default" : ""}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
                {errors.directoryId && (
                  <p className="text-xs text-destructive">{errors.directoryId.message}</p>
                )}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor={`revision-${model.id}`}>Revision</Label>
                <Input
                  id={`revision-${model.id}`}
                  className="font-mono"
                  {...register("revision")}
                />
                {errors.revision && (
                  <p className="text-xs text-destructive">{errors.revision.message}</p>
                )}
              </div>
            </>
          )}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={close}>
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={targets.length === 0 || isSubmitting || createDownload.isPending}
            >
              {createDownload.isPending && <LoaderCircle className="animate-spin" />}
              Create task
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
