import type {
  ActivityLog,
  ApiEndpoint,
  DownloadTask,
  GPU,
  GPUProcess,
  ModelDefinition,
  ModelFile,
  Server,
  SystemSettings,
} from "@/types";

export const servers: Server[] = [
  {
    id: "srv-lab-4090-01",
    name: "lab-4090-01",
    status: "online",
    type: "local",
    provider: "On-premise",
    host: "gpu-lab.internal",
    ip: "10.20.0.21",
    description: "Primary inference workstation for large language models.",
    tags: ["primary", "inference", "cuda-12"],
    gpuModel: "RTX 4090",
    gpuCount: 4,
    gpuMemoryTotalGb: 96,
    cpuUsage: 34,
    cpuModel: "AMD EPYC 9354P",
    cpuCores: 32,
    ramUsedGb: 184,
    ramTotalGb: 256,
    diskUsedGb: 6220,
    diskTotalGb: 8192,
    modelCount: 4,
    runningCount: 1,
    lastSeen: "2026-08-07T14:58:42Z",
    hostname: "lab-4090-01",
    os: "Ubuntu 24.04 LTS",
    kernel: "6.8.0-51-generic",
    uptime: "18d 07h 42m",
    agentVersion: "0.1.0-preview",
    networkRxMbps: 148,
    networkTxMbps: 62,
  },
  {
    id: "srv-lab-a6000-01",
    name: "lab-a6000-01",
    status: "online",
    type: "local",
    provider: "On-premise",
    host: "a6000-lab.internal",
    ip: "10.20.0.32",
    description: "Shared lab server for embeddings and evaluation workloads.",
    tags: ["shared", "evaluation"],
    gpuModel: "RTX A6000",
    gpuCount: 4,
    gpuMemoryTotalGb: 192,
    cpuUsage: 12,
    cpuModel: "AMD Threadripper PRO 5975WX",
    cpuCores: 32,
    ramUsedGb: 108,
    ramTotalGb: 256,
    diskUsedGb: 3910,
    diskTotalGb: 8192,
    modelCount: 5,
    runningCount: 1,
    lastSeen: "2026-08-07T14:58:39Z",
    hostname: "lab-a6000-01",
    os: "Ubuntu 22.04 LTS",
    kernel: "5.15.0-118-generic",
    uptime: "42d 16h 11m",
    agentVersion: "0.1.0-preview",
    networkRxMbps: 39,
    networkTxMbps: 18,
  },
  {
    id: "srv-cloud-h100-01",
    name: "cloud-h100-01",
    status: "online",
    type: "cloud",
    provider: "Cloud GPU",
    host: "h100-01.compute.example",
    ip: "172.31.8.14",
    description: "Burst capacity for high-throughput inference experiments.",
    tags: ["cloud", "burst", "high-throughput"],
    gpuModel: "H100 SXM",
    gpuCount: 1,
    gpuMemoryTotalGb: 80,
    cpuUsage: 51,
    cpuModel: "Intel Xeon Platinum 8480C",
    cpuCores: 56,
    ramUsedGb: 318,
    ramTotalGb: 512,
    diskUsedGb: 1320,
    diskTotalGb: 2048,
    modelCount: 2,
    runningCount: 1,
    lastSeen: "2026-08-07T14:58:44Z",
    hostname: "cloud-h100-01",
    os: "Ubuntu 24.04 LTS",
    kernel: "6.8.0-48-cloud",
    uptime: "3d 21h 08m",
    agentVersion: "0.1.0-preview",
    networkRxMbps: 622,
    networkTxMbps: 481,
  },
  {
    id: "srv-lab-old-01",
    name: "lab-old-01",
    status: "offline",
    type: "local",
    provider: "On-premise",
    host: "old-gpu.internal",
    ip: "10.20.0.12",
    description: "Legacy experimentation node currently awaiting maintenance.",
    tags: ["legacy", "maintenance"],
    gpuModel: "RTX 3090",
    gpuCount: 2,
    gpuMemoryTotalGb: 48,
    cpuUsage: null,
    cpuModel: "AMD Ryzen 9 5950X",
    cpuCores: 16,
    ramUsedGb: null,
    ramTotalGb: 128,
    diskUsedGb: null,
    diskTotalGb: 4096,
    modelCount: 1,
    runningCount: 0,
    lastSeen: "2026-08-06T04:22:13Z",
    hostname: "lab-old-01",
    os: "Ubuntu 20.04 LTS",
    kernel: "5.4.0-196-generic",
    uptime: "--",
    agentVersion: "0.0.8-preview",
    networkRxMbps: null,
    networkTxMbps: null,
  },
];

