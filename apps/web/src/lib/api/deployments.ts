import { z } from "zod";

import type {
  Deployment,
  DeploymentLog,
  DeploymentOperation,
  DeploymentTarget,
  ModelServer,
  ServerStatus,
  ServerType,
} from "@/types";

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

const deploymentGpuDtoSchema = z.object({
  id: z.string(),
  index: z.number().int(),
  uuid: z.string(),
  name: z.string(),
  status: z.string(),
  memory_total: z.number().int(),
  memory_used: z.number().int().nullable(),
  utilization: nullableNumber,
});

const deploymentModelDtoSchema = z.object({
  id: z.string(),
  model_file_id: z.string(),
  source: z.string(),
  source_id: z.string(),
  name: z.string(),
  display_name: z.string(),
  path: z.string(),
  format: nullableString,
  quantization: nullableString,
  revision: nullableString,
  size: z.number().int().nullable(),
});

const deploymentOperationDtoSchema = z.object({
  id: z.string(),
  action: z.enum(["create", "start", "stop", "restart", "delete"]),
  status: z.enum(["queued", "running", "completed", "failed"]),
  generation: z.number().int(),
  attempt_count: z.number().int(),
  error_code: nullableString,
  error_message: nullableString,
  started_at: nullableString,
  completed_at: nullableString,
  created_at: z.string(),
  updated_at: z.string(),
});

export const deploymentDtoSchema = z.object({
  id: z.string(),
  name: z.string(),
  model: deploymentModelDtoSchema,
  server: modelServerDtoSchema,
  gpus: z.array(deploymentGpuDtoSchema),
  backend: z.literal("vllm"),
  selection_mode: z.enum(["automatic", "manual"]),
  desired_state: z.enum(["running", "stopped", "deleted"]),
  status: z.enum([
    "queued",
    "starting",
    "running",
    "stopping",
    "stopped",
    "restarting",
    "deleting",
    "failed",
    "unknown",
  ]),
  generation: z.number().int(),
  port: z.number().int(),
  endpoint: z.string(),
  config: z.object({
    tensor_parallel_size: z.number().int(),
    gpu_memory_utilization: z.number(),
    max_model_length: z.number().int(),
    data_type: z.string(),
    trust_remote_code: z.boolean(),
    extra_arguments: z.array(z.string()),
  }),
  health_status: z.enum(["healthy", "degraded", "unhealthy", "unknown"]),
  health_latency_ms: nullableNumber,
  last_health_checked_at: nullableString,
  last_reconciled_at: nullableString,
  uptime_seconds: z.number().int().nullable(),
  error_code: nullableString,
  error_message: nullableString,
  current_operation: deploymentOperationDtoSchema.nullable(),
  started_at: nullableString,
  stopped_at: nullableString,
  created_at: z.string(),
  updated_at: z.string(),
});

export const deploymentTargetDtoSchema = z.object({
  server: modelServerDtoSchema,
  docker_available: z.boolean(),
  docker_version: nullableString,
  model_files: z.array(deploymentModelDtoSchema),
  gpus: z.array(deploymentGpuDtoSchema),
});

export const deploymentLogDtoSchema = z.object({
  sequence: z.number().int(),
  timestamp: z.string(),
  stream: z.enum(["stdout", "stderr"]),
  message: z.string(),
});

export const apiEndpointTestResponseSchema = z.object({
  response: z.string(),
  latency_ms: z.number(),
  input_tokens: z.number().int().nullable(),
  output_tokens: z.number().int().nullable(),
  total_tokens: z.number().int().nullable(),
  model: nullableString,
});

export type DeploymentAction = "start" | "stop" | "restart" | "retry" | "delete";

export interface ApiEndpointTestInput {
  prompt: string;
  maxTokens: number;
  temperature: number;
}

export interface ApiEndpointTestResult {
  response: string;
  latencyMs: number;
  inputTokens: number | null;
  outputTokens: number | null;
  totalTokens: number | null;
  model: string | null;
}

export interface DeploymentCreateInput {
  name: string;
  modelFileId: string;
  selectionMode: "automatic" | "manual";
  gpuIds: string[];
  port: number;
  tensorParallelSize: number;
  gpuMemoryUtilization: number;
  maxModelLength: number;
  dataType: "auto" | "float16" | "bfloat16";
  trustRemoteCode: boolean;
  extraArguments: string[];
}

export function deploymentCreatePayload(input: DeploymentCreateInput) {
  return {
    name: input.name,
    model_file_id: input.modelFileId,
    selection_mode: input.selectionMode,
    gpu_ids: input.gpuIds,
    port: input.port,
    config: {
      tensor_parallel_size: input.tensorParallelSize,
      gpu_memory_utilization: input.gpuMemoryUtilization,
      max_model_length: input.maxModelLength,
      data_type: input.dataType,
      trust_remote_code: input.trustRemoteCode,
      extra_arguments: input.extraArguments,
    },
  };
}

export function deploymentLogPath(id: string, search: string, limit: number) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (search) params.set("search", search);
  return `/api/deployments/${encodeURIComponent(id)}/logs?${params.toString()}`;
}

