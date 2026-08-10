import { describe, expect, it } from "vitest";

import {
  apiAccountSchema,
  apiCredentialSchema,
  apiProviderSchema,
  apiUsageSummarySchema,
} from "@/lib/api/api-resources";

const capabilities = {
  credential_validation: true,
  model_discovery: true,
  balance_sync: false,
  usage_sync: false,
  usage_by_model: false,
  usage_by_credential: false,
  manual_usage_import: true,
};

describe("API resource DTO schemas", () => {
  it("parses capability-aware providers and account summaries", () => {
    const provider = apiProviderSchema.parse({
      id: "provider-1",
      slug: "openai",
      display_name: "OpenAI",
      provider_type: "built_in",
      default_base_url: "https://api.openai.com/v1",
      adapter_kind: "openai-compatible",
      credential_header: "authorization",
      static_headers: {},
      capabilities,
      is_enabled: true,
    });
    const account = apiAccountSchema.parse({
      id: "account-1",
      provider,
      name: "Research",
      purpose: null,
      owner: "Platform",
      base_url: "https://api.openai.com/v1",
      status: "active",
      billing_currency: "USD",
      monthly_budget: 100,
      tags: ["research"],
      notes: null,
      last_verified_at: null,
      last_synced_at: null,
      credential_count: 1,
      model_count: 20,
      latest_balance: 42,
      latest_usage_cost: 5,
      created_at: "2026-08-10T00:00:00Z",
      updated_at: "2026-08-10T00:00:00Z",
    });

    expect(account.provider.capabilities.usage_sync).toBe(false);
    expect(account.model_count).toBe(20);
  });

  it("keeps credential responses masked and ignores storage-only fields", () => {
    const credential = apiCredentialSchema.parse({
      id: "credential-1",
      account_id: "account-1",
      name: "Primary",
      credential_type: "api_key",
      masked_value: "sk-a****1234",
      status: "active",
      expires_at: null,
      last_validated_at: null,
      last_error_code: null,
      last_error_message: null,
      created_at: "2026-08-10T00:00:00Z",
      updated_at: "2026-08-10T00:00:00Z",
      encrypted_value: "must-not-reach-the-client",
      fingerprint: "must-not-reach-the-client",
    });

    expect(credential).not.toHaveProperty("encrypted_value");
    expect(credential).not.toHaveProperty("fingerprint");
  });

  it("keeps costs separated by currency", () => {
    const summary = apiUsageSummarySchema.parse({
      account_count: 2,
      request_count: 10,
      input_tokens: 100,
      output_tokens: 20,
      total_tokens: 120,
      costs_by_currency: { USD: 1.25, CNY: 2.5 },
    });

    expect(summary.costs_by_currency).toEqual({ USD: 1.25, CNY: 2.5 });
  });
});