export const gpus: GPU[] = [
  { id: "gpu-4090-0", serverId: "srv-lab-4090-01", index: 0, name: "RTX 4090", status: "active", utilization: 92, memoryUsedGb: 21.1, memoryTotalGb: 24, temperatureC: 73, powerWatts: 382, powerLimitWatts: 450, workload: "Qwen3-32B", deploymentId: "dep-qwen32" },
  { id: "gpu-4090-1", serverId: "srv-lab-4090-01", index: 1, name: "RTX 4090", status: "active", utilization: 75, memoryUsedGb: 18.4, memoryTotalGb: 24, temperatureC: 68, powerWatts: 318, powerLimitWatts: 450, workload: "Qwen3-32B", deploymentId: "dep-qwen32" },
  { id: "gpu-4090-2", serverId: "srv-lab-4090-01", index: 2, name: "RTX 4090", status: "available", utilization: 0, memoryUsedGb: 0.8, memoryTotalGb: 24, temperatureC: 36, powerWatts: 31, powerLimitWatts: 450, workload: null, deploymentId: null },
  { id: "gpu-4090-3", serverId: "srv-lab-4090-01", index: 3, name: "RTX 4090", status: "available", utilization: 4, memoryUsedGb: 1.2, memoryTotalGb: 24, temperatureC: 39, powerWatts: 38, powerLimitWatts: 450, workload: null, deploymentId: null },
  { id: "gpu-a6000-0", serverId: "srv-lab-a6000-01", index: 0, name: "RTX A6000", status: "active", utilization: 44, memoryUsedGb: 12.6, memoryTotalGb: 48, temperatureC: 59, powerWatts: 186, powerLimitWatts: 300, workload: "BGE-M3", deploymentId: "dep-bge" },
  { id: "gpu-a6000-1", serverId: "srv-lab-a6000-01", index: 1, name: "RTX A6000", status: "available", utilization: 2, memoryUsedGb: 0.9, memoryTotalGb: 48, temperatureC: 37, powerWatts: 27, powerLimitWatts: 300, workload: null, deploymentId: null },
  { id: "gpu-a6000-2", serverId: "srv-lab-a6000-01", index: 2, name: "RTX A6000", status: "high-load", utilization: 97, memoryUsedGb: 45.9, memoryTotalGb: 48, temperatureC: 81, powerWatts: 294, powerLimitWatts: 300, workload: "DeepSeek-R1 Distill", deploymentId: "dep-deepseek" },
  { id: "gpu-a6000-3", serverId: "srv-lab-a6000-01", index: 3, name: "RTX A6000", status: "available", utilization: 1, memoryUsedGb: 1.0, memoryTotalGb: 48, temperatureC: 38, powerWatts: 29, powerLimitWatts: 300, workload: null, deploymentId: null },
  { id: "gpu-h100-0", serverId: "srv-cloud-h100-01", index: 0, name: "H100 SXM", status: "memory-full", utilization: 96, memoryUsedGb: 74.2, memoryTotalGb: 80, temperatureC: 67, powerWatts: 612, powerLimitWatts: 700, workload: "Qwen3-8B Throughput", deploymentId: "dep-qwen8" },
  { id: "gpu-3090-0", serverId: "srv-lab-old-01", index: 0, name: "RTX 3090", status: "unavailable", utilization: null, memoryUsedGb: null, memoryTotalGb: 24, temperatureC: null, powerWatts: null, powerLimitWatts: 350, workload: null, deploymentId: null },
  { id: "gpu-3090-1", serverId: "srv-lab-old-01", index: 1, name: "RTX 3090", status: "unavailable", utilization: null, memoryUsedGb: null, memoryTotalGb: 24, temperatureC: null, powerWatts: null, powerLimitWatts: 350, workload: null, deploymentId: null },
];

