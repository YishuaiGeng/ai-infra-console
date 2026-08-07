import { z } from "zod";

import type {
  CatalogModel,
  DownloadTarget,
  ModelDeleteTask,
  ModelDownloadTask,
  ServerStatus,
  ServerType,
} from "@/types";
import { mapModelDirectory, modelDirectoryDtoSchema } from "@/lib/api/models";

export function pendingDownloadTaskId(
  cancelPending: boolean,
  cancelTaskId: string | undefined,
  retryPending: boolean,
  retryTaskId: string | undefined,
) {
  if (cancelPending) return cancelTaskId ?? null;
  if (retryPending) return retryTaskId ?? null;
  return null;
}

const nullableString = z.string().nullable();
const nullableNumber = z.number().nullable();

const modelServerDtoSchema = z.object({
  id: z.string(),
  name: z.string(),
  status: z.string(),
  type: z.string(),
  host: nullableString,
  hostname: nullableString,
});

export const catalogModelDtoSchema = z.object({
  provider: z.enum(["huggingface", "modelscope"]),
  source_id: z.string(),
  display_name: z.string(),
  model_type: nullableString,
  description: nullableString,
  tags: z.array(z.string()),
  downloads: nullableNumber,
  likes: nullableNumber,
  license: nullableString,
  gated: z.boolean(),
  private: z.boolean(),
  revision: nullableString,
  size: nullableNumber,
  architecture: nullableString,
  last_modified: nullableString,
});

export const catalogSearchDtoSchema = z.object({
  items: z.array(catalogModelDtoSchema),
  provider_errors: z.partialRecord(
    z.enum(["huggingface", "modelscope"]),
    z.string(),
  ),
});

export const downloadTargetDtoSchema = z.object({
  server: modelServerDtoSchema,
  directories: z.array(modelDirectoryDtoSchema),
});

export const downloadTaskDtoSchema = z.object({
  id: z.string(),
  model_id: nullableString,
  server: modelServerDtoSchema,
  directory_id: nullableString,
  target_path: z.string(),
  source: z.enum(["huggingface", "modelscope"]),
  source_id: z.string(),
  revision: z.string(),
  status: z.enum([
    "queued",
    "downloading",
    "cancelling",
    "completed",
    "failed",
    "cancelled",
  ]),
  downloaded_size: z.number().int(),
  total_size: z.number().int().nullable(),
  speed_bytes_per_second: z.number().int().nullable(),
  progress: z.number().nullable(),
  attempt_count: z.number().int(),
  error_code: nullableString,
  error_message: nullableString,
  started_at: nullableString,
  completed_at: nullableString,
  last_progress_at: nullableString,
  created_at: z.string(),
  updated_at: z.string(),
});

export const modelDeleteTaskDtoSchema = z.object({
  id: z.string(),
  model_file_id: nullableString,
  server: modelServerDtoSchema,
  directory_id: nullableString,
  source: z.string(),
  source_id: z.string(),
  target_path: z.string(),
  status: z.enum(["queued", "deleting", "completed", "failed"]),
  attempt_count: z.number().int(),
  error_code: nullableString,
  error_message: nullableString,
  started_at: nullableString,
  completed_at: nullableString,
  created_at: z.string(),
  updated_at: z.string(),
});

export type CatalogSearchResult = {
  items: CatalogModel[];
  providerErrors: Partial<Record<"huggingface" | "modelscope", string>>;
};

export interface DownloadCreateInput {
  provider: "huggingface" | "modelscope";
  sourceId: string;
  revision: string;
  serverId: string;
  directoryId: string;
}

export const downloadQueryKeys = {
  all: ["downloads"] as const,
  list: ["downloads", "list"] as const,
  targets: ["downloads", "targets"] as const,
  catalogAll: ["catalog"] as const,
  catalog: (query: string, provider: string) =>
    ["catalog", query, provider] as const,
};

function serverStatus(value: string): ServerStatus {
  return ["online", "offline", "pending", "warning", "unknown"].includes(value)
    ? (value as ServerStatus)
    : "unknown";
}

function serverType(value: string): ServerType {
  return value === "cloud" ? "cloud" : "local";
}

function mapServer(dto: z.infer<typeof modelServerDtoSchema>) {
  return {
    id: dto.id,
    name: dto.name,
    status: serverStatus(dto.status),
    type: serverType(dto.type),
    host: dto.host ?? dto.hostname ?? "Not reported",
  };
}

export function mapCatalogModel(
  dto: z.infer<typeof catalogModelDtoSchema>,
): CatalogModel {
  return {
    id: `${dto.provider}:${dto.source_id}`,
    provider: dto.provider,
    providerLabel:
      dto.provider === "huggingface" ? "Hugging Face" : "ModelScope",
    sourceId: dto.source_id,
    displayName: dto.display_name,
    modelType: dto.model_type ?? "Unknown",
    description: dto.description ?? "No provider description available.",
    tags: dto.tags,
    downloads: dto.downloads,
    likes: dto.likes,
    license: dto.license ?? "Not reported",
    gated: dto.gated,
    private: dto.private,
    revision: dto.revision ?? "main",
    sizeBytes: dto.size,
    architecture: dto.architecture ?? "Not reported",
    lastModified: dto.last_modified,
    sourceUrl:
      dto.provider === "huggingface"
        ? `https://huggingface.co/${dto.source_id}`
        : `https://modelscope.cn/models/${dto.source_id}`,
  };
}

export function mapCatalogSearch(
  dto: z.infer<typeof catalogSearchDtoSchema>,
): CatalogSearchResult {
  return {
    items: dto.items.map(mapCatalogModel),
    providerErrors: dto.provider_errors,
  };
}

export function mapDownloadTarget(
  dto: z.infer<typeof downloadTargetDtoSchema>,
): DownloadTarget {
  return {
    server: mapServer(dto.server),
    directories: dto.directories.map(mapModelDirectory),
  };
}

export function mapDownloadTask(
  dto: z.infer<typeof downloadTaskDtoSchema>,
): ModelDownloadTask {
  return {
    id: dto.id,
    modelId: dto.model_id,
    server: mapServer(dto.server),
    directoryId: dto.directory_id,
    targetPath: dto.target_path,
    provider: dto.source,
    sourceId: dto.source_id,
    revision: dto.revision,
    status: dto.status,
    downloadedSize: dto.downloaded_size,
    totalSize: dto.total_size,
    speedBytesPerSecond: dto.speed_bytes_per_second,
    progress: dto.progress,
    attemptCount: dto.attempt_count,
    errorCode: dto.error_code,
    errorMessage: dto.error_message,
    startedAt: dto.started_at,
    completedAt: dto.completed_at,
    lastProgressAt: dto.last_progress_at,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

export function mapDeleteTask(
  dto: z.infer<typeof modelDeleteTaskDtoSchema>,
): ModelDeleteTask {
  return {
    id: dto.id,
    modelFileId: dto.model_file_id,
    status: dto.status,
    targetPath: dto.target_path,
  };
}
