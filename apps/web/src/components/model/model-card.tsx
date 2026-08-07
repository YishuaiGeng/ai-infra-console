import { ArrowUpRight, Box, Database, FileCode2, LockKeyhole } from "lucide-react";

import type { CatalogModel } from "@/types";
import { formatBytes } from "@/lib/format";
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

function compactNumber(value: number | null) {
  return value === null
    ? "--"
    : new Intl.NumberFormat("en", { notation: "compact" }).format(value);
}

export function ModelCard({
  model,
  isAdmin,
}: {
  model: CatalogModel;
  isAdmin: boolean;
}) {
  const embedding = model.modelType.toLowerCase().includes("embedding");
  return (
    <article className="flex min-h-64 flex-col overflow-hidden rounded-md border bg-card">
      <div className="flex items-start gap-3 border-b p-4">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
          {embedding ? <Database className="size-4" /> : <Box className="size-4" />}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <Badge variant="outline" className="rounded-sm">
              {model.providerLabel}
            </Badge>
            <Badge variant="secondary" className="max-w-40 truncate rounded-sm">
              {model.modelType}
            </Badge>
            {(model.gated || model.private) && (
              <Badge variant="outline" className="rounded-sm">
                <LockKeyhole /> {model.private ? "Private" : "Gated"}
              </Badge>
            )}
          </div>
          <h3 className="mt-2 break-words text-sm font-semibold">{model.displayName}</h3>
          <p className="mt-0.5 break-all font-mono text-[11px] text-muted-foreground">
            {model.sourceId}
          </p>
        </div>
      </div>
      <div className="flex-1 p-4">
        <p className="line-clamp-3 text-sm leading-5 text-muted-foreground">
          {model.description}
        </p>
        <dl className="mt-4 grid grid-cols-3 gap-2 text-xs">
          <div>
            <dt className="text-muted-foreground">Downloads</dt>
            <dd className="mt-0.5 font-mono font-medium">{compactNumber(model.downloads)}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Size</dt>
            <dd className="mt-0.5 font-mono font-medium">
              {model.sizeBytes === null ? "--" : formatBytes(model.sizeBytes)}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">License</dt>
            <dd className="mt-0.5 truncate font-medium" title={model.license}>
              {model.license}
            </dd>
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
              <DialogDescription className="break-all font-mono">
                {model.sourceId}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 text-sm">
              <p className="leading-6 text-muted-foreground">{model.description}</p>
              <dl className="grid grid-cols-2 gap-3 rounded-md border p-3 sm:grid-cols-4">
                <div>
                  <dt className="text-xs text-muted-foreground">Architecture</dt>
                  <dd className="mt-1 break-all font-mono text-xs">{model.architecture}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">Revision</dt>
                  <dd className="mt-1 truncate font-mono text-xs" title={model.revision}>
                    {model.revision}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">Downloads</dt>
                  <dd className="mt-1 font-mono">{compactNumber(model.downloads)}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">License</dt>
                  <dd className="mt-1 break-words">{model.license}</dd>
                </div>
              </dl>
              <div className="flex flex-wrap gap-1.5">
                {model.tags.slice(0, 12).map((tag) => (
                  <Badge key={tag} variant="secondary" className="rounded-sm">
                    {tag}
                  </Badge>
                ))}
              </div>
              <a
                href={model.sourceUrl}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-2 rounded-md bg-muted p-3 font-mono text-xs hover:text-foreground"
              >
                <ArrowUpRight className="size-3.5 shrink-0" />
                <span className="break-all">{model.sourceUrl}</span>
              </a>
            </div>
          </DialogContent>
        </Dialog>
        {isAdmin && <ModelDownloadDialog model={model} />}
      </div>
    </article>
  );
}
