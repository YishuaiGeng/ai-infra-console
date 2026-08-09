import { z } from "zod";

import type { SystemSettings } from "@/types";

export const systemSettingsDtoSchema = z.object({
  console_name: z.string(),
  timezone: z.string(),
  language: z.string(),
  heartbeat_interval: z.number().int(),
  offline_threshold: z.number().int(),
  metrics_retention_days: z.number().int(),
  default_model_directory: z.string(),
  default_backend: z.enum(["vLLM", "Ollama"]),
  default_port: z.number().int(),
  default_gpu_memory_utilization: z.number(),
  require_delete_confirmation: z.boolean(),
  audit_log_retention_days: z.number().int(),
});

export const settingsQueryKeys = {
  all: ["settings"] as const,
};

export function mapSystemSettings(
  dto: z.infer<typeof systemSettingsDtoSchema>,
): SystemSettings {
  return {
    consoleName: dto.console_name,
    timezone: dto.timezone,
    language: dto.language,
    heartbeatInterval: dto.heartbeat_interval,
    offlineThreshold: dto.offline_threshold,
    metricsRetentionDays: dto.metrics_retention_days,
    defaultModelDirectory: dto.default_model_directory,
    defaultBackend: dto.default_backend,
    defaultPort: dto.default_port,
    defaultGpuMemoryUtilization: dto.default_gpu_memory_utilization,
    requireDeleteConfirmation: dto.require_delete_confirmation,
    auditLogRetentionDays: dto.audit_log_retention_days,
  };
}

export function systemSettingsPayload(input: SystemSettings) {
  return {
    console_name: input.consoleName,
    timezone: input.timezone,
    language: input.language,
    heartbeat_interval: input.heartbeatInterval,
    offline_threshold: input.offlineThreshold,
    metrics_retention_days: input.metricsRetentionDays,
    default_model_directory: input.defaultModelDirectory,
    default_backend: input.defaultBackend,
    default_port: input.defaultPort,
    default_gpu_memory_utilization: input.defaultGpuMemoryUtilization,
    require_delete_confirmation: input.requireDeleteConfirmation,
    audit_log_retention_days: input.auditLogRetentionDays,
  };
}
