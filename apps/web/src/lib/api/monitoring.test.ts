import { describe, expect, it } from "vitest";

import {
  mapMetricsHistory,
  mapNotificationList,
  metricsHistoryDtoSchema,
  metricsHistoryPath,
  notificationListDtoSchema,
} from "@/lib/api/monitoring";

describe("monitoring API mapping", () => {
  it("maps metric history points", () => {
    expect(metricsHistoryPath(24)).toBe("/api/metrics/history?window_hours=24");
    expect(
      mapMetricsHistory(
        metricsHistoryDtoSchema.parse({
          window_hours: 24,
          server_points: [
            {
              server_id: "server-1",
              server_name: "xiao-pro6000",
              collected_at: "2026-08-10T00:00:00Z",
              cpu_utilization: 42,
              memory_used: 1024,
              memory_total: 2048,
              disk_used: 4096,
              disk_total: 8192,
              network_bytes_sent: 1,
              network_bytes_received: 2,
            },
          ],
          gpu_points: [
            {
              gpu_id: "gpu-1",
              server_id: "server-1",
              server_name: "xiao-pro6000",
              gpu_index: 0,
              gpu_name: "RTX 4090",
              collected_at: "2026-08-10T00:00:00Z",
              utilization: 80,
              memory_used: 1024,
              memory_total: 2048,
              temperature: 70,
              power_usage: 320,
            },
          ],
        }),
      ),
    ).toMatchObject({
      windowHours: 24,
      serverPoints: [{ serverName: "xiao-pro6000", cpuUtilization: 42 }],
      gpuPoints: [{ gpuName: "RTX 4090", utilization: 80 }],
    });
  });

  it("maps notification lists", () => {
    expect(
      mapNotificationList(
        notificationListDtoSchema.parse({
          unread_count: 1,
          items: [
            {
              id: "derived:server-offline",
              level: "critical",
              title: "xiao-pro6000 is offline",
              message: "The Agent heartbeat is outside the configured online window.",
              is_read: false,
              source: "derived",
              created_at: "2026-08-10T00:00:00Z",
            },
          ],
        }),
      ),
    ).toMatchObject({
      unreadCount: 1,
      items: [{ level: "critical", source: "derived" }],
    });
  });
});
