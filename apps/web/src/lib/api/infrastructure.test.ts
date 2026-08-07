import { describe, expect, it } from "vitest";

import {
  bytesToGiB,
  gpuDtoSchema,
  infrastructureEventQueryKeys,
  infrastructureEventSchema,
  mapGpu,
  mapProcess,
  mapServer,
  serverDtoSchema,
} from "@/lib/api/infrastructure";

const gib = 1024 ** 3;

function serverDto() {
  return {
    id: "server-1",
    name: "lab-server-01",
    status: "online",
    type: "local",
    provider: null,
    host: null,
    hostname: "lab-node",
    description: null,
    tags: ["phase-3"],
    os: "Linux",
    kernel: "6.8.0",
    cpu_model: "Test CPU",
    cpu_cores: 16,
    memory_total: 64 * gib,
    disk_total: 1024 * gib,
    agent_version: "0.1.0",
    last_seen: "2026-08-08T00:00:00Z",
    created_at: "2026-08-07T00:00:00Z",
    updated_at: "2026-08-08T00:00:00Z",
    metric: {
      collected_at: "2026-08-08T00:00:00Z",
      uptime_seconds: 93_600,
      cpu_utilization: 25,
      memory_used: 32 * gib,
      memory_total: 64 * gib,
      disk_used: 400 * gib,
      disk_total: 1024 * gib,
      network_bytes_sent: 1000,
      network_bytes_received: 2000,
      architecture: "x86_64",
      runtimes: { docker: { available: true, version: "27.0" } },
    },
    gpu_count: 1,
    available_gpu_count: 1,
    gpu_memory_total: 24 * gib,
    gpu_models: ["NVIDIA Test GPU"],
    model_count: 2,
  };
}

function gpuDto() {
  return {
    id: "gpu-1",
    server: {
      id: "server-1",
      name: "lab-server-01",
      type: "local",
      status: "online",
      host: null,
      hostname: "lab-node",
    },
    index: 0,
    uuid: "GPU-test",
    vendor: "NVIDIA",
    name: "NVIDIA Test GPU",
    status: "active" as const,
    utilization: 55,
    memory_used: 12 * gib,
    memory_total: 24 * gib,
    temperature: 62,
    power_usage: 250,
    power_limit: 450,
    fan_speed: 40,
    driver_version: "580.00",
    cuda_version: "13.0",
    metric_collected_at: "2026-08-08T00:00:00Z",
    process_count: 2,
  };
}

describe("infrastructure DTO mapping", () => {
  it("maps server bytes, nullable fields, and uptime into display values", () => {
    const mapped = mapServer(serverDtoSchema.parse(serverDto()));

    expect(mapped.provider).toBe("Self-hosted");
    expect(mapped.host).toBe("lab-node");
    expect(mapped.ramUsedGb).toBe(32);
    expect(mapped.diskTotalGb).toBe(1024);
    expect(mapped.uptime).toBe("1d 2h");
    expect(mapped.gpuModel).toBe("NVIDIA Test GPU");
    expect(mapped.modelCount).toBe(2);
  });

  it("maps GPU server context and process counts without mock joins", () => {
    const mapped = mapGpu(gpuDtoSchema.parse(gpuDto()));

    expect(mapped.serverName).toBe("lab-server-01");
    expect(mapped.serverHost).toBe("lab-node");
    expect(mapped.memoryUsedGb).toBe(12);
    expect(mapped.workload).toBe("2 active processes");
  });

  it("maps CPU-only/null values and process records deterministically", () => {
    expect(bytesToGiB(null)).toBeNull();
    const process = mapProcess({
      id: "process-1",
      gpu_id: "gpu-1",
      gpu_index: 0,
      gpu_name: "NVIDIA Test GPU",
      pid: 1200,
      username: null,
      command: null,
      memory_used: null,
      collected_at: "2026-08-08T00:00:00Z",
    });
    expect(process).toMatchObject({ user: "Unknown", command: "Unknown", memoryGb: 0 });
  });

  it("rejects malformed infrastructure events", () => {
    expect(
      infrastructureEventSchema.safeParse({ kind: "shell", server_id: "server-1" }).success,
    ).toBe(false);
  });

  it("targets summary, collections, and the changed server after an event", () => {
    expect(infrastructureEventQueryKeys("server-1")).toEqual([
      ["infrastructure", "summary"],
      ["infrastructure", "servers"],
      ["infrastructure", "gpus"],
      ["infrastructure", "servers", "server-1"],
    ]);
    expect(
      infrastructureEventQueryKeys("server-1", "model.inventory.updated"),
    ).toContainEqual(["models", "summary"]);
  });
});
