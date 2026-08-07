"use client";

import { MoreHorizontal, Play, RotateCcw, Square } from "lucide-react";
import { toast } from "sonner";

import type { Deployment } from "@/types";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function DeploymentActions({ deployment }: { deployment: Deployment }) {
  const act = (action: string) =>
    toast.success(`${action} requested`, {
      description: `Lifecycle request recorded for ${deployment.name}.`,
    });

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button
            variant="ghost"
            size="icon-xs"
            aria-label={`Actions for ${deployment.name}`}
          />
        }
      >
        <MoreHorizontal />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => act("Start")}>
          <Play /> Start
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => act("Stop")}>
          <Square /> Stop
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => act("Restart")}>
          <RotateCcw /> Restart
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
