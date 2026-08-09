import { z } from "zod";

import type { MetricsHistory, NotificationList } from "@/types";

const nullableNumber = z.number().nullable();

const serverMetricPointDtoSchema = z.object({
  server_id: z.string(),
  server_name: z.string(),
  collected_at: z.string(),
  cpu_utilization: nullableNumber,
  memory_used: z.number().int().nullable(),
  memory_total: z.number().int().nullable(),
  disk_used: z.number().int().nullable(),
  disk_total: z.number().int().nullable(),
  network_bytes_sent: z.number().int().nullable(),
  network_bytes_received: z.number().int().nullable(),
});

const gpuMetricPointDtoSchema = z.object({
  gpu_id: z.string(),
  server_id: z.string(),
  server_name: z.string(),
  gpu_index: z.number().int(),
  gpu_name: z.string(),
  collected_at: z.string(),
  utilization: nullableNumber,
  memory_used: z.number().int().nullable(),
  memory_total: z.number().int(),
  temperature: nullableNumber,
  power_usage: nullableNumber,
});

export const metricsHistoryDtoSchema = z.object({
  window_hours: z.number().int(),
  server_points: z.array(serverMetricPointDtoSchema),
  gpu_points: z.array(gpuMetricPointDtoSchema),
});

const notificationDtoSchema = z.object({
  id: z.string(),
  level: z.enum(["info", "warning", "critical"]),
  title: z.string(),
  message: z.string(),
  is_read: z.boolean(),
  source: z.enum(["derived", "stored"]),
  created_at: z.string(),
});

export const notificationListDtoSchema = z.object({
  unread_count: z.number().int(),
  items: z.array(notificationDtoSchema),
});

export const monitoringQueryKeys = {
  all: ["monitoring"] as const,
  metrics: (windowHours: number) => ["monitoring", "metrics", windowHours] as const,
  notifications: ["monitoring", "notifications"] as const,
};

export function metricsHistoryPath(windowHours: number) {
  return `/api/metrics/history?window_hours=${encodeURIComponent(String(windowHours))}`;
}

export function mapMetricsHistory(
  dto: z.infer<typeof metricsHistoryDtoSchema>,
): MetricsHistory {
  return {
    windowHours: dto.window_hours,
    serverPoints: dto.server_points.map((point) => ({
      serverId: point.server_id,
      serverName: point.server_name,
      collectedAt: point.collected_at,
      cpuUtilization: point.cpu_utilization,
      memoryUsed: point.memory_used,
      memoryTotal: point.memory_total,
      diskUsed: point.disk_used,
      diskTotal: point.disk_total,
    })),
    gpuPoints: dto.gpu_points.map((point) => ({
      gpuId: point.gpu_id,
      serverId: point.server_id,
      serverName: point.server_name,
      gpuIndex: point.gpu_index,
      gpuName: point.gpu_name,
      collectedAt: point.collected_at,
      utilization: point.utilization,
      memoryUsed: point.memory_used,
      memoryTotal: point.memory_total,
      temperature: point.temperature,
      powerUsage: point.power_usage,
    })),
  };
}

export function mapNotificationList(
  dto: z.infer<typeof notificationListDtoSchema>,
): NotificationList {
  return {
    unreadCount: dto.unread_count,
    items: dto.items.map((item) => ({
      id: item.id,
      level: item.level,
      title: item.title,
      message: item.message,
      isRead: item.is_read,
      source: item.source,
      createdAt: item.created_at,
    })),
  };
}
