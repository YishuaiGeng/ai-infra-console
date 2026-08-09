import { describe, expect, it } from "vitest";

import {
  apiEndpointTestPayload,
  apiEndpointTestResponseSchema,
  availableDeploymentActions,
  deploymentCreatePayload,
  deploymentDtoSchema,
  deploymentLogPath,
  mapApiEndpointTestResult,
  mapDeployment,
} from "@/lib/api/deployments";

function deploymentDto(status = "running") {
  return {
    id: "deployment-1",
    name: "qwen3-8b-prod",
    model: {
      id: "model-1",
      model_file_id: "file-1",
      source: "huggingface",
      source_id: "Qwen/Qwen3-8B",
      name: "Qwen3-8B",
      display_name: "Qwen3 8B",
      path: "/models/Qwen/Qwen3-8B",
      format: "safetensors",
      quantization: null,
      revision: "main",
      size: 1024,
    },
    server: {
      id: "server-1",
      name: "xiao-pro6000",
      status: "online",
      type: "local",
      host: "10.20.0.60",
      hostname: "xiao-pro6000",
    },
    gpus: [
      {
        id: "gpu-1",
        index: 0,
        uuid: "GPU-test",
        name: "RTX PRO 6000",
        status: "active",
        memory_total: 96 * 1024 ** 3,
        memory_used: 10 * 1024 ** 3,
        utilization: 25,
      },
    ],
    backend: "vllm",
    selection_mode: "automatic",
    desired_state: status === "stopped" ? "stopped" : "running",
    status,
    generation: 1,
    port: 8001,
    endpoint: "http://10.20.0.60:8001/v1",
    config: {
      tensor_parallel_size: 1,
      gpu_memory_utilization: 0.9,
      max_model_length: 32768,
      data_type: "auto",
      trust_remote_code: false,
      extra_arguments: ["--enable-prefix-caching"],
    },
    health_status: "healthy",
    health_latency_ms: 12.5,
    last_health_checked_at: "2026-08-08T00:00:04Z",
    last_reconciled_at: "2026-08-08T00:00:04Z",
    uptime_seconds: 120,
    error_code: null,
    error_message: null,
    current_operation: null,
    started_at: "2026-08-08T00:00:02Z",
    stopped_at: null,
    created_at: "2026-08-08T00:00:00Z",
    updated_at: "2026-08-08T00:00:04Z",
  };
}

describe("deployment DTO mapping", () => {
  it("maps runtime, placement, model, and health without Docker internals", () => {
    const deployment = mapDeployment(deploymentDtoSchema.parse(deploymentDto()));
    expect(deployment).toMatchObject({
      status: "running",
      backend: "vllm",
      healthStatus: "healthy",
      model: { modelFileId: "file-1", sourceId: "Qwen/Qwen3-8B" },
      server: { name: "xiao-pro6000" },
      config: { extraArguments: ["--enable-prefix-caching"] },
    });
    expect(deployment).not.toHaveProperty("containerId");
    expect(deployment).not.toHaveProperty("leaseToken");
  });

  it("keeps lifecycle controls aligned with stable server states", () => {
    const running = mapDeployment(deploymentDtoSchema.parse(deploymentDto("running")));
    const stopped = mapDeployment(deploymentDtoSchema.parse(deploymentDto("stopped")));
    const failed = mapDeployment(deploymentDtoSchema.parse(deploymentDto("failed")));
    const starting = mapDeployment(deploymentDtoSchema.parse(deploymentDto("starting")));
    expect(availableDeploymentActions(running)).toEqual(["stop", "restart", "delete"]);
    expect(availableDeploymentActions(stopped)).toEqual(["start", "delete"]);
    expect(availableDeploymentActions(failed)).toEqual(["retry", "delete"]);
    expect(availableDeploymentActions(starting)).toEqual([]);
  });

  it("serializes only typed vLLM configuration fields", () => {
    expect(
      deploymentCreatePayload({
        name: "qwen3-8b-prod",
        modelFileId: "file-1",
        selectionMode: "manual",
        gpuIds: ["gpu-1"],
        port: 8001,
        tensorParallelSize: 1,
        gpuMemoryUtilization: 0.9,
        maxModelLength: 32768,
        dataType: "bfloat16",
        trustRemoteCode: false,
        extraArguments: ["--max-num-seqs", "256"],
      }),
    ).toEqual({
      name: "qwen3-8b-prod",
      model_file_id: "file-1",
      selection_mode: "manual",
      gpu_ids: ["gpu-1"],
      port: 8001,
      config: {
        tensor_parallel_size: 1,
        gpu_memory_utilization: 0.9,
        max_model_length: 32768,
        data_type: "bfloat16",
        trust_remote_code: false,
        extra_arguments: ["--max-num-seqs", "256"],
      },
    });
  });

  it("encodes bounded log search parameters", () => {
    expect(deploymentLogPath("id/1", "CUDA error", 200)).toBe(
      "/api/deployments/id%2F1/logs?limit=200&search=CUDA+error",
    );
  });

  it("maps real OpenAI-compatible endpoint test responses", () => {
    expect(
      apiEndpointTestPayload({
        prompt: "Hello",
        maxTokens: 16,
        temperature: 0.2,
      }),
    ).toEqual({ prompt: "Hello", max_tokens: 16, temperature: 0.2 });
    expect(
      mapApiEndpointTestResult(
        apiEndpointTestResponseSchema.parse({
          response: "Hello from vLLM",
          latency_ms: 42.5,
          input_tokens: 3,
          output_tokens: 4,
          total_tokens: 7,
          model: "Qwen/Qwen3-8B",
        }),
      ),
    ).toEqual({
      response: "Hello from vLLM",
      latencyMs: 42.5,
      inputTokens: 3,
      outputTokens: 4,
      totalTokens: 7,
      model: "Qwen/Qwen3-8B",
    });
  });
});
