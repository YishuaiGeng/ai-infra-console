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
  | "starting"
  | "running"
  | "stopping"
  | "stopped"
  | "failed"
  | "unknown";

export type DownloadStatus =
  | "queued"
  | "downloading"
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

export interface DeploymentConfig {
  tensorParallelSize: number;
  gpuMemoryUtilization: number;
  maxModelLength: number;
  dataType: string;
  trustRemoteCode: boolean;
  extraArguments: string;
}

export interface Deployment {
  id: string;
  name: string;
  modelId: string;
  serverId: string;
  gpuIds: string[];
  backend: "vLLM" | "Ollama";
  port: number;
  status: DeploymentStatus;
  uptime: string;
  endpoint: string;
  createdAt: string;
  updatedAt: string;
  errorMessage?: string;
  config: DeploymentConfig;
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
