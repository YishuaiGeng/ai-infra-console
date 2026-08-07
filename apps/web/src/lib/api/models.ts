import { z } from "zod";

import type {
  ModelDetail,
  ModelDirectory,
  ModelInstallation,
  ServerStatus,
  ServerType,
} from "@/types";

const nullableString = z.string().nullable();

const modelServerDtoSchema = z.object({
  id: z.string(),
  name: z.string(),
  status: z.string(),
  type: z.string(),
  host: nullableString,
  hostname: nullableString,
});

export const modelDirectoryDtoSchema = z.object({
  id: z.string(),
  server_id: z.string(),
  path: z.string(),
  is_default: z.boolean(),
  is_allowed: z.boolean(),
  is_available: z.boolean(),
  error_code: nullableString,
  last_scanned_at: nullableString,
  model_count: z.number().int(),
});

export const modelInstallationDtoSchema = z.object({
  id: z.string(),
  model_id: z.string(),
  source: z.string(),
  source_id: z.string(),
  name: z.string(),
  display_name: nullableString,
  description: nullableString,
  architecture: nullableString,
  model_type: nullableString,
  metadata: z.record(z.string(), z.string()),
  server: modelServerDtoSchema,
  directory_id: nullableString,
  path: z.string(),
  size: z.number().int().nullable(),
  file_count: z.number().int(),
  format: nullableString,
  quantization: nullableString,
  revision: nullableString,
  status: z.string(),
  last_seen_at: nullableString,
  created_at: z.string(),
  updated_at: z.string(),
});

export const modelDetailDtoSchema = z.object({
  id: z.string(),
  source: z.string(),
  source_id: z.string(),
  name: z.string(),
  display_name: nullableString,
  description: nullableString,
  architecture: nullableString,
  model_type: nullableString,
  metadata: z.record(z.string(), z.string()),
  locations: z.array(modelInstallationDtoSchema),
});

export const modelInventorySummaryDtoSchema = z.object({
  model_count: z.number().int(),
  installation_count: z.number().int(),
  current_installation_count: z.number().int(),
  server_count: z.number().int(),
  total_size: z.number().int(),
  formats: z.record(z.string(), z.number().int()),
  latest_scanned_at: nullableString,
});

export const defaultModelDirectoryResponseSchema = modelDirectoryDtoSchema;

export type ModelInventorySummary = z.infer<
  typeof modelInventorySummaryDtoSchema
>;

export const modelQueryKeys = {
  all: ["models"] as const,
  installations: ["models", "installations"] as const,
  detail: (id: string) => ["models", "detail", id] as const,
  summary: ["models", "summary"] as const,
};

function serverStatus(value: string): ServerStatus {
  return ["online", "offline", "pending", "warning", "unknown"].includes(value)
    ? (value as ServerStatus)
    : "unknown";
}

function serverType(value: string): ServerType {
  return value === "cloud" ? "cloud" : "local";
}

function installationStatus(
  value: string,
): ModelInstallation["status"] {
  return ["discovered", "stale", "missing", "error"].includes(value)
    ? (value as ModelInstallation["status"])
    : "error";
}

export function mapModelInstallation(
  dto: z.infer<typeof modelInstallationDtoSchema>,
): ModelInstallation {
  return {
    id: dto.id,
    modelId: dto.model_id,
    source: dto.source,
    sourceId: dto.source_id,
    name: dto.name,
    displayName: dto.display_name ?? dto.name,
    description: dto.description ?? "No description reported.",
    architecture: dto.architecture ?? "Not reported",
    modelType: dto.model_type ?? "Unknown",
    metadata: dto.metadata,
    server: {
      id: dto.server.id,
      name: dto.server.name,
      status: serverStatus(dto.server.status),
      type: serverType(dto.server.type),
      host: dto.server.host ?? dto.server.hostname ?? "Not reported",
    },
    directoryId: dto.directory_id,
    path: dto.path,
    sizeBytes: dto.size,
    fileCount: dto.file_count,
    format: dto.format ?? "unknown",
    quantization: dto.quantization ?? "Not reported",
    revision: dto.revision ?? "Not reported",
    status: installationStatus(dto.status),
    lastSeenAt: dto.last_seen_at,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

export function mapModelDirectory(
  dto: z.infer<typeof modelDirectoryDtoSchema>,
): ModelDirectory {
  return {
    id: dto.id,
    serverId: dto.server_id,
    path: dto.path,
    isDefault: dto.is_default,
    isAllowed: dto.is_allowed,
    isAvailable: dto.is_available,
    errorCode: dto.error_code,
    lastScannedAt: dto.last_scanned_at,
    modelCount: dto.model_count,
  };
}

export function mapModelDetail(
  dto: z.infer<typeof modelDetailDtoSchema>,
): ModelDetail {
  return {
    id: dto.id,
    source: dto.source,
    sourceId: dto.source_id,
    name: dto.name,
    displayName: dto.display_name ?? dto.name,
    description: dto.description ?? "No description reported.",
    architecture: dto.architecture ?? "Not reported",
    modelType: dto.model_type ?? "Unknown",
    metadata: dto.metadata,
    locations: dto.locations.map(mapModelInstallation),
  };
}
