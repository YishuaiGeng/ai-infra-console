export type ServerStatus =
  | "online"
  | "offline"
  | "pending"
  | "warning"
  | "unknown";
export type ServerType = "local" | "cloud";

export type GPUStatus =
  | "available"
  | "active"
  | "high-load"
  | "memory-full"
  | "unavailable";

export type DeploymentStatus =
  | "queued"
  | "starting"
  | "running"
  | "stopping"
  | "stopped"
  | "restarting"
  | "deleting"
  | "failed"
  | "unknown";

export type DeploymentHealth =
  | "healthy"
  | "degraded"
  | "unhealthy"
  | "unknown";

export type DownloadStatus =
  | "queued"
  | "downloading"
  | "cancelling"
  | "completed"
  | "failed"
  | "cancelled";

export type ModelProvider = "Hugging Face" | "ModelScope" | "Local";

export interface Server {
  id: string;
  name: string;
  status: ServerStatus;
  type: ServerType;
  provider: string;
  host: string;
  ip: string;
  description: string;
  tags: string[];
  gpuModel: string;
  gpuCount: number;
  gpuMemoryTotalGb: number;
  cpuUsage: number | null;
  cpuModel: string;
  cpuCores: number;
  ramUsedGb: number | null;
  ramTotalGb: number;
  diskUsedGb: number | null;
  diskTotalGb: number;
  modelCount: number;
  runningCount: number;
  lastSeen: string;
  hostname: string;
  os: string;
  kernel: string;
  uptime: string;
  agentVersion: string;
  networkRxMbps: number | null;
  networkTxMbps: number | null;
}

export interface GPU {
  id: string;
  serverId: string;
  serverName?: string;
  serverType?: ServerType;
  serverHost?: string;
  index: number;
  name: string;
  status: GPUStatus;
  utilization: number | null;
  memoryUsedGb: number | null;
  memoryTotalGb: number;
  temperatureC: number | null;
  powerWatts: number | null;
  powerLimitWatts: number;
  workload: string | null;
  deploymentId: string | null;
}

export interface GPUProcess {
  id: string;
  gpuId: string;
  gpuIndex?: number;
  gpuName?: string;
  pid: number;
  user: string;
  command: string;
  memoryGb: number;
  startedAt: string;
}

export interface ModelDefinition {
  id: string;
  provider: ModelProvider;
  name: string;
  displayName: string;
  type: "LLM" | "Embedding" | "Reranker";
  parameters: string;
  license: string;
  source: string;
  description: string;
  tags: string[];
  downloads: string;
  contextLength: string;
  architecture: string;
}

export interface CatalogModel {
  id: string;
  provider: "huggingface" | "modelscope";
  providerLabel: "Hugging Face" | "ModelScope";
  sourceId: string;
  displayName: string;
  modelType: string;
  description: string;
  tags: string[];
  downloads: number | null;
  likes: number | null;
  license: string;
  gated: boolean;
  private: boolean;
  revision: string;
  sizeBytes: number | null;
  architecture: string;
  lastModified: string | null;
  sourceUrl: string;
}

export interface DownloadTarget {
  server: ModelServer;
  directories: ModelDirectory[];
}

