import { describe, expect, it } from "vitest";

import {
  mapSystemSettings,
  systemSettingsDtoSchema,
  systemSettingsPayload,
} from "@/lib/api/settings";

describe("settings API mapping", () => {
  it("maps settings DTOs and update payloads", () => {
    const settings = mapSystemSettings(
      systemSettingsDtoSchema.parse({
        console_name: "Personal GPU Console",
        timezone: "Asia/Shanghai",
        language: "English",
        heartbeat_interval: 15,
        offline_threshold: 45,
        metrics_retention_days: 30,
        default_model_directory: "/data/models",
        default_backend: "vLLM",
        default_port: 8001,
        default_gpu_memory_utilization: 0.85,
        require_delete_confirmation: true,
        audit_log_retention_days: 120,
      }),
    );

    expect(settings).toMatchObject({
      consoleName: "Personal GPU Console",
      metricsRetentionDays: 30,
      defaultPort: 8001,
    });
    expect(systemSettingsPayload(settings)).toMatchObject({
      console_name: "Personal GPU Console",
      metrics_retention_days: 30,
      default_port: 8001,
    });
  });
});
