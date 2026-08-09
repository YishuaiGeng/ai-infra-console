import { z } from "zod";

import type { GPU, GPUProcess, Server, ServerStatus, ServerType } from "@/types";
import {
  mapModelDirectory,
  mapModelInstallation,
  modelDirectoryDtoSchema,
  modelInstallationDtoSchema,
} from "@/lib/api/models";

const nullableNumber = z.number().nullable();
const nullableString = z.string().nullable();

const runtimeSchema = z.object({
  available: z.boolean(),
  version: nullableString,
});

const serverMetricSchema = z.object({
  collected_at: z.string(),
  uptime_seconds: z.number().int().nullable(),
  cpu_utilization: nullableNumber,
  memory_used: z.number().int().nullable(),
  memory_total: z.number().int().nullable(),
  disk_used: z.number().int().nullable(),
  disk_total: z.number().int().nullable(),
  network_bytes_sent: z.number().int().nullable(),
  network_bytes_received: z.number().int().nullable(),
  architecture: nullableString,
  runtimes: z.record(z.string(), runtimeSchema),
});

const serverReferenceSchema = z.object({
  id: z.string(),
  name: z.string(),
  type: z.string(),
  status: z.string(),
  host: nullableString,
  hostname: nullableString,
});

export const gpuDtoSchema = z.object({
  id: z.string(),
  server: serverReferenceSchema,
  index: z.number().int(),
  uuid: z.string(),
  vendor: z.string(),
  name: z.string(),
  status: z.enum([
    "available",
    "active",
    "high-load",
    "memory-full",
    "unavailable",
  ]),
  utilization: nullableNumber,
  memory_used: z.number().int().nullable(),
  memory_total: z.number().int(),
  temperature: nullableNumber,
  power_usage: nullableNumber,
  power_limit: nullableNumber,
  fan_speed: nullableNumber,
  driver_version: nullableString,
  cuda_version: nullableString,
  metric_collected_at: nullableString,
  process_count: z.number().int(),
  deployment_id: nullableString.optional().default(null),
  deployment_name: nullableString.optional().default(null),
});

export const processDtoSchema = z.object({
  id: z.string(),
  gpu_id: z.string(),
  gpu_index: z.number().int(),
  gpu_name: z.string(),
  pid: z.number().int(),
  username: nullableString,
  command: nullableString,
  memory_used: z.number().int().nullable(),
  collected_at: z.string(),
});

export const serverDtoSchema = z.object({
  id: z.string(),
  name: z.string(),
  status: z.string(),
  type: z.string(),
  provider: nullableString,
  host: nullableString,
  hostname: nullableString,
  description: nullableString,
  tags: z.array(z.string()),
  os: nullableString,
  kernel: nullableString,
  cpu_model: nullableString,
  cpu_cores: z.number().int().nullable(),
  memory_total: z.number().int().nullable(),
  disk_total: z.number().int().nullable(),
  agent_version: nullableString,
  last_seen: nullableString,
  created_at: z.string(),
  updated_at: z.string(),
  metric: serverMetricSchema.nullable(),
  gpu_count: z.number().int(),
  available_gpu_count: z.number().int(),
  gpu_memory_total: z.number().int(),
  gpu_models: z.array(z.string()),
  model_count: z.number().int(),
});

export const serverDetailDtoSchema = serverDtoSchema.extend({
  gpus: z.array(gpuDtoSchema),
  processes: z.array(processDtoSchema),
  models: z.array(modelInstallationDtoSchema),
  model_directories: z.array(modelDirectoryDtoSchema),
});

export const infrastructureSummarySchema = z.object({
  server_count: z.number().int(),
  online_server_count: z.number().int(),
  offline_server_count: z.number().int(),
  gpu_count: z.number().int(),
  available_gpu_count: z.number().int(),
  gpu_memory_used: z.number().int(),
  gpu_memory_total: z.number().int(),
  latest_collected_at: nullableString,
});

export const registrationResponseSchema = z.object({
  server_id: z.string(),
  registration_token: z.string(),
});

export const infrastructureEventSchema = z.object({
  id: z.string(),
  kind: z.enum([
    "server.updated",
    "server.offline",
    "model.inventory.updated",
    "model.download.updated",
    "deployment.updated",
    "deployment.logs.updated",
  ]),
  server_id: z.string(),
  occurred_at: z.string(),
});

export type ServerDto = z.infer<typeof serverDtoSchema>;
export type ServerDetailDto = z.infer<typeof serverDetailDtoSchema>;
export type GpuDto = z.infer<typeof gpuDtoSchema>;
export type InfrastructureSummary = z.infer<typeof infrastructureSummarySchema>;
export type RegistrationResponse = z.infer<typeof registrationResponseSchema>;

export const infrastructureQueryKeys = {
  all: ["infrastructure"] as const,
  summary: ["infrastructure", "summary"] as const,
  servers: ["infrastructure", "servers"] as const,
  server: (id: string) => ["infrastructure", "servers", id] as const,
  gpus: ["infrastructure", "gpus"] as const,
};

export function infrastructureEventQueryKeys(
  serverId: string,
  kind: z.infer<typeof infrastructureEventSchema>["kind"] = "server.updated",
) {
  const keys: readonly (readonly string[])[] = [
    infrastructureQueryKeys.summary,
    infrastructureQueryKeys.servers,
    infrastructureQueryKeys.gpus,
    infrastructureQueryKeys.server(serverId),
  ];
  if (kind === "model.inventory.updated") {
    return [...keys, ["models"], ["models", "summary"], ["downloads"]];
  }
  if (kind === "model.download.updated") return [...keys, ["downloads"]];
  return kind.startsWith("deployment.")
    ? [...keys, ["deployments"], ["models"], ["models", "summary"]]
    : keys;
}

