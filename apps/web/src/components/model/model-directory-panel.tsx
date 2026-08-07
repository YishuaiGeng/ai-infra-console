"use client";

import { FolderSearch, Star } from "lucide-react";
import { toast } from "sonner";

import type { ModelDirectory } from "@/types";
import { useSetDefaultModelDirectory } from "@/hooks/use-model-inventory";
import { formatDateTime } from "@/lib/format";
import { EmptyState } from "@/components/shared/empty-state";
import { SectionPanel } from "@/components/shared/section-panel";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";

export function ModelDirectoryPanel({
  serverId,
  directories,
  isAdmin,
}: {
  serverId: string;
  directories: ModelDirectory[];
  isAdmin: boolean;
}) {
  const mutation = useSetDefaultModelDirectory(serverId);

  const setDefault = async (directory: ModelDirectory) => {
    try {
      await mutation.mutateAsync(directory.id);
      toast.success("Default model directory updated");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Directory update failed.");
    }
  };

  return (
    <SectionPanel
      title="Model directories"
      description="Agent-advertised read-only scan roots"
    >
      {directories.length === 0 ? (
        <EmptyState
          icon={FolderSearch}
          title="No model directories configured"
          message="Configure an allowed model directory in the Agent environment, then wait for its next report."
        />
      ) : (
        <div className="divide-y">
          {directories.map((directory) => (
            <div
              key={directory.id}
              className="flex flex-col gap-2 p-4 sm:flex-row sm:items-center"
            >
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="break-all font-mono text-xs">{directory.path}</span>
                  <StatusBadge
                    status={directory.isAvailable ? "available" : "error"}
                    label={directory.isAvailable ? "Available" : directory.errorCode ?? "Error"}
                  />
                  {directory.isDefault && <StatusBadge status="active" label="Default" />}
                </div>
                <div className="mt-1 text-[11px] text-muted-foreground">
                  {directory.modelCount} models / {directory.lastScannedAt
                    ? formatDateTime(directory.lastScannedAt)
                    : "not scanned"}
                </div>
              </div>
              {isAdmin &&
                !directory.isDefault &&
                directory.isAllowed &&
                directory.isAvailable && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => void setDefault(directory)}
                  disabled={mutation.isPending}
                >
                  <Star /> Set default
                </Button>
                )}
            </div>
          ))}
        </div>
      )}
    </SectionPanel>
  );
}