export interface ModelDownloadTask {
  id: string;
  modelId: string | null;
  server: ModelServer;
  directoryId: string | null;
  targetPath: string;
  provider: "huggingface" | "modelscope";
  sourceId: string;
  revision: string;
  status: DownloadStatus;
  downloadedSize: number;
  totalSize: number | null;
  speedBytesPerSecond: number | null;
  progress: number | null;
  attemptCount: number;
  errorCode: string | null;
  errorMessage: string | null;
  startedAt: string | null;
  completedAt: string | null;
  lastProgressAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ModelDeleteTask {
  id: string;
  modelFileId: string | null;
  status: "queued" | "deleting" | "completed" | "failed";
  targetPath: string;
}

export interface ModelFile {
  id: string;
  modelId: string;
  serverId: string;
  sizeGb: number;
  format: "Safetensors" | "GGUF" | "Ollama";
  path: string;
  status: "installed" | "verifying" | "error";
  deployments: number;
  quantization: string;
  revision: string;
}

export interface ModelServer {
  id: string;
  name: string;
  status: ServerStatus;
  type: ServerType;
  host: string;
}

export interface ModelInstallation {
  id: string;
  modelId: string;
  source: string;
  sourceId: string;
  name: string;
  displayName: string;
  description: string;
  architecture: string;
  modelType: string;
  metadata: Record<string, string>;
  server: ModelServer;
  directoryId: string | null;
  path: string;
  sizeBytes: number | null;
  fileCount: number;
  format: string;
  quantization: string;
  revision: string;
  status: "discovered" | "stale" | "missing" | "error";
  lastSeenAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ModelDirectory {
  id: string;
  serverId: string;
  path: string;
  isDefault: boolean;
  isAllowed: boolean;
  isAvailable: boolean;
  errorCode: string | null;
  lastScannedAt: string | null;
  modelCount: number;
}

export interface ModelDetail {
  id: string;
  source: string;
  sourceId: string;
  name: string;
  displayName: string;
  description: string;
  architecture: string;
  modelType: string;
  metadata: Record<string, string>;
  locations: ModelInstallation[];
}

export interface DeploymentConfig {
  tensorParallelSize: number;
  gpuMemoryUtilization: number;
  maxModelLength: number;
  dataType: string;
  trustRemoteCode: boolean;
  extraArguments: string[];
}

export interface DeploymentModel {
  id: string;
  modelFileId: string;
  source: string;
  sourceId: string;
  name: string;
  displayName: string;
  path: string;
  format: string | null;
  quantization: string | null;
  revision: string | null;
  sizeBytes: number | null;
}

export interface DeploymentGPU {
  id: string;
  index: number;
  uuid: string;
  name: string;
  status: string;
  memoryTotal: number;
  memoryUsed: number | null;
  utilization: number | null;
}

export interface DeploymentOperation {
  id: string;
  action: "create" | "start" | "stop" | "restart" | "delete";
  status: "queued" | "running" | "completed" | "failed";
  generation: number;
  attemptCount: number;
  errorCode: string | null;
  errorMessage: string | null;
  startedAt: string | null;
  completedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface Deployment {
  id: string;
  name: string;
  model: DeploymentModel;
  server: ModelServer;
  gpus: DeploymentGPU[];
  backend: "vllm";
  selectionMode: "automatic" | "manual";
  desiredState: "running" | "stopped" | "deleted";
  generation: number;
  port: number;
  status: DeploymentStatus;
  endpoint: string;
  healthStatus: DeploymentHealth;
  healthLatencyMs: number | null;
  lastHealthCheckedAt: string | null;
  lastReconciledAt: string | null;
  uptimeSeconds: number | null;
  errorCode: string | null;
  errorMessage: string | null;
  currentOperation: DeploymentOperation | null;
  startedAt: string | null;
  stoppedAt: string | null;
  createdAt: string;
  updatedAt: string;
  config: DeploymentConfig;
}

export interface DeploymentTarget {
  server: ModelServer;
  dockerAvailable: boolean;
  dockerVersion: string | null;
  modelFiles: DeploymentModel[];
  gpus: DeploymentGPU[];
}

export interface DeploymentLog {
  sequence: number;
  timestamp: string;
  stream: "stdout" | "stderr";
  message: string;
}

export interface DownloadTask {
  id: string;
  modelId: string;
  serverId: string;
  progress: number;
  downloadedGb: number;
  totalGb: number;
  speedMbps: number;
  status: DownloadStatus;
  startedAt: string;
  targetDirectory: string;
  revision: string;
  errorMessage?: string;
}

export interface ApiEndpoint {
  id: string;
  deploymentId: string;
  modelId: string;
  serverId: string;
  endpoint: string;
  backend: "vLLM" | "Ollama";
  status: "healthy" | "degraded" | "offline";
  port: number;
  latencyMs: number | null;
  lastChecked: string;
}

export interface ActivityLog {
  id: string;
  time: string;
  user: string;
  action: string;
  resource: string;
  serverId: string | null;
  status: "success" | "failed" | "warning";
  detail: string;
}

export interface SystemSettings {
  consoleName: string;
  timezone: string;
  language: string;
  heartbeatInterval: number;
  offlineThreshold: number;
  metricsRetentionDays: number;
  defaultModelDirectory: string;
  defaultBackend: "vLLM" | "Ollama";
  defaultPort: number;
  defaultGpuMemoryUtilization: number;
  requireDeleteConfirmation: boolean;
  auditLogRetentionDays: number;
}