export const gpuProcesses: GPUProcess[] = [
  { id: "proc-1", gpuId: "gpu-4090-0", pid: 34182, user: "vllm", command: "python -m vllm.entrypoints.openai.api_server", memoryGb: 20.4, startedAt: "2026-08-05T08:12:00Z" },
  { id: "proc-2", gpuId: "gpu-4090-1", pid: 34182, user: "vllm", command: "python -m vllm.entrypoints.openai.api_server", memoryGb: 17.8, startedAt: "2026-08-05T08:12:00Z" },
  { id: "proc-3", gpuId: "gpu-a6000-0", pid: 8807, user: "models", command: "text-embeddings-router --model-id BAAI/bge-m3", memoryGb: 11.9, startedAt: "2026-08-07T09:41:00Z" },
  { id: "proc-4", gpuId: "gpu-a6000-2", pid: 19402, user: "research", command: "python evaluate_reasoning.py --batch-size 32", memoryGb: 45.1, startedAt: "2026-08-07T11:08:00Z" },
  { id: "proc-5", gpuId: "gpu-h100-0", pid: 7221, user: "vllm", command: "vllm serve Qwen/Qwen3-8B --max-num-seqs 256", memoryGb: 73.4, startedAt: "2026-08-06T02:17:00Z" },
];

export const models: ModelDefinition[] = [
  { id: "model-qwen3-8b", provider: "Hugging Face", name: "Qwen/Qwen3-8B", displayName: "Qwen3-8B", type: "LLM", parameters: "8B", license: "Apache-2.0", source: "huggingface.co/Qwen/Qwen3-8B", description: "Compact dense language model with strong reasoning and multilingual capabilities.", tags: ["text-generation", "reasoning", "multilingual"], downloads: "4.2M", contextLength: "32K", architecture: "Qwen3ForCausalLM" },
  { id: "model-qwen3-32b", provider: "ModelScope", name: "Qwen/Qwen3-32B", displayName: "Qwen3-32B", type: "LLM", parameters: "32B", license: "Apache-2.0", source: "modelscope.cn/models/Qwen/Qwen3-32B", description: "High-capability dense model for reasoning, coding, and agent workloads.", tags: ["text-generation", "coding", "reasoning"], downloads: "1.8M", contextLength: "32K", architecture: "Qwen3ForCausalLM" },
  { id: "model-deepseek-r1", provider: "Hugging Face", name: "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B", displayName: "DeepSeek-R1-Distill-Qwen-32B", type: "LLM", parameters: "32B", license: "MIT", source: "huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-32B", description: "Distilled reasoning model built on Qwen with strong mathematical performance.", tags: ["reasoning", "math", "distilled"], downloads: "7.6M", contextLength: "32K", architecture: "Qwen2ForCausalLM" },
  { id: "model-bge-m3", provider: "Hugging Face", name: "BAAI/bge-m3", displayName: "BGE-M3", type: "Embedding", parameters: "568M", license: "MIT", source: "huggingface.co/BAAI/bge-m3", description: "Multi-lingual, multi-function, multi-granularity embedding model.", tags: ["embedding", "retrieval", "multilingual"], downloads: "11.3M", contextLength: "8K", architecture: "XLMRobertaModel" },
  { id: "model-llama-8b", provider: "Hugging Face", name: "meta-llama/Llama-3.1-8B-Instruct", displayName: "Llama 3.1 8B Instruct", type: "LLM", parameters: "8B", license: "Llama 3.1", source: "huggingface.co/meta-llama/Llama-3.1-8B-Instruct", description: "Instruction-tuned open model for assistant and general text generation workloads.", tags: ["instruction", "text-generation", "multilingual"], downloads: "18.9M", contextLength: "128K", architecture: "LlamaForCausalLM" },
];

