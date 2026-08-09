import { describe, expect, it } from "vitest";

import { activityLogDtoSchema, activityPath, mapActivityLog } from "@/lib/api/activity";

describe("activity API mapping", () => {
  it("encodes list parameters and maps audit log rows", () => {
    expect(activityPath("deployment created", 50)).toBe(
      "/api/activity?limit=50&search=deployment+created",
    );
    expect(
      mapActivityLog(
        activityLogDtoSchema.parse({
          id: "audit-1",
          time: "2026-08-10T00:00:00Z",
          user: "admin",
          action: "deployment.created",
          resource: "deployment:dep-1",
          server_id: "server-1",
          status: "success",
          detail: "{\"operation_id\":\"op-1\"}",
        }),
      ),
    ).toEqual({
      id: "audit-1",
      time: "2026-08-10T00:00:00Z",
      user: "admin",
      action: "deployment.created",
      resource: "deployment:dep-1",
      serverId: "server-1",
      status: "success",
      detail: "{\"operation_id\":\"op-1\"}",
    });
  });
});
