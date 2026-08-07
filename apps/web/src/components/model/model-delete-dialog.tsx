"use client";

import { useState } from "react";
import { LoaderCircle, Trash2 } from "lucide-react";
import { toast } from "sonner";

import type { ModelInstallation } from "@/types";
import { useDeleteModelInstallation } from "@/hooks/use-downloads";
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

export function ModelDeleteDialog({ model }: { model: ModelInstallation }) {
  const [open, setOpen] = useState(false);
  const [confirmation, setConfirmation] = useState("");
  const mutation = useDeleteModelInstallation();
  const confirmed = confirmation === model.sourceId;

  const close = () => {
    setOpen(false);
    setConfirmation("");
    mutation.reset();
  };

  const remove = async () => {
    if (!confirmed) return;
    try {
      const task = await mutation.mutateAsync({
        installationId: model.id,
        confirmation,
      });
      toast.success("Deletion queued", {
        description: `${model.sourceId} on ${model.server.name} / task ${task.id.slice(0, 8)}`,
      });
      close();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Deletion could not be queued.");
    }
  };

  return (
    <Dialog open={open} onOpenChange={(next) => (next ? setOpen(true) : close())}>
      <DialogTrigger
        render={
          <Button
            variant="ghost"
            size="icon-xs"
            aria-label={`Delete ${model.displayName} from ${model.server.name}`}
          />
        }
      >
        <Trash2 />
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Delete model location</DialogTitle>
          <DialogDescription>
            This removes one physical installation from {model.server.name}.
          </DialogDescription>
        </DialogHeader>
        <dl className="divide-y rounded-md border text-sm">
          <div className="grid gap-1 p-3 sm:grid-cols-[90px_1fr]">
            <dt className="text-muted-foreground">Model</dt>
            <dd className="break-all font-mono text-xs">{model.sourceId}</dd>
          </div>
          <div className="grid gap-1 p-3 sm:grid-cols-[90px_1fr]">
            <dt className="text-muted-foreground">Path</dt>
            <dd className="break-all font-mono text-xs">{model.path}</dd>
          </div>
        </dl>
        <div className="space-y-1.5">
          <Label htmlFor={`delete-${model.id}`}>Type the model source ID to confirm</Label>
          <Input
            id={`delete-${model.id}`}
            value={confirmation}
            onChange={(event) => setConfirmation(event.target.value)}
            placeholder={model.sourceId}
            className="font-mono"
            autoComplete="off"
          />
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={close}>
            Cancel
          </Button>
          <Button
            type="button"
            variant="destructive"
            onClick={() => void remove()}
            disabled={!confirmed || mutation.isPending}
          >
            {mutation.isPending ? <LoaderCircle className="animate-spin" /> : <Trash2 />}
            Delete location
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