export const modelFiles: ModelFile[] = [
  { id: "file-qwen32-4090", modelId: "model-qwen3-32b", serverId: "srv-lab-4090-01", sizeGb: 61.2, format: "Safetensors", path: "/data/models/Qwen/Qwen3-32B", status: "installed", deployments: 1, quantization: "BF16", revision: "main" },
  { id: "file-qwen8-4090", modelId: "model-qwen3-8b", serverId: "srv-lab-4090-01", sizeGb: 16.4, format: "Safetensors", path: "/data/models/Qwen/Qwen3-8B", status: "installed", deployments: 0, quantization: "BF16", revision: "main" },
  { id: "file-bge-4090", modelId: "model-bge-m3", serverId: "srv-lab-4090-01", sizeGb: 2.3, format: "Safetensors", path: "/data/models/BAAI/bge-m3", status: "installed", deployments: 0, quantization: "FP16", revision: "main" },
  { id: "file-llama-4090", modelId: "model-llama-8b", serverId: "srv-lab-4090-01", sizeGb: 8.7, format: "GGUF", path: "/data/models/meta-llama/llama-3.1-8b-q4_k_m.gguf", status: "installed", deployments: 0, quantization: "Q4_K_M", revision: "main" },
  { id: "file-bge-a6000", modelId: "model-bge-m3", serverId: "srv-lab-a6000-01", sizeGb: 2.3, format: "Safetensors", path: "/mnt/models/BAAI/bge-m3", status: "installed", deployments: 1, quantization: "FP16", revision: "main" },
  { id: "file-deepseek-a6000", modelId: "model-deepseek-r1", serverId: "srv-lab-a6000-01", sizeGb: 63.8, format: "Safetensors", path: "/mnt/models/deepseek-ai/DeepSeek-R1-Distill-Qwen-32B", status: "installed", deployments: 1, quantization: "BF16", revision: "main" },
  { id: "file-qwen8-a6000", modelId: "model-qwen3-8b", serverId: "srv-lab-a6000-01", sizeGb: 9.1, format: "GGUF", path: "/mnt/models/Qwen/Qwen3-8B-Q4_K_M.gguf", status: "installed", deployments: 0, quantization: "Q4_K_M", revision: "main" },
  { id: "file-qwen32-a6000", modelId: "model-qwen3-32b", serverId: "srv-lab-a6000-01", sizeGb: 61.2, format: "Safetensors", path: "/mnt/models/Qwen/Qwen3-32B", status: "verifying", deployments: 0, quantization: "BF16", revision: "v1.0" },
  { id: "file-llama-a6000", modelId: "model-llama-8b", serverId: "srv-lab-a6000-01", sizeGb: 15.8, format: "Safetensors", path: "/mnt/models/meta-llama/Llama-3.1-8B-Instruct", status: "installed", deployments: 0, quantization: "BF16", revision: "main" },
  { id: "file-qwen8-h100", modelId: "model-qwen3-8b", serverId: "srv-cloud-h100-01", sizeGb: 16.4, format: "Safetensors", path: "/models/Qwen/Qwen3-8B", status: "installed", deployments: 1, quantization: "BF16", revision: "main" },
  { id: "file-deepseek-h100", modelId: "model-deepseek-r1", serverId: "srv-cloud-h100-01", sizeGb: 19.6, format: "Safetensors", path: "/models/deepseek-ai/DeepSeek-R1-Distill-Qwen-32B-AWQ", status: "installed", deployments: 0, quantization: "AWQ", revision: "main" },
  { id: "file-llama-old", modelId: "model-llama-8b", serverId: "srv-lab-old-01", sizeGb: 8.7, format: "GGUF", path: "/home/share/models/llama-3.1-8b-q4_k_m.gguf", status: "error", deployments: 0, quantization: "Q4_K_M", revision: "main" },
];

