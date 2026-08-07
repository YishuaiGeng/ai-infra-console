"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";

import {
  catalogSearchDtoSchema,
  downloadQueryKeys,
  downloadTargetDtoSchema,
  downloadTaskDtoSchema,
  mapCatalogSearch,
  mapDeleteTask,
  mapDownloadTarget,
  mapDownloadTask,
  modelDeleteTaskDtoSchema,
  type DownloadCreateInput,
} from "@/lib/api/downloads";
import { apiRequest, infrastructureQueryKeys } from "@/lib/api/infrastructure";
import { modelQueryKeys } from "@/lib/api/models";

function refreshInterval() {
  return typeof document !== "undefined" && document.hidden ? false : 5_000;
}

export function useCatalogModels(
  query: string,
  provider: "all" | "huggingface" | "modelscope",
) {
  return useQuery({
    queryKey: downloadQueryKeys.catalog(query, provider),
    queryFn: async () => {
      const params = new URLSearchParams({ query, limit: "20" });
      if (provider !== "all") params.set("provider", provider);
      return mapCatalogSearch(
        await apiRequest(
          `/api/catalog/models?${params.toString()}`,
          catalogSearchDtoSchema,
        ),
      );
    },
    staleTime: 60_000,
  });
}

export function useDownloadTargets() {
  return useQuery({
    queryKey: downloadQueryKeys.targets,
    queryFn: async () =>
      (
        await apiRequest(
          "/api/download-targets",
          z.array(downloadTargetDtoSchema),
        )
      ).map(mapDownloadTarget),
    refetchInterval: 30_000,
  });
}

export function useDownloads() {
  return useQuery({
    queryKey: downloadQueryKeys.list,
    queryFn: async () =>
      (
        await apiRequest("/api/downloads", z.array(downloadTaskDtoSchema))
      ).map(mapDownloadTask),
    refetchInterval: refreshInterval,
  });
}

export function useCreateDownload() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: DownloadCreateInput) =>
      mapDownloadTask(
        await apiRequest("/api/downloads", downloadTaskDtoSchema, {
          method: "POST",
          body: JSON.stringify({
            provider: input.provider,
            source_id: input.sourceId,
            revision: input.revision,
            server_id: input.serverId,
            directory_id: input.directoryId,
          }),
        }),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: downloadQueryKeys.all }),
  });
}

function useDownloadAction(action: "cancel" | "retry") {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (taskId: string) =>
      mapDownloadTask(
        await apiRequest(
          `/api/downloads/${encodeURIComponent(taskId)}/${action}`,
          downloadTaskDtoSchema,
          { method: "POST" },
        ),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: downloadQueryKeys.all }),
  });
}

export function useCancelDownload() {
  return useDownloadAction("cancel");
}

export function useRetryDownload() {
  return useDownloadAction("retry");
}

export function useDeleteModelInstallation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      installationId,
      confirmation,
    }: {
      installationId: string;
      confirmation: string;
    }) =>
      mapDeleteTask(
        await apiRequest(
          `/api/model-files/${encodeURIComponent(installationId)}/delete`,
          modelDeleteTaskDtoSchema,
          {
            method: "POST",
            body: JSON.stringify({ confirmation }),
          },
        ),
      ),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: modelQueryKeys.all }),
        queryClient.invalidateQueries({ queryKey: infrastructureQueryKeys.all }),
      ]);
    },
  });
}
