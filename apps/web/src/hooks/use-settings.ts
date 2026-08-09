"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { SystemSettings } from "@/types";
import {
  mapSystemSettings,
  settingsQueryKeys,
  systemSettingsDtoSchema,
  systemSettingsPayload,
} from "@/lib/api/settings";
import { apiRequest } from "@/lib/api/infrastructure";
import { activityQueryKeys } from "@/lib/api/activity";

export function useSystemSettings() {
  return useQuery({
    queryKey: settingsQueryKeys.all,
    queryFn: async () =>
      mapSystemSettings(await apiRequest("/api/settings", systemSettingsDtoSchema)),
  });
}

export function useUpdateSystemSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: SystemSettings) =>
      mapSystemSettings(
        await apiRequest("/api/settings", systemSettingsDtoSchema, {
          method: "PUT",
          body: JSON.stringify(systemSettingsPayload(input)),
        }),
      ),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: settingsQueryKeys.all }),
        queryClient.invalidateQueries({ queryKey: activityQueryKeys.all }),
      ]);
    },
  });
}
