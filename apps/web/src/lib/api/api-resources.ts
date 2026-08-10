import { z } from "zod";

const nullableString = z.string().nullable();
const nullableNumber = z.number().nullable();

export const providerCapabilitiesSchema = z.object({
  credential_validation: z.boolean(),
  model_discovery: z.boolean(),
  balance_sync: z.boolean(),
  usage_sync: z.boolean(),
  usage_by_model: z.boolean(),
  usage_by_credential: z.boolean(),
  manual_usage_import: z.boolean(),
});

export const apiProviderSchema = z.object({
  id: z.string(),
  slug: z.string(),
  display_name: z.string(),
  provider_type: z.string(),
  default_base_url: nullableString,
  capabilities: providerCapabilitiesSchema,
  is_enabled: z.boolean(),
});

export const apiAccountSchema = z.object({
  id: z.string(),
  provider: apiProviderSchema,
  name: z.string(),
  purpose: nullableString,
  owner: nullableString,
  base_url: z.string(),
  status: z.string(),
  billing_currency: nullableString,
  monthly_budget: nullableNumber,
  tags: z.array(z.string()),
  notes: nullableString,
  last_verified_at: nullableString,
  last_synced_at: nullableString,
  credential_count: z.number().int(),
  model_count: z.number().int(),
  latest_balance: nullableNumber,
  latest_usage_cost: nullableNumber,
  created_at: z.string(),
  updated_at: z.string(),
});

export const apiCredentialSchema = z.object({
  id: z.string(),
  account_id: z.string(),
  name: z.string(),
  credential_type: z.string(),
  masked_value: z.string(),
  status: z.string(),
  expires_at: nullableString,
  last_validated_at: nullableString,
  last_error_code: nullableString,
  last_error_message: nullableString,
  created_at: z.string(),
  updated_at: z.string(),
});

export const apiAccountModelSchema = z.object({
  id: z.string(),
  account_id: z.string(),
  provider_model_id: z.string(),
  display_name: nullableString,
  model_family: nullableString,
  capabilities: z.array(z.string()),
  context_window: nullableNumber,
  is_available: z.boolean(),
  source: z.string(),
  discovered_at: z.string(),
  last_seen_at: z.string(),
});

export const apiUsageSchema = z.object({
  id: z.string(),
  account_id: z.string(),
  credential_id: nullableString,
  provider_model_id: nullableString,
  period_start: z.string(),
  period_end: z.string(),
  granularity: z.string(),
  request_count: nullableNumber,
  input_tokens: nullableNumber,
  output_tokens: nullableNumber,
  cached_tokens: nullableNumber,
  total_tokens: nullableNumber,
  cost_amount: nullableNumber,
  currency: nullableString,
  source: z.string(),
  collected_at: z.string(),
});

export const apiBalanceSchema = z.object({
  id: z.string(),
  account_id: z.string(),
  balance_amount: nullableNumber,
  credit_limit: nullableNumber,
  remaining_credit: nullableNumber,
  currency: nullableString,
  expires_at: nullableString,
  source: z.string(),
  collected_at: z.string(),
});

export const apiSyncRunSchema = z.object({
  id: z.string(),
  account_id: z.string(),
  sync_type: z.string(),
  status: z.string(),
  requested_by_user_id: nullableString,
  started_at: nullableString,
  completed_at: nullableString,
  records_written: z.number().int(),
  error_code: nullableString,
  error_message: nullableString,
  details: z.record(z.string(), z.unknown()),
  created_at: z.string(),
  updated_at: z.string(),
});

export const apiUsageSummarySchema = z.object({
  account_count: z.number().int(),
  request_count: z.number().int(),
  input_tokens: z.number().int(),
  output_tokens: z.number().int(),
  total_tokens: z.number().int(),
  costs_by_currency: z.record(z.string(), z.number()),
});

export type ApiProvider = z.infer<typeof apiProviderSchema>;
export type ApiAccount = z.infer<typeof apiAccountSchema>;
export type ApiCredential = z.infer<typeof apiCredentialSchema>;
export type ApiAccountModel = z.infer<typeof apiAccountModelSchema>;
export type ApiUsage = z.infer<typeof apiUsageSchema>;
export type ApiBalance = z.infer<typeof apiBalanceSchema>;
export type ApiSyncRun = z.infer<typeof apiSyncRunSchema>;
export type ApiUsageSummary = z.infer<typeof apiUsageSummarySchema>;

export const apiResourceQueryKeys = {
  all: ["api-resources"] as const,
  providers: ["api-resources", "providers"] as const,
  accounts: ["api-resources", "accounts"] as const,
  summary: ["api-resources", "summary"] as const,
  credentials: (accountId: string) => ["api-resources", accountId, "credentials"] as const,
  models: (accountId: string) => ["api-resources", accountId, "models"] as const,
  usage: (accountId: string) => ["api-resources", accountId, "usage"] as const,
  balance: (accountId: string) => ["api-resources", accountId, "balance"] as const,
  syncRuns: (accountId: string) => ["api-resources", accountId, "sync-runs"] as const,
};
