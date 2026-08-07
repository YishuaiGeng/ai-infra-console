import { ArrowUpRight, Box, Database, FileCode2 } from "lucide-react";

import type { ModelDefinition } from "@/types";
import { ModelDownloadDialog } from "@/components/model/model-download-dialog";
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

export function ModelCard({ model }: { model: ModelDefinition }) {
  return (
    <article className="flex min-h-64 flex-col overflow-hidden rounded-md border bg-card">
      <div className="flex items-start gap-3 border-b p-4">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
          {model.type === "Embedding" ? (
            <Database className="size-4" />
          ) : (
            <Box className="size-4" />
          )}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <Badge variant="outline" className="rounded-sm">
              {model.provider}
            </Badge>
            <Badge variant="secondary" className="rounded-sm">
              {model.type}
            </Badge>
          </div>
          <h3 className="mt-2 break-words text-sm font-semibold">
            {model.displayName}
          </h3>
          <p className="mt-0.5 break-all font-mono text-[11px] text-muted-foreground">
            {model.name}
          </p>
        </div>
      </div>
      <div className="flex-1 p-4">
        <p className="line-clamp-3 text-sm leading-5 text-muted-foreground">
          {model.description}
        </p>
        <dl className="mt-4 grid grid-cols-3 gap-2 text-xs">
          <div>
            <dt className="text-muted-foreground">Parameters</dt>
            <dd className="mt-0.5 font-mono font-medium">{model.parameters}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Context</dt>
            <dd className="mt-0.5 font-mono font-medium">
              {model.contextLength}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">License</dt>
            <dd className="mt-0.5 truncate font-medium">{model.license}</dd>
          </div>
        </dl>
      </div>
      <div className="flex items-center justify-between gap-2 border-t bg-muted/20 p-3">
        <Dialog>
          <DialogTrigger render={<Button variant="outline" size="sm" />}>
            <FileCode2 /> Details
          </DialogTrigger>
          <DialogContent className="sm:max-w-xl">
            <DialogHeader>
              <DialogTitle>{model.displayName}</DialogTitle>
              <DialogDescription className="font-mono">
                {model.name}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 text-sm">
              <p className="leading-6 text-muted-foreground">
                {model.description}
              </p>
              <dl className="grid grid-cols-2 gap-3 rounded-md border p-3 sm:grid-cols-4">
                <div>
                  <dt className="text-xs text-muted-foreground">Architecture</dt>
                  <dd className="mt-1 break-all font-mono text-xs">
                    {model.architecture}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">Parameters</dt>
                  <dd className="mt-1 font-mono">{model.parameters}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">Downloads</dt>
                  <dd className="mt-1 font-mono">{model.downloads}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">License</dt>
                  <dd className="mt-1">{model.license}</dd>
                </div>
              </dl>
              <div>
                <div className="mb-2 text-xs font-medium text-muted-foreground">
                  Capabilities
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {model.tags.map((tag) => (
                    <Badge key={tag} variant="secondary" className="rounded-sm">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>
              <div className="flex items-center gap-2 rounded-md bg-muted p-3 font-mono text-xs">
                <ArrowUpRight className="size-3.5 shrink-0" />
                <span className="break-all">{model.source}</span>
              </div>
            </div>
          </DialogContent>
        </Dialog>
        <ModelDownloadDialog model={model} />
      </div>
    </article>
  );
}
