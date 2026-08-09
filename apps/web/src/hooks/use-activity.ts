"use client";

import { useQuery } from "@tanstack/react-query";
import { z } from "zod";

import {
  activityLogDtoSchema,
  activityPath,
  activityQueryKeys,
  mapActivityLog,
} from "@/lib/api/activity";
import { apiRequest } from "@/lib/api/infrastructure";

export function useActivityLogs(search: string, limit = 200) {
  return useQuery({
    queryKey: activityQueryKeys.list(search, limit),
    queryFn: async () =>
      (await apiRequest(activityPath(search, limit), z.array(activityLogDtoSchema))).map(
        mapActivityLog,
      ),
    refetchInterval: 15_000,
  });
}
