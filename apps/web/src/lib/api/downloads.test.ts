import { describe, expect, it } from "vitest";

import {
  catalogSearchDtoSchema,
  downloadTargetDtoSchema,
  downloadTaskDtoSchema,
  mapCatalogSearch,
  mapDownloadTarget,
  mapDownloadTask,
  pendingDownloadTaskId,
} from "@/lib/api/downloads";

const server = {
  id: "server-1",
  name: "xiao-pro6000",
  status: "online",
  type: "local",
  host: null,
  hostname: "xiao-pro6000",
};

describe("model download DTO mapping", () => {
  it("only marks an actively mutating task as busy", () => {
    expect(pendingDownloadTaskId(false, "cancelled-task", false, undefined)).toBeNull();
    expect(pendingDownloadTaskId(true, "cancel-task", false, undefined)).toBe(
      "cancel-task",
    );
    expect(pendingDownloadTaskId(false, "old-task", true, "retry-task")).toBe(
      "retry-task",
    );
  });

  it("accepts an empty provider error map and normalizes catalog values", () => {
    const result = mapCatalogSearch(
      catalogSearchDtoSchema.parse({
        items: [
          {
            provider: "huggingface",
            source_id: "Qwen/Qwen3-8B",
            display_name: "Qwen3 8B",
            model_type: null,
            description: null,
            tags: ["text-generation"],
            downloads: 12_000,
            likes: 100,
            license: null,
            gated: false,
            private: false,
            revision: null,
            size: null,
            architecture: null,
            last_modified: null,
          },
        ],
        provider_errors: {},
      }),
    );

    expect(result.providerErrors).toEqual({});
    expect(result.items[0]).toMatchObject({
      id: "huggingface:Qwen/Qwen3-8B",
      revision: "main",
      sourceUrl: "https://huggingface.co/Qwen/Qwen3-8B",
    });
  });

  it("maps only Agent-approved download directories", () => {
    const target = mapDownloadTarget(
      downloadTargetDtoSchema.parse({
        server,
        directories: [
          {
            id: "directory-1",
            server_id: "server-1",
            path: "/data/models",
            is_default: true,
            is_allowed: true,
            is_available: true,
            error_code: null,
            last_scanned_at: "2026-08-08T00:00:00Z",
            model_count: 1,
          },
        ],
      }),
    );

    expect(target.server.host).toBe("xiao-pro6000");
    expect(target.directories[0]).toMatchObject({
      id: "directory-1",
      isDefault: true,
      isAvailable: true,
    });
  });

  it("maps lease-backed task progress without exposing lease data", () => {
    const task = mapDownloadTask(
      downloadTaskDtoSchema.parse({
        id: "task-1",
        model_id: "model-1",
        server,
        directory_id: "directory-1",
        target_path: "/data/models/huggingface/Qwen/Qwen3-8B",
        source: "huggingface",
        source_id: "Qwen/Qwen3-8B",
        revision: "main",
        status: "downloading",
        downloaded_size: 50,
        total_size: 100,
        speed_bytes_per_second: 10,
        progress: 50,
        attempt_count: 1,
        error_code: null,
        error_message: null,
        started_at: "2026-08-08T00:00:01Z",
        completed_at: null,
        last_progress_at: "2026-08-08T00:00:02Z",
        created_at: "2026-08-08T00:00:00Z",
        updated_at: "2026-08-08T00:00:02Z",
      }),
    );

    expect(task).toMatchObject({
      status: "downloading",
      downloadedSize: 50,
      totalSize: 100,
      progress: 50,
      attemptCount: 1,
    });
    expect(task).not.toHaveProperty("leaseToken");
  });
});
