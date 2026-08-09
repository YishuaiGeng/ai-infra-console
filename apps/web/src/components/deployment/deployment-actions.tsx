"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  LoaderCircle,
  MoreHorizontal,
  Play,
  RotateCcw,
  Square,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";

import type { Deployment } from "@/types";
import {
  availableDeploymentActions,
  type DeploymentAction,
} from "@/lib/api/deployments";
import {
  useDeleteDeployment,
  useDeploymentAction,
} from "@/hooks/use-deployments";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const actionLabels: Record<DeploymentAction, string> = {
  start: "Start",
  stop: "Stop",
  restart: "Restart",
  retry: "Retry",
  delete: "Delete",
};

function ActionIcon({ action }: { action: DeploymentAction }) {
  if (action === "start") return <Play />;
  if (action === "stop") return <Square />;
  if (action === "delete") return <Trash2 />;
  return <RotateCcw />;
}

function useDeploymentControls(deployment: Deployment, redirectAfterDelete: boolean) {
  const router = useRouter();
  const lifecycle = useDeploymentAction();
  const deletion = useDeleteDeployment();
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [confirmation, setConfirmation] = useState("");

  const run = async (action: Exclude<DeploymentAction, "delete">) => {
    try {
      await lifecycle.mutateAsync({ id: deployment.id, action });
      toast.success(`${actionLabels[action]} requested`, {
        description: `${deployment.name} is queued for reconciliation.`,
      });
    } catch (error) {
      toast.error(`${actionLabels[action]} request failed`, {
        description: error instanceof Error ? error.message : "The request failed.",
      });
    }
  };

  const remove = async () => {
    try {
      await deletion.mutateAsync({ id: deployment.id, confirmation });
      toast.success("Delete requested", {
        description: `${deployment.name} will be removed after its runtime is reconciled.`,
      });
      setDeleteOpen(false);
      setConfirmation("");
      if (redirectAfterDelete) router.push("/deployments");
    } catch (error) {
      toast.error("Delete request failed", {
        description: error instanceof Error ? error.message : "The request failed.",
      });
    }
  };

  return {
    busy: lifecycle.isPending || deletion.isPending,
    confirmation,
    deleteOpen,
    remove,
    run,
    setConfirmation,
    setDeleteOpen,
  };
}

function DeleteDialog({
  deployment,
  controls,
}: {
  deployment: Deployment;
  controls: ReturnType<typeof useDeploymentControls>;
}) {
  return (
    <Dialog open={controls.deleteOpen} onOpenChange={controls.setDeleteOpen}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Delete deployment</DialogTitle>
          <DialogDescription>
            The managed runtime and deployment record will be removed. The installed model is preserved.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <Label htmlFor={`delete-${deployment.id}`}>
            Type <span className="font-mono">{deployment.name}</span> to confirm
          </Label>
          <Input
            id={`delete-${deployment.id}`}
            value={controls.confirmation}
            onChange={(event) => controls.setConfirmation(event.target.value)}
            autoComplete="off"
          />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => controls.setDeleteOpen(false)}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            disabled={controls.confirmation !== deployment.name || controls.busy}
            onClick={() => void controls.remove()}
          >
            {controls.busy ? <LoaderCircle className="animate-spin" /> : <Trash2 />}
            Delete deployment
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function DeploymentActions({
  deployment,
  isAdmin,
}: {
  deployment: Deployment;
  isAdmin: boolean;
}) {
  const controls = useDeploymentControls(deployment, false);
  const actions = availableDeploymentActions(deployment);
  if (!isAdmin || actions.length === 0) return null;

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger
          render={
            <Button
              variant="ghost"
              size="icon-xs"
              disabled={controls.busy}
              aria-label={`Actions for ${deployment.name}`}
            />
          }
        >
          {controls.busy ? <LoaderCircle className="animate-spin" /> : <MoreHorizontal />}
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {actions.map((action) => (
            <DropdownMenuItem
              key={action}
              variant={action === "delete" ? "destructive" : "default"}
              onClick={() =>
                action === "delete"
                  ? controls.setDeleteOpen(true)
                  : void controls.run(action)
              }
            >
              <ActionIcon action={action} /> {actionLabels[action]}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
      <DeleteDialog deployment={deployment} controls={controls} />
    </>
  );
}

export function DeploymentPrimaryActions({
  deployment,
  isAdmin,
}: {
  deployment: Deployment;
  isAdmin: boolean;
}) {
  const controls = useDeploymentControls(deployment, true);
  const actions = availableDeploymentActions(deployment);
  if (!isAdmin || actions.length === 0) return null;

  return (
    <>
      {actions.map((action) => (
        <Button
          key={action}
          variant={action === "delete" ? "destructive" : "outline"}
          disabled={controls.busy}
          onClick={() =>
            action === "delete"
              ? controls.setDeleteOpen(true)
              : void controls.run(action)
          }
        >
          {controls.busy ? <LoaderCircle className="animate-spin" /> : <ActionIcon action={action} />}
          {actionLabels[action]}
        </Button>
      ))}
      <DeleteDialog deployment={deployment} controls={controls} />
    </>
  );
}