export function apiEndpointTestPayload(input: ApiEndpointTestInput) {
  return {
    prompt: input.prompt,
    max_tokens: input.maxTokens,
    temperature: input.temperature,
  };
}

export const deploymentQueryKeys = {
  all: ["deployments"] as const,
  list: ["deployments", "list"] as const,
  targets: ["deployments", "targets"] as const,
  detail: (id: string) => ["deployments", "detail", id] as const,
  logs: (id: string, search: string, limit: number) =>
    ["deployments", "logs", id, search, limit] as const,
};

function serverStatus(value: string): ServerStatus {
  return ["online", "offline", "pending", "warning", "unknown"].includes(value)
    ? (value as ServerStatus)
    : "unknown";
}

function serverType(value: string): ServerType {
  return value === "cloud" ? "cloud" : "local";
}

function mapServer(dto: z.infer<typeof modelServerDtoSchema>): ModelServer {
  return {
    id: dto.id,
    name: dto.name,
    status: serverStatus(dto.status),
    type: serverType(dto.type),
    host: dto.host ?? dto.hostname ?? "Not reported",
  };
}

function mapGpu(dto: z.infer<typeof deploymentGpuDtoSchema>) {
  return {
    id: dto.id,
    index: dto.index,
    uuid: dto.uuid,
    name: dto.name,
    status: dto.status,
    memoryTotal: dto.memory_total,
    memoryUsed: dto.memory_used,
    utilization: dto.utilization,
  };
}

function mapModel(dto: z.infer<typeof deploymentModelDtoSchema>) {
  return {
    id: dto.id,
    modelFileId: dto.model_file_id,
    source: dto.source,
    sourceId: dto.source_id,
    name: dto.name,
    displayName: dto.display_name,
    path: dto.path,
    format: dto.format,
    quantization: dto.quantization,
    revision: dto.revision,
    sizeBytes: dto.size,
  };
}

function mapOperation(
  dto: z.infer<typeof deploymentOperationDtoSchema>,
): DeploymentOperation {
  return {
    id: dto.id,
    action: dto.action,
    status: dto.status,
    generation: dto.generation,
    attemptCount: dto.attempt_count,
    errorCode: dto.error_code,
    errorMessage: dto.error_message,
    startedAt: dto.started_at,
    completedAt: dto.completed_at,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

export function mapDeployment(dto: z.infer<typeof deploymentDtoSchema>): Deployment {
  return {
    id: dto.id,
    name: dto.name,
    model: mapModel(dto.model),
    server: mapServer(dto.server),
    gpus: dto.gpus.map(mapGpu),
    backend: dto.backend,
    selectionMode: dto.selection_mode,
    desiredState: dto.desired_state,
    status: dto.status,
    generation: dto.generation,
    port: dto.port,
    endpoint: dto.endpoint,
    config: {
      tensorParallelSize: dto.config.tensor_parallel_size,
      gpuMemoryUtilization: dto.config.gpu_memory_utilization,
      maxModelLength: dto.config.max_model_length,
      dataType: dto.config.data_type,
      trustRemoteCode: dto.config.trust_remote_code,
      extraArguments: dto.config.extra_arguments,
    },
    healthStatus: dto.health_status,
    healthLatencyMs: dto.health_latency_ms,
    lastHealthCheckedAt: dto.last_health_checked_at,
    lastReconciledAt: dto.last_reconciled_at,
    uptimeSeconds: dto.uptime_seconds,
    errorCode: dto.error_code,
    errorMessage: dto.error_message,
    currentOperation: dto.current_operation ? mapOperation(dto.current_operation) : null,
    startedAt: dto.started_at,
    stoppedAt: dto.stopped_at,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

export function mapDeploymentTarget(
  dto: z.infer<typeof deploymentTargetDtoSchema>,
): DeploymentTarget {
  return {
    server: mapServer(dto.server),
    dockerAvailable: dto.docker_available,
    dockerVersion: dto.docker_version,
    modelFiles: dto.model_files.map(mapModel),
    gpus: dto.gpus.map(mapGpu),
  };
}

export function mapDeploymentLog(
  dto: z.infer<typeof deploymentLogDtoSchema>,
): DeploymentLog {
  return {
    sequence: dto.sequence,
    timestamp: dto.timestamp,
    stream: dto.stream,
    message: dto.message,
  };
}

export function mapApiEndpointTestResult(
  dto: z.infer<typeof apiEndpointTestResponseSchema>,
): ApiEndpointTestResult {
  return {
    response: dto.response,
    latencyMs: dto.latency_ms,
    inputTokens: dto.input_tokens,
    outputTokens: dto.output_tokens,
    totalTokens: dto.total_tokens,
    model: dto.model,
  };
}

export function availableDeploymentActions(deployment: Deployment): DeploymentAction[] {
  if (
    deployment.currentOperation &&
    ["queued", "running"].includes(deployment.currentOperation.status)
  ) {
    return [];
  }
  if (deployment.status === "running") return ["stop", "restart", "delete"];
  if (deployment.status === "stopped") return ["start", "delete"];
  if (deployment.status === "failed") return ["retry", "delete"];
  if (deployment.status === "unknown") return ["delete"];
  return [];
}
