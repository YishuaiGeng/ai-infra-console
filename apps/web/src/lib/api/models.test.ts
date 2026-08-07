import { describe, expect, it } from "vitest";

import {
  mapModelDetail,
  mapModelDirectory,
  mapModelInstallation,
  modelDetailDtoSchema,
  modelDirectoryDtoSchema,
  modelInstallationDtoSchema,
} from "@/lib/api/models";

function installationDto() {
  return {
    id: "location-1",
    model_id: "model-1",
    source: "huggingface",
    source_id: "Qwen/Qwen3-8B",
    name: "Qwen/Qwen3-8B",
    display_name: null,
    description: null,
    architecture: "Qwen3ForCausalLM",
    model_type: "qwen3",
    metadata: { dtype: "bfloat16" },
    server: {
      id: "server-1",
      name: "xiao-cpu",
      status: "online",
      type: "local",
      host: null,
      hostname: "xiao-cpu",
    },
    directory_id: "directory-1",
    path: "/data/models/Qwen3-8B",
    size: 8_000,
    file_count: 2,
    format: "safetensors",
    quantization: null,
    revision: "main",
    status: "discovered",
    last_seen_at: "2026-08-08T00:00:00Z",
    created_at: "2026-08-08T00:00:00Z",
    updated_at: "2026-08-08T00:00:00Z",
  };
}

describe("model inventory DTO mapping", () => {
  it("maps nullable installation fields and embedded server identity", () => {
    const mapped = mapModelInstallation(
      modelInstallationDtoSchema.parse(installationDto()),
    );

    expect(mapped.displayName).toBe("Qwen/Qwen3-8B");
    expect(mapped.server.host).toBe("xiao-cpu");
    expect(mapped.quantization).toBe("Not reported");
    expect(mapped.sizeBytes).toBe(8_000);
  });

  it("maps directory scan state", () => {
    const mapped = mapModelDirectory(
      modelDirectoryDtoSchema.parse({
        id: "directory-1",
        server_id: "server-1",
        path: "/data/models",
        is_default: true,
        is_allowed: true,
        is_available: false,
        error_code: "unavailable",
        last_scanned_at: null,
        model_count: 2,
      }),
    );

    expect(mapped).toMatchObject({
      isDefault: true,
      isAvailable: false,
      errorCode: "unavailable",
      modelCount: 2,
    });
  });

  it("maps logical model details with multiple physical locations", () => {
    const second = {
      ...installationDto(),
      id: "location-2",
      server: { ...installationDto().server, id: "server-2", name: "xiao-pro6000" },
    };
    const mapped = mapModelDetail(
      modelDetailDtoSchema.parse({
        id: "model-1",
        source: "huggingface",
        source_id: "Qwen/Qwen3-8B",
        name: "Qwen/Qwen3-8B",
        display_name: "Qwen3 8B",
        description: null,
        architecture: "Qwen3ForCausalLM",
        model_type: "qwen3",
        metadata: {},
        locations: [installationDto(), second],
      }),
    );

    expect(mapped.locations.map((item) => item.server.name)).toEqual([
      "xiao-cpu",
      "xiao-pro6000",
    ]);
  });
});
