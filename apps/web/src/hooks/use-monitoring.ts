"use client";

import { useQuery } from "@tanstack/react-query";

import {
  mapMetricsHistory,
  mapNotificationList,
  metricsHistoryDtoSchema,
  metricsHistoryPath,
  monitoringQueryKeys,
  notificationListDtoSchema,
} from "@/lib/api/monitoring";
import { apiRequest } from "@/lib/api/infrastructure";

export function useMetricsHistory(windowHours = 24) {
  return useQuery({
    queryKey: monitoringQueryKeys.metrics(windowHours),
    queryFn: async () =>
      mapMetricsHistory(await apiRequest(metricsHistoryPath(windowHours), metricsHistoryDtoSchema)),
    refetchInterval: 30_000,
  });
}

export function useNotifications() {
  return useQuery({
    queryKey: monitoringQueryKeys.notifications,
    queryFn: async () =>
      mapNotificationList(await apiRequest("/api/notifications", notificationListDtoSchema)),
    refetchInterval: 30_000,
  });
}
