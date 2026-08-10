"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";

import {
  apiAccountModelSchema,
  apiAccountSchema,
  apiBalanceSchema,
  apiCredentialSchema,
  apiProviderSchema,
  apiResourceQueryKeys,
  apiSyncRunSchema,
  apiUsageSchema,
  apiUsageSummarySchema,
} from "@/lib/api/api-resources";
import { apiRequest } from "@/lib/api/infrastructure";

export function useApiProviders() {
  return useQuery({
    queryKey: apiResourceQueryKeys.providers,
    queryFn: () => apiRequest("/api/api-resources/providers", z.array(apiProviderSchema)),
  });
}

export function useApiAccounts() {
  return useQuery({
    queryKey: apiResourceQueryKeys.accounts,
    queryFn: () => apiRequest("/api/api-resources/accounts", z.array(apiAccountSchema)),
  });
}

export function useApiUsageSummary() {
  return useQuery({
    queryKey: apiResourceQueryKeys.summary,
    queryFn: () => apiRequest("/api/api-resources/usage/summary", apiUsageSummarySchema),
  });
}

export function useApiAccountDetails(accountId: string | null) {
  const enabled = Boolean(accountId);
  return {
    credentials: useQuery({
      queryKey: apiResourceQueryKeys.credentials(accountId ?? "none"),
      queryFn: () => apiRequest(`/api/api-resources/accounts/${accountId}/credentials`, z.array(apiCredentialSchema)),
      enabled,
    }),
    models: useQuery({
      queryKey: apiResourceQueryKeys.models(accountId ?? "none"),
      queryFn: () => apiRequest(`/api/api-resources/accounts/${accountId}/models`, z.array(apiAccountModelSchema)),
      enabled,
    }),
    usage: useQuery({
      queryKey: apiResourceQueryKeys.usage(accountId ?? "none"),
      queryFn: () => apiRequest(`/api/api-resources/accounts/${accountId}/usage`, z.array(apiUsageSchema)),
      enabled,
    }),
    balance: useQuery({
      queryKey: apiResourceQueryKeys.balance(accountId ?? "none"),
      queryFn: () => apiRequest(`/api/api-resources/accounts/${accountId}/balance`, z.array(apiBalanceSchema)),
      enabled,
    }),
    syncRuns: useQuery({
      queryKey: apiResourceQueryKeys.syncRuns(accountId ?? "none"),
      queryFn: () => apiRequest(`/api/api-resources/accounts/${accountId}/sync-runs`, z.array(apiSyncRunSchema)),
      enabled,
    }),
  };
}

export function useApiResourceMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ path, method = "POST", payload, schema = apiAccountSchema }: {
      path: string;
      method?: "POST" | "PATCH" | "DELETE";
      payload?: unknown;
      schema?: z.ZodType;
    }) => apiRequest(`/api/api-resources/${path}`, schema, {
      method,
      body: payload === undefined ? undefined : JSON.stringify(payload),
    }),
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: apiResourceQueryKeys.all }),
  });
}
