"use client";

import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";

import {
  apiRequest,
  gpuDtoSchema,
  infrastructureEventQueryKeys,
  infrastructureEventSchema,
  infrastructureQueryKeys,
  infrastructureSummarySchema,
  mapGpu,
  mapServer,
  mapServerDetail,
  registrationResponseSchema,
  serverDetailDtoSchema,
  serverDtoSchema,
} from "@/lib/api/infrastructure";

const sessionSchema = z.object({
  id: z.string(),
  username: z.string(),
  role: z.enum(["admin", "viewer"]),
  is_active: z.boolean(),
  created_at: z.string(),
  last_login_at: z.string().nullable(),
});

function refreshInterval() {
  return typeof document !== "undefined" && document.hidden ? false : 30_000;
}

export function useInfrastructureSummary() {
  return useQuery({
    queryKey: infrastructureQueryKeys.summary,
    queryFn: () =>
      apiRequest("/api/infrastructure/summary", infrastructureSummarySchema),
    refetchInterval: refreshInterval,
  });
}

export function useSession() {
  return useQuery({
    queryKey: ["session"],
    queryFn: () => apiRequest("/api/session", sessionSchema),
    staleTime: 60_000,
  });
}

export function useServers() {
  return useQuery({
    queryKey: infrastructureQueryKeys.servers,
    queryFn: async () =>
      (await apiRequest("/api/servers", z.array(serverDtoSchema))).map(mapServer),
    refetchInterval: refreshInterval,
  });
}

export function useServer(id: string) {
  return useQuery({
    queryKey: infrastructureQueryKeys.server(id),
    queryFn: async () => {
      const dto = await apiRequest(
        `/api/servers/${encodeURIComponent(id)}`,
        serverDetailDtoSchema,
      );
      return mapServerDetail(dto);
    },
    refetchInterval: refreshInterval,
  });
}

export function useGpus() {
  return useQuery({
    queryKey: infrastructureQueryKeys.gpus,
    queryFn: async () =>
      (await apiRequest("/api/gpus", z.array(gpuDtoSchema))).map(mapGpu),
    refetchInterval: refreshInterval,
  });
}

export interface RegistrationInput {
  name: string;
  type: "local" | "cloud";
  provider?: string;
  description?: string;
  tags: string[];
}

export function useCreateRegistration() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: RegistrationInput) =>
      apiRequest("/api/servers", registrationResponseSchema, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: infrastructureQueryKeys.all }),
  });
}

export function useRotateAgentToken(serverId: string) {
  return useMutation({
    mutationFn: () =>
      apiRequest(
        `/api/servers/${encodeURIComponent(serverId)}/agent-token`,
        registrationResponseSchema,
        { method: "POST" },
      ),
  });
}

export function useRevokeAgentToken(serverId: string) {
  return useMutation({
    mutationFn: async () => {
      const response = await fetch(
        `/api/servers/${encodeURIComponent(serverId)}/agent-token/revoke`,
        { method: "POST" },
      );
      if (!response.ok) throw new Error("The Agent token could not be revoked.");
    },
  });
}

export function useInfrastructureEvents(enabled = true) {
  const queryClient = useQueryClient();
  useEffect(() => {
    if (!enabled) return;
    const source = new EventSource("/api/infrastructure/events");
    const update = (message: MessageEvent<string>) => {
      let value: unknown;
      try {
        value = JSON.parse(message.data);
      } catch {
        return;
      }
      const parsed = infrastructureEventSchema.safeParse(value);
      if (!parsed.success) return;
      for (const queryKey of infrastructureEventQueryKeys(
        parsed.data.server_id,
        parsed.data.kind,
      )) {
        void queryClient.invalidateQueries({ queryKey });
      }
    };
    source.addEventListener("infrastructure", update as EventListener);
    return () => source.close();
  }, [enabled, queryClient]);
}