export const deployments = [
  { id: "dep-qwen32", name: "qwen3-32b-prod", modelId: "model-qwen3-32b", serverId: "srv-lab-4090-01", gpuIds: ["gpu-4090-0", "gpu-4090-1"], backend: "vLLM", port: 8001, status: "running", uptime: "2d 06h", endpoint: "http://10.20.0.21:8001/v1", createdAt: "2026-08-05T08:12:00Z", updatedAt: "2026-08-07T14:58:00Z", config: { tensorParallelSize: 2, gpuMemoryUtilization: 0.9, maxModelLength: 32768, dataType: "bfloat16", trustRemoteCode: false, extraArguments: "--enable-prefix-caching" } },
  { id: "dep-bge", name: "bge-m3-embeddings", modelId: "model-bge-m3", serverId: "srv-lab-a6000-01", gpuIds: ["gpu-a6000-0"], backend: "vLLM", port: 8002, status: "running", uptime: "05h 17m", endpoint: "http://10.20.0.32:8002/v1", createdAt: "2026-08-07T09:41:00Z", updatedAt: "2026-08-07T14:58:00Z", config: { tensorParallelSize: 1, gpuMemoryUtilization: 0.55, maxModelLength: 8192, dataType: "float16", trustRemoteCode: true, extraArguments: "--task embed" } },
  { id: "dep-qwen8", name: "qwen3-8b-throughput", modelId: "model-qwen3-8b", serverId: "srv-cloud-h100-01", gpuIds: ["gpu-h100-0"], backend: "vLLM", port: 8000, status: "running", uptime: "1d 12h", endpoint: "http://172.31.8.14:8000/v1", createdAt: "2026-08-06T02:17:00Z", updatedAt: "2026-08-07T14:58:00Z", config: { tensorParallelSize: 1, gpuMemoryUtilization: 0.92, maxModelLength: 32768, dataType: "bfloat16", trustRemoteCode: false, extraArguments: "--max-num-seqs 256" } },
  { id: "dep-llama", name: "llama-8b-sandbox", modelId: "model-llama-8b", serverId: "srv-lab-4090-01", gpuIds: ["gpu-4090-3"], backend: "Ollama", port: 11434, status: "stopped", uptime: "--", endpoint: "http://10.20.0.21:11434/v1", createdAt: "2026-08-01T03:09:00Z", updatedAt: "2026-08-06T10:44:00Z", config: { tensorParallelSize: 1, gpuMemoryUtilization: 0.75, maxModelLength: 8192, dataType: "auto", trustRemoteCode: false, extraArguments: "" } },
  { id: "dep-deepseek", name: "deepseek-r1-eval", modelId: "model-deepseek-r1", serverId: "srv-lab-a6000-01", gpuIds: ["gpu-a6000-2"], backend: "vLLM", port: 8003, status: "failed", uptime: "--", endpoint: "http://10.20.0.32:8003/v1", createdAt: "2026-08-07T11:08:00Z", updatedAt: "2026-08-07T11:12:00Z", errorMessage: "Worker exited: CUDA out of memory while initializing KV cache.", config: { tensorParallelSize: 1, gpuMemoryUtilization: 0.95, maxModelLength: 65536, dataType: "bfloat16", trustRemoteCode: false, extraArguments: "--max-num-seqs 128" } },
];

export const downloadTasks: DownloadTask[] = [
  { id: "dl-1", modelId: "model-qwen3-8b", serverId: "srv-lab-a6000-01", progress: 68, downloadedGb: 11.2, totalGb: 16.4, speedMbps: 82.4, status: "downloading", startedAt: "2026-08-07T14:36:00Z", targetDirectory: "/mnt/models", revision: "main" },
  { id: "dl-2", modelId: "model-deepseek-r1", serverId: "srv-cloud-h100-01", progress: 100, downloadedGb: 19.6, totalGb: 19.6, speedMbps: 0, status: "completed", startedAt: "2026-08-07T08:04:00Z", targetDirectory: "/models", revision: "main" },
  { id: "dl-3", modelId: "model-llama-8b", serverId: "srv-lab-4090-01", progress: 0, downloadedGb: 0, totalGb: 15.8, speedMbps: 0, status: "queued", startedAt: "2026-08-07T14:55:00Z", targetDirectory: "/data/models", revision: "main" },
  { id: "dl-4", modelId: "model-qwen3-32b", serverId: "srv-lab-a6000-01", progress: 43, downloadedGb: 26.3, totalGb: 61.2, speedMbps: 0, status: "failed", startedAt: "2026-08-06T18:22:00Z", targetDirectory: "/mnt/models", revision: "v1.0", errorMessage: "Connection reset after 3 retries." },
];