const bytesPerGiB = 1024 ** 3;

export function bytesToGiB(value: number | null) {
  return value === null ? null : Math.round((value / bytesPerGiB) * 10) / 10;
}

function serverStatus(status: string): ServerStatus {
  return ["online", "offline", "pending", "warning", "unknown"].includes(status)
    ? (status as ServerStatus)
    : "unknown";
}

function serverType(type: string): ServerType {
  return type === "cloud" ? "cloud" : "local";
}

function uptimeLabel(seconds: number | null | undefined) {
  if (seconds === null || seconds === undefined) return "Not reported";
  const days = Math.floor(seconds / 86_400);
  const hours = Math.floor((seconds % 86_400) / 3_600);
  return days > 0 ? `${days}d ${hours}h` : `${hours}h`;
}

export function mapServer(dto: ServerDto): Server {
  const metric = dto.metric;
  const hostLabel = dto.host ?? dto.hostname ?? "Not reported";
  return {
    id: dto.id,
    name: dto.name,
    status: serverStatus(dto.status),
    type: serverType(dto.type),
    provider: dto.provider ?? "Self-hosted",
    host: hostLabel,
    ip: dto.host ?? "Not reported",
    description: dto.description ?? "No description provided.",
    tags: dto.tags,
    gpuModel: dto.gpu_models.join(", ") || "CPU only",
    gpuCount: dto.gpu_count,
    gpuMemoryTotalGb: bytesToGiB(dto.gpu_memory_total) ?? 0,
    cpuUsage: metric?.cpu_utilization ?? null,
    cpuModel: dto.cpu_model ?? "Not reported",
    cpuCores: dto.cpu_cores ?? 0,
    ramUsedGb: bytesToGiB(metric?.memory_used ?? null),
    ramTotalGb: bytesToGiB(metric?.memory_total ?? dto.memory_total) ?? 0,
    diskUsedGb: bytesToGiB(metric?.disk_used ?? null),
    diskTotalGb: bytesToGiB(metric?.disk_total ?? dto.disk_total) ?? 0,
    modelCount: dto.model_count,
    runningCount: 0,
    lastSeen: dto.last_seen ?? dto.created_at,
    hostname: dto.hostname ?? "Not reported",
    os: dto.os ?? "Not reported",
    kernel: dto.kernel ?? "Not reported",
    uptime: uptimeLabel(metric?.uptime_seconds),
    agentVersion: dto.agent_version ?? "Not connected",
    networkRxMbps: null,
    networkTxMbps: null,
  };
}

export function mapServerDetail(dto: ServerDetailDto) {
  return {
    server: mapServer(dto),
    gpus: dto.gpus.map(mapGpu),
    processes: dto.processes.map(mapProcess),
    models: dto.models.map(mapModelInstallation),
    modelDirectories: dto.model_directories.map(mapModelDirectory),
  };
}

export function mapGpu(dto: GpuDto): GPU {
  return {
    id: dto.id,
    serverId: dto.server.id,
    serverName: dto.server.name,
    serverType: serverType(dto.server.type),
    serverHost: dto.server.host ?? dto.server.hostname ?? "Not reported",
    index: dto.index,
    name: dto.name,
    status: dto.status,
    utilization: dto.utilization,
    memoryUsedGb: bytesToGiB(dto.memory_used),
    memoryTotalGb: bytesToGiB(dto.memory_total) ?? 0,
    temperatureC: dto.temperature,
    powerWatts: dto.power_usage,
    powerLimitWatts: dto.power_limit ?? 0,
    workload:
      dto.deployment_name ??
      (dto.process_count > 0
        ? `${dto.process_count} active process${dto.process_count === 1 ? "" : "es"}`
        : null),
    deploymentId: dto.deployment_id,
  };
}

export function mapProcess(dto: z.infer<typeof processDtoSchema>): GPUProcess {
  return {
    id: dto.id,
    gpuId: dto.gpu_id,
    gpuIndex: dto.gpu_index,
    gpuName: dto.gpu_name,
    pid: dto.pid,
    user: dto.username ?? "Unknown",
    command: dto.command ?? "Unknown",
    memoryGb: bytesToGiB(dto.memory_used) ?? 0,
    startedAt: dto.collected_at,
  };
}

interface ApiErrorEnvelope {
  error?: { code?: string; message?: string; request_id?: string };
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string,
    readonly requestId?: string,
  ) {
    super(message);
  }
}

export async function apiRequest<T>(
  path: string,
  schema: z.ZodType<T>,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      accept: "application/json",
      ...(init?.body ? { "content-type": "application/json" } : {}),
      ...init?.headers,
    },
    cache: "no-store",
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ApiErrorEnvelope;
    if (response.status === 401 && typeof window !== "undefined") {
      window.location.replace(`/login?next=${encodeURIComponent(window.location.pathname)}`);
    }
    throw new ApiError(
      body.error?.message ?? "The request failed.",
      response.status,
      body.error?.code ?? "request_failed",
      body.error?.request_id,
    );
  }
  return schema.parse(await response.json());
}
