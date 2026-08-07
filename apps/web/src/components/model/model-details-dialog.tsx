"use client";

import { useState } from "react";
import { Eye, LoaderCircle } from "lucide-react";

import { useModelDetail } from "@/hooks/use-model-inventory";
import { formatBytes } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

export function ModelDetailsDialog({ modelId }: { modelId: string }) {
  const [open, setOpen] = useState(false);
  const detailQuery = useModelDetail(modelId, open);
  const model = detailQuery.data;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger
        render={<Button variant="ghost" size="icon-xs" aria-label="View model details" />}
      >
        <Eye />
      </DialogTrigger>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{model?.displayName ?? "Model details"}</DialogTitle>
          <DialogDescription className="break-all font-mono">
            {model?.sourceId ?? "Loading inventory..."}
          </DialogDescription>
        </DialogHeader>
        {detailQuery.isPending ? (
          <div className="flex min-h-32 items-center justify-center text-muted-foreground">
            <LoaderCircle className="size-5 animate-spin" />
          </div>
        ) : detailQuery.isError || !model ? (
          <p className="py-6 text-sm text-destructive">
            {detailQuery.error?.message ?? "The model detail is unavailable."}
          </p>
        ) : (
          <div className="space-y-4 text-sm">
            <dl className="grid gap-3 sm:grid-cols-3">
              <div>
                <dt className="text-xs text-muted-foreground">Architecture</dt>
                <dd className="mt-1 break-all font-mono text-xs">{model.architecture}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Model type</dt>
                <dd className="mt-1 font-mono text-xs">{model.modelType}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Source</dt>
                <dd className="mt-1 capitalize">{model.source}</dd>
              </div>
            </dl>
            <div>
              <div className="mb-2 text-xs font-medium text-muted-foreground">
                Physical locations
              </div>
              <div className="divide-y rounded-md border">
                {model.locations.map((location) => (
                  <div key={location.id} className="p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium">{location.server.name}</span>
                      <Badge variant="outline" className="rounded-sm uppercase">
                        {location.format}
                      </Badge>
                      <span className="ml-auto font-mono text-xs text-muted-foreground">
                        {formatBytes(location.sizeBytes)}
                      </span>
                    </div>
                    <div className="mt-1 break-all font-mono text-[11px] text-muted-foreground">
                      {location.path}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