export const apiEndpoints: ApiEndpoint[] = [
  { id: "api-1", deploymentId: "dep-qwen32", modelId: "model-qwen3-32b", serverId: "srv-lab-4090-01", endpoint: "http://10.20.0.21:8001/v1", backend: "vLLM", status: "healthy", port: 8001, latencyMs: 41, lastChecked: "2026-08-07T14:58:35Z" },
  { id: "api-2", deploymentId: "dep-bge", modelId: "model-bge-m3", serverId: "srv-lab-a6000-01", endpoint: "http://10.20.0.32:8002/v1", backend: "vLLM", status: "healthy", port: 8002, latencyMs: 18, lastChecked: "2026-08-07T14:58:32Z" },
  { id: "api-3", deploymentId: "dep-qwen8", modelId: "model-qwen3-8b", serverId: "srv-cloud-h100-01", endpoint: "http://172.31.8.14:8000/v1", backend: "vLLM", status: "degraded", port: 8000, latencyMs: 126, lastChecked: "2026-08-07T14:58:29Z" },
];

export const activityLogs: ActivityLog[] = [
  { id: "act-1", time: "2026-08-07T14:55:10Z", user: "admin", action: "DOWNLOAD_MODEL", resource: "Llama 3.1 8B Instruct", serverId: "srv-lab-4090-01", status: "success", detail: "Queued download task dl-3." },
  { id: "act-2", time: "2026-08-07T14:41:22Z", user: "admin", action: "DOWNLOAD_MODEL", resource: "Qwen3-8B", serverId: "srv-lab-a6000-01", status: "success", detail: "Download is 68% complete." },
  { id: "act-3", time: "2026-08-07T11:12:04Z", user: "admin", action: "DEPLOY_MODEL", resource: "DeepSeek-R1-Distill-Qwen-32B", serverId: "srv-lab-a6000-01", status: "failed", detail: "Deployment failed during KV cache initialization." },
  { id: "act-4", time: "2026-08-07T09:41:18Z", user: "admin", action: "DEPLOY_MODEL", resource: "BGE-M3", serverId: "srv-lab-a6000-01", status: "success", detail: "Deployment bge-m3-embeddings is healthy." },
  { id: "act-5", time: "2026-08-07T04:22:13Z", user: "system", action: "SERVER_OFFLINE", resource: "lab-old-01", serverId: "srv-lab-old-01", status: "warning", detail: "No heartbeat received for 30 seconds." },
  { id: "act-6", time: "2026-08-06T10:44:00Z", user: "admin", action: "STOP_DEPLOYMENT", resource: "llama-8b-sandbox", serverId: "srv-lab-4090-01", status: "success", detail: "Ollama deployment stopped." },
];

export const systemSettings: SystemSettings = {
  consoleName: "AI Infra Console",
  timezone: "Asia/Shanghai",
  language: "English",
  heartbeatInterval: 10,
  offlineThreshold: 30,
  metricsRetentionDays: 14,
  defaultModelDirectory: "/data/models",
  defaultBackend: "vLLM",
  defaultPort: 8000,
  defaultGpuMemoryUtilization: 0.9,
  requireDeleteConfirmation: true,
  auditLogRetentionDays: 90,
};

export const deploymentLogs = [
  "2026-08-07 14:52:08 INFO  HTTP server listening on 0.0.0.0:8001",
  "2026-08-07 14:52:08 INFO  Using model Qwen/Qwen3-32B",
  "2026-08-07 14:52:09 INFO  Tensor parallel size: 2",
  "2026-08-07 14:52:10 INFO  Loading safetensors checkpoint shards: 8/8",
  "2026-08-07 14:52:28 INFO  Model weights loaded in 18.2 seconds",
  "2026-08-07 14:52:31 INFO  GPU KV cache size: 192,864 tokens",
  "2026-08-07 14:52:32 INFO  Application startup complete",
  "2026-08-07 14:57:42 INFO  10.20.0.8:54218 POST /v1/chat/completions 200 1.84s",
  "2026-08-07 14:58:01 INFO  Running: 3 reqs, Waiting: 0 reqs, KV cache: 42.1%",
];

export function getServer(id: string) {
  return servers.find((server) => server.id === id);
}

export function getGpu(id: string) {
  return gpus.find((gpu) => gpu.id === id);
}

export function getModel(id: string) {
  return models.find((model) => model.id === id);
}

export function getDeployment(id: string) {
  return deployments.find((deployment) => deployment.id === id);
}
