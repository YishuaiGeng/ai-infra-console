import { z } from "zod";

import type { ActivityLog } from "@/types";

export const activityLogDtoSchema = z.object({
  id: z.string(),
  time: z.string(),
  user: z.string(),
  action: z.string(),
  resource: z.string(),
  server_id: z.string().nullable(),
  status: z.enum(["success", "failed", "warning"]),
  detail: z.string(),
});

export const activityQueryKeys = {
  all: ["activity"] as const,
  list: (search: string, limit: number) => ["activity", "list", search, limit] as const,
};

export function activityPath(search: string, limit: number) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (search) params.set("search", search);
  return `/api/activity?${params.toString()}`;
}

export function mapActivityLog(dto: z.infer<typeof activityLogDtoSchema>): ActivityLog {
  return {
    id: dto.id,
    time: dto.time,
    user: dto.user,
    action: dto.action,
    resource: dto.resource,
    serverId: dto.server_id,
    status: dto.status,
    detail: dto.detail,
  };
}
