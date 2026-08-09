"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";

import {
  deploymentDtoSchema,
  deploymentCreatePayload,
  deploymentLogPath,
  deploymentLogDtoSchema,
  deploymentQueryKeys,
  deploymentTargetDtoSchema,
  mapDeployment,
  mapDeploymentLog,
  mapDeploymentTarget,
  type DeploymentAction,
  type DeploymentCreateInput,
} from "@/lib/api/deployments";
import { apiRequest, infrastructureQueryKeys } from "@/lib/api/infrastructure";
import { modelQueryKeys } from "@/lib/api/models";

function refreshInterval() {
  return typeof document !== "undefined" && document.hidden ? false : 5_000;
}

export function useDeploymentTargets() {
  return useQuery({
    queryKey: deploymentQueryKeys.targets,
    queryFn: async () =>
      (
        await apiRequest(
          "/api/deployment-targets",
          z.array(deploymentTargetDtoSchema),
        )
      ).map(mapDeploymentTarget),
    refetchInterval: 30_000,
  });
}

export function useDeployments() {
  return useQuery({
    queryKey: deploymentQueryKeys.list,
    queryFn: async () =>
      (await apiRequest("/api/deployments", z.array(deploymentDtoSchema))).map(
        mapDeployment,
      ),
    refetchInterval: refreshInterval,
  });
}

export function useDeployment(id: string, enabled = true) {
  return useQuery({
    queryKey: deploymentQueryKeys.detail(id),
    queryFn: async () =>
      mapDeployment(
        await apiRequest(
          `/api/deployments/${encodeURIComponent(id)}`,
          deploymentDtoSchema,
        ),
      ),
    enabled: enabled && id.length > 0,
    refetchInterval: refreshInterval,
  });
}

export function useDeploymentLogs(id: string, search: string, limit: number) {
  return useQuery({
    queryKey: deploymentQueryKeys.logs(id, search, limit),
    queryFn: async () => {
      return (
        await apiRequest(
          deploymentLogPath(id, search, limit),
          z.array(deploymentLogDtoSchema),
        )
      ).map(mapDeploymentLog);
    },
    enabled: id.length > 0,
    refetchInterval: refreshInterval,
  });
}

async function invalidateDeploymentQueries(queryClient: ReturnType<typeof useQueryClient>) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: deploymentQueryKeys.all }),
    queryClient.invalidateQueries({ queryKey: infrastructureQueryKeys.all }),
    queryClient.invalidateQueries({ queryKey: modelQueryKeys.all }),
  ]);
}

export function useCreateDeployment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: DeploymentCreateInput) =>
      mapDeployment(
        await apiRequest("/api/deployments", deploymentDtoSchema, {
          method: "POST",
          body: JSON.stringify(deploymentCreatePayload(input)),
        }),
      ),
    onSuccess: () => invalidateDeploymentQueries(queryClient),
  });
}

export function useDeploymentAction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, action }: { id: string; action: Exclude<DeploymentAction, "delete"> }) =>
      mapDeployment(
        await apiRequest(
          `/api/deployments/${encodeURIComponent(id)}/${action}`,
          deploymentDtoSchema,
          { method: "POST" },
        ),
      ),
    onSuccess: () => invalidateDeploymentQueries(queryClient),
  });
}

export function useDeleteDeployment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, confirmation }: { id: string; confirmation: string }) =>
      mapDeployment(
        await apiRequest(`/api/deployments/${encodeURIComponent(id)}`, deploymentDtoSchema, {
          method: "DELETE",
          body: JSON.stringify({ confirmation }),
        }),
      ),
    onSuccess: () => invalidateDeploymentQueries(queryClient),
  });
}
