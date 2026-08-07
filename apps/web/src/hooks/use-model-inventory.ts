"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";

import { apiRequest, infrastructureQueryKeys } from "@/lib/api/infrastructure";
import {
  defaultModelDirectoryResponseSchema,
  mapModelDetail,
  mapModelDirectory,
  mapModelInstallation,
  modelDetailDtoSchema,
  modelDirectoryDtoSchema,
  modelInstallationDtoSchema,
  modelInventorySummaryDtoSchema,
  modelQueryKeys,
} from "@/lib/api/models";

function refreshInterval() {
  return typeof document !== "undefined" && document.hidden ? false : 30_000;
}

export function useModelInstallations() {
  return useQuery({
    queryKey: modelQueryKeys.installations,
    queryFn: async () =>
      (await apiRequest("/api/models", z.array(modelInstallationDtoSchema))).map(
        mapModelInstallation,
      ),
    refetchInterval: refreshInterval,
  });
}

export function useModelDetail(modelId: string, enabled = true) {
  return useQuery({
    queryKey: modelQueryKeys.detail(modelId),
    queryFn: async () =>
      mapModelDetail(
        await apiRequest(
          `/api/models/${encodeURIComponent(modelId)}`,
          modelDetailDtoSchema,
        ),
      ),
    enabled,
  });
}

export function useModelInventorySummary() {
  return useQuery({
    queryKey: modelQueryKeys.summary,
    queryFn: () =>
      apiRequest("/api/model-inventory/summary", modelInventorySummaryDtoSchema),
    refetchInterval: refreshInterval,
  });
}

export function useModelDirectories(serverId: string) {
  return useQuery({
    queryKey: ["models", "directories", serverId],
    queryFn: async () =>
      (
        await apiRequest(
          `/api/servers/${encodeURIComponent(serverId)}/model-directories`,
          z.array(modelDirectoryDtoSchema),
        )
      ).map(mapModelDirectory),
    refetchInterval: refreshInterval,
  });
}

export function useSetDefaultModelDirectory(serverId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (directoryId: string) =>
      mapModelDirectory(
        await apiRequest(
          `/api/servers/${encodeURIComponent(serverId)}/model-directories/default`,
          defaultModelDirectoryResponseSchema,
          {
            method: "PUT",
            body: JSON.stringify({ directory_id: directoryId }),
          },
        ),
      ),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: infrastructureQueryKeys.server(serverId),
        }),
        queryClient.invalidateQueries({ queryKey: modelQueryKeys.all }),
      ]);
    },
  });
}
