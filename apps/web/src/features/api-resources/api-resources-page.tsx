"use client";

import { FormEvent, useMemo, useState } from "react";
import {
  Archive,
  Boxes,
  CircleDollarSign,
  CloudCog,
  KeyRound,
  Plus,
  RefreshCw,
  ServerCog,
  Settings2,
} from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import type { ApiAccount, ApiProvider } from "@/lib/api/api-resources";
import {
  apiAccountSchema,
  apiBalanceSchema,
  apiCredentialSchema,
  apiProviderSchema,
  apiSyncRunSchema,
  apiUsageSchema,
} from "@/lib/api/api-resources";
import {
  useApiAccountDetails,
  useApiAccounts,
  useApiProviders,
  useApiResourceMutation,
  useApiUsageSummary,
} from "@/hooks/use-api-resources";
import { useSession } from "@/hooks/use-infrastructure";
import { formatDateTime } from "@/lib/format";
import { PageContainer } from "@/components/layout/page-container";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { TableLoadingSkeleton } from "@/components/shared/loading-skeleton";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";

function amount(value: number | null, currency?: string | null) {
  if (value === null) return "—";
  return new Intl.NumberFormat("en-US", {
    style: currency ? "currency" : "decimal",
    currency: currency ?? undefined,
    maximumFractionDigits: 4,
  }).format(value);
}

function compact(value: number) {
  return new Intl.NumberFormat("en-US", { notation: "compact" }).format(value);
}

function SummaryCard({
  label,
  value,
  detail,
  icon: Icon,
}: {
  label: string;
  value: string;
  detail: string;
  icon: typeof CloudCog;
}) {
  return (
    <Card>
      <CardContent className="flex items-start justify-between p-4">
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="mt-1 text-2xl font-semibold">{value}</p>
          <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
        </div>
        <span className="rounded-md bg-muted p-2 text-muted-foreground"><Icon className="size-4" /></span>
      </CardContent>
    </Card>
  );
}

export function ApiResourcesPage() {
  const providers = useApiProviders();
  const accounts = useApiAccounts();
  const summary = useApiUsageSummary();
  const session = useSession();
  const mutation = useApiResourceMutation();
  const [createOpen, setCreateOpen] = useState(false);
  const [providerOpen, setProviderOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<ApiProvider | null>(null);
  const [selected, setSelected] = useState<ApiAccount | null>(null);
  const isAdmin = session.data?.role === "admin";
  const costs = useMemo(
    () => Object.entries(summary.data?.costs_by_currency ?? {}).map(([currency, value]) => amount(value, currency)).join(" · ") || "No cost data",
    [summary.data],
  );

  async function createAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const provider = providers.data?.find((item) => item.slug === data.get("provider_slug"));
    try {
      await mutation.mutateAsync({
        path: "accounts",
        payload: {
          provider_slug: data.get("provider_slug"),
          name: data.get("name"),
          purpose: data.get("purpose") || null,
          owner: data.get("owner") || null,
          base_url: data.get("base_url") || provider?.default_base_url,
          billing_currency: data.get("billing_currency") || null,
          monthly_budget: data.get("monthly_budget") ? Number(data.get("monthly_budget")) : null,
          tags: String(data.get("tags") ?? "").split(",").map((item) => item.trim()).filter(Boolean),
          notes: data.get("notes") || null,
          credential_name: data.get("credential_value") ? data.get("credential_name") || "Primary" : null,
          credential_value: data.get("credential_value") || null,
        },
      });
      setCreateOpen(false);
      toast.success("API account created");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to create API account");
    }
  }

  async function saveProvider(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    try {
      const staticHeaders = JSON.parse(String(data.get("static_headers") || "{}")) as unknown;
      if (!staticHeaders || Array.isArray(staticHeaders) || typeof staticHeaders !== "object") {
        throw new Error("Static headers must be a JSON object");
      }
      const capabilities = {
        credential_validation: data.has("credential_validation"),
        model_discovery: data.has("model_discovery"),
        balance_sync: data.has("balance_sync"),
        usage_sync: data.has("usage_sync"),
        usage_by_model: data.has("usage_by_model"),
        usage_by_credential: data.has("usage_by_credential"),
        manual_usage_import: data.has("manual_usage_import"),
      };
      const shared = {
        display_name: data.get("display_name"),
        default_base_url: data.get("default_base_url") || null,
        credential_header: data.get("credential_header"),
        static_headers: staticHeaders,
        capabilities,
        is_enabled: data.has("is_enabled"),
      };
      await mutation.mutateAsync({
        path: editingProvider ? `providers/${editingProvider.slug}` : "providers",
        method: editingProvider ? "PATCH" : "POST",
        payload: editingProvider ? shared : {
          ...shared,
          slug: data.get("slug"),
          adapter_kind: data.get("adapter_kind"),
        },
        schema: apiProviderSchema,
      });
      setProviderOpen(false);
      setEditingProvider(null);
      toast.success(editingProvider ? "Provider updated" : "Provider created");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to save provider");
    }
  }

  if (accounts.isLoading || providers.isLoading) {
    return <PageContainer><PageHeader title="API Resources" description="External API inventory, credentials, models, balance and usage." /><TableLoadingSkeleton /></PageContainer>;
  }
  if (accounts.isError || providers.isError) {
    return <PageContainer><ErrorState title="API resources unavailable" message="The API resource inventory could not be loaded." onRetry={() => void Promise.all([accounts.refetch(), providers.refetch()])} /></PageContainer>;
  }

  return (
    <PageContainer>
      <PageHeader
        title="API Resources"
        description="Inventory and observe model inference APIs and external provider accounts. Business traffic is not proxied through this console."
        actions={isAdmin ? <Button onClick={() => setCreateOpen(true)}><Plus /> Add external account</Button> : undefined}
      />
      <div className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <SummaryCard label="External accounts" value={String(summary.data?.account_count ?? accounts.data?.length ?? 0)} detail={`${providers.data?.length ?? 0} provider adapters`} icon={CloudCog} />
        <SummaryCard label="Requests recorded" value={compact(summary.data?.request_count ?? 0)} detail="Provider or manual snapshots" icon={ServerCog} />
        <SummaryCard label="Tokens recorded" value={compact(summary.data?.total_tokens ?? 0)} detail={`${compact(summary.data?.input_tokens ?? 0)} input · ${compact(summary.data?.output_tokens ?? 0)} output`} icon={Boxes} />
        <SummaryCard label="Tracked cost" value={costs} detail="Currencies remain separated" icon={CircleDollarSign} />
      </div>

      <div className="mb-5 rounded-lg border bg-card p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold">Provider adapters</h2>
            <p className="text-xs text-muted-foreground">Official OpenAI, Codex, Anthropic, Claude Code, Alibaba Bailian, and custom compatible services.</p>
          </div>
          {isAdmin && <Button variant="outline" size="sm" onClick={() => { setEditingProvider(null); setProviderOpen(true); }}><Settings2 /> Add provider</Button>}
        </div>
        <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {providers.data?.map((provider) => (
            <button
              key={provider.slug}
              type="button"
              disabled={!isAdmin || provider.provider_type !== "custom"}
              onClick={() => { setEditingProvider(provider); setProviderOpen(true); }}
              className="rounded-md border p-3 text-left disabled:cursor-default"
            >
              <div className="flex items-center justify-between gap-2"><p className="font-medium">{provider.display_name}</p><Badge variant={provider.is_enabled ? "secondary" : "outline"}>{provider.is_enabled ? "Enabled" : "Disabled"}</Badge></div>
              <p className="mt-1 font-mono text-xs text-muted-foreground">{provider.slug} · {provider.adapter_kind}</p>
              <p className="mt-2 truncate text-xs text-muted-foreground">{provider.default_base_url ?? "Account-specific base URL"}</p>
            </button>
          ))}
        </div>
      </div>

      <div className="mb-3 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold">External API accounts</h2>
          <p className="text-xs text-muted-foreground">Credentials are encrypted and never displayed again after saving.</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => void accounts.refetch()}><RefreshCw /> Refresh</Button>
      </div>

      {accounts.data?.length === 0 ? (
        <EmptyState icon={CloudCog} title="No external API accounts" message="Add OpenAI or any OpenAI-compatible platform to start an API asset inventory." />
      ) : (
        <div className="grid gap-3 xl:grid-cols-2">
          {accounts.data?.map((account) => (
            <button key={account.id} type="button" onClick={() => setSelected(account)} className="rounded-lg border bg-card p-4 text-left transition-colors hover:bg-muted/30">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2"><h3 className="truncate font-semibold">{account.name}</h3><StatusBadge status={account.status} /></div>
                  <p className="mt-1 truncate font-mono text-xs text-muted-foreground">{account.base_url}</p>
                </div>
                <Badge variant="outline">{account.provider.display_name}</Badge>
              </div>
              <div className="mt-4 grid grid-cols-4 gap-3 text-xs">
                <div><p className="text-muted-foreground">Credentials</p><p className="mt-1 font-semibold">{account.credential_count}</p></div>
                <div><p className="text-muted-foreground">Models</p><p className="mt-1 font-semibold">{account.model_count}</p></div>
                <div><p className="text-muted-foreground">Balance</p><p className="mt-1 font-semibold">{amount(account.latest_balance, account.billing_currency)}</p></div>
                <div><p className="text-muted-foreground">Recorded cost</p><p className="mt-1 font-semibold">{amount(account.latest_usage_cost, account.billing_currency)}</p></div>
              </div>
              <div className="mt-3 flex flex-wrap gap-1">{account.tags.map((tag) => <Badge key={tag} variant="secondary">{tag}</Badge>)}</div>
            </button>
          ))}
        </div>
      )}

      <CreateAccountDialog open={createOpen} onOpenChange={setCreateOpen} providers={providers.data ?? []} pending={mutation.isPending} onSubmit={createAccount} />
      <ProviderDialog key={editingProvider?.slug ?? "new"} open={providerOpen} onOpenChange={(open) => { setProviderOpen(open); if (!open) setEditingProvider(null); }} provider={editingProvider} pending={mutation.isPending} onSubmit={saveProvider} />
      <AccountDialog account={selected} onOpenChange={(open) => !open && setSelected(null)} isAdmin={isAdmin} />
    </PageContainer>
  );
}

function ProviderDialog({ open, onOpenChange, provider, pending, onSubmit }: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  provider: ApiProvider | null;
  pending: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  const capabilities = provider?.capabilities;
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <form onSubmit={onSubmit}>
          <DialogHeader><DialogTitle>{provider ? "Edit custom provider" : "Add custom provider"}</DialogTitle><DialogDescription>Configure discovery/authentication metadata only. Put secrets on individual API accounts, never in static headers.</DialogDescription></DialogHeader>
          <div className="grid gap-4 py-4 sm:grid-cols-2">
            <Field label="Slug"><Input name="slug" defaultValue={provider?.slug} disabled={Boolean(provider)} required pattern="[a-z0-9][a-z0-9-]*" /></Field>
            <Field label="Display name"><Input name="display_name" defaultValue={provider?.display_name} required /></Field>
            <Field label="Adapter kind"><select name="adapter_kind" defaultValue={provider?.adapter_kind ?? "openai-compatible"} disabled={Boolean(provider)} className="h-8 w-full rounded-lg border bg-background px-2 text-sm"><option value="openai-compatible">OpenAI compatible</option><option value="anthropic">Anthropic compatible</option></select></Field>
            <Field label="Credential header"><Input name="credential_header" defaultValue={provider?.credential_header ?? "authorization"} required /></Field>
            <Field label="Default base URL" className="sm:col-span-2"><Input name="default_base_url" type="url" defaultValue={provider?.default_base_url ?? ""} placeholder="https://api.example.com/v1" /></Field>
            <Field label="Static non-secret headers (JSON)" className="sm:col-span-2"><Textarea name="static_headers" defaultValue={JSON.stringify(provider?.static_headers ?? {}, null, 2)} className="min-h-24 font-mono text-xs" /></Field>
            <div className="space-y-2 sm:col-span-2">
              <Label>Capabilities</Label>
              <div className="grid gap-2 sm:grid-cols-2">
                <Capability name="credential_validation" label="Credential validation" checked={capabilities?.credential_validation ?? true} />
                <Capability name="model_discovery" label="Model discovery" checked={capabilities?.model_discovery ?? true} />
                <Capability name="usage_sync" label="Provider usage sync" checked={capabilities?.usage_sync ?? false} />
                <Capability name="balance_sync" label="Provider balance sync" checked={capabilities?.balance_sync ?? false} />
                <Capability name="usage_by_model" label="Usage grouped by model" checked={capabilities?.usage_by_model ?? false} />
                <Capability name="usage_by_credential" label="Usage grouped by credential" checked={capabilities?.usage_by_credential ?? false} />
                <Capability name="manual_usage_import" label="Manual usage snapshots" checked={capabilities?.manual_usage_import ?? true} />
                <Capability name="is_enabled" label="Provider enabled" checked={provider?.is_enabled ?? true} />
              </div>
            </div>
          </div>
          <DialogFooter><Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button><Button type="submit" disabled={pending}>{pending ? "Saving…" : "Save provider"}</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function Capability({ name, label, checked }: { name: string; label: string; checked: boolean }) {
  return <label className="flex items-center gap-2 rounded-md border p-2 text-sm"><input type="checkbox" name={name} defaultChecked={checked} className="size-4" />{label}</label>;
}

function CreateAccountDialog({ open, onOpenChange, providers, pending, onSubmit }: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  providers: Array<{ slug: string; display_name: string; default_base_url: string | null }>;
  pending: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <form onSubmit={onSubmit}>
          <DialogHeader><DialogTitle>Add external API account</DialogTitle><DialogDescription>Register an account for inventory and usage tracking. This does not create a proxy gateway.</DialogDescription></DialogHeader>
          <div className="grid gap-4 py-4 sm:grid-cols-2">
            <Field label="Provider"><select name="provider_slug" className="h-8 w-full rounded-lg border bg-background px-2 text-sm" required>{providers.map((provider) => <option key={provider.slug} value={provider.slug}>{provider.display_name}</option>)}</select></Field>
            <Field label="Account name"><Input name="name" required maxLength={128} /></Field>
            <Field label="Purpose"><Input name="purpose" placeholder="Model evaluation, coding tools…" /></Field>
            <Field label="Owner"><Input name="owner" placeholder="Team or person" /></Field>
            <Field label="Base URL" className="sm:col-span-2"><Input name="base_url" type="url" placeholder="Provider default or https://api.example.com/v1" /></Field>
            <Field label="Credential name"><Input name="credential_name" placeholder="Primary" /></Field>
            <Field label="API key / bearer token"><Input name="credential_value" type="password" autoComplete="new-password" /></Field>
            <Field label="Billing currency"><Input name="billing_currency" placeholder="USD" /></Field>
            <Field label="Monthly budget"><Input name="monthly_budget" type="number" min="0" step="0.01" /></Field>
            <Field label="Tags" className="sm:col-span-2"><Input name="tags" placeholder="research, coding, production" /></Field>
            <Field label="Notes" className="sm:col-span-2"><Textarea name="notes" placeholder="Non-sensitive notes only" /></Field>
          </div>
          <DialogFooter><Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button><Button type="submit" disabled={pending}>{pending ? "Saving…" : "Save account"}</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function Field({ label, className, children }: { label: string; className?: string; children: React.ReactNode }) {
  return <div className={className}><Label className="mb-1.5">{label}</Label>{children}</div>;
}

function AccountDialog({ account, onOpenChange, isAdmin }: { account: ApiAccount | null; onOpenChange: (open: boolean) => void; isAdmin: boolean }) {
  const details = useApiAccountDetails(account?.id ?? null);
  const mutation = useApiResourceMutation();

  async function act(path: string, payload: unknown, schema: z.ZodType, message: string) {
    try {
      await mutation.mutateAsync({ path, payload, schema });
      toast.success(message);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Request failed");
    }
  }

  if (!account) return null;
  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[92vh] overflow-y-auto sm:max-w-4xl">
        <DialogHeader>
          <div className="flex flex-wrap items-center gap-2"><DialogTitle>{account.name}</DialogTitle><StatusBadge status={account.status} /><Badge variant="outline">{account.provider.display_name}</Badge></div>
          <DialogDescription>{account.base_url} · {account.owner || "No owner"} · Updated {formatDateTime(account.updated_at)}</DialogDescription>
        </DialogHeader>
        <Tabs defaultValue="credentials">
          <TabsList className="flex-wrap"><TabsTrigger value="credentials">Credentials</TabsTrigger><TabsTrigger value="models">Models</TabsTrigger><TabsTrigger value="usage">Usage & balance</TabsTrigger><TabsTrigger value="sync">Sync history</TabsTrigger></TabsList>
          <TabsContent value="credentials" className="mt-4 space-y-3">
            {details.credentials.data?.map((item) => <div key={item.id} className="flex items-center justify-between rounded-md border p-3"><div><div className="flex items-center gap-2"><KeyRound className="size-4 text-muted-foreground" /><span className="font-medium">{item.name}</span><StatusBadge status={item.status} /></div><p className="mt-1 font-mono text-xs text-muted-foreground">{item.masked_value}</p></div>{isAdmin && <Button size="sm" variant="outline" onClick={() => void act(`credentials/${item.id}/validate`, {}, apiCredentialSchema, "Credential validation completed")}>Validate</Button>}</div>)}
            {isAdmin && <CredentialForm accountId={account.id} onCreate={act} />}
          </TabsContent>
          <TabsContent value="models" className="mt-4 space-y-3">
            <div className="flex justify-end">{isAdmin && account.provider.capabilities.model_discovery && <Button size="sm" onClick={() => void act(`accounts/${account.id}/models/sync`, {}, apiSyncRunSchema, "Model synchronization completed")}><RefreshCw /> Sync models</Button>}</div>
            <div className="grid gap-2 sm:grid-cols-2">{details.models.data?.map((model) => <div key={model.id} className="rounded-md border p-3"><div className="flex items-center justify-between gap-2"><code className="truncate text-xs font-semibold">{model.provider_model_id}</code><StatusBadge status={model.is_available ? "available" : "unavailable"} /></div><p className="mt-2 text-xs text-muted-foreground">{model.source} · {model.context_window ? `${compact(model.context_window)} context` : "Context unknown"}</p></div>)}</div>
          </TabsContent>
          <TabsContent value="usage" className="mt-4 space-y-4">
            <div className="flex justify-end">{isAdmin && account.provider.capabilities.usage_sync && <Button size="sm" onClick={() => void act(`accounts/${account.id}/usage/sync`, {}, apiSyncRunSchema, "Usage synchronization completed")}><RefreshCw /> Sync provider usage</Button>}</div>
            <div className="grid gap-3 sm:grid-cols-2"><DataList title="Latest balance" rows={(details.balance.data ?? []).slice(0, 5).map((row) => ({ id: row.id, primary: amount(row.balance_amount ?? row.remaining_credit, row.currency), secondary: `${row.source} · ${formatDateTime(row.collected_at)}` }))} /><DataList title="Usage snapshots" rows={(details.usage.data ?? []).slice(0, 8).map((row) => ({ id: row.id, primary: `${compact(row.total_tokens ?? 0)} tokens · ${amount(row.cost_amount, row.currency)}`, secondary: `${row.source} · ${formatDateTime(row.period_start)}` }))} /></div>
            {isAdmin && <UsageForms account={account} onCreate={act} />}
          </TabsContent>
          <TabsContent value="sync" className="mt-4 space-y-2">{details.syncRuns.data?.map((run) => <div key={run.id} className="flex items-center justify-between rounded-md border p-3"><div><p className="font-medium">{run.sync_type}</p><p className="text-xs text-muted-foreground">{formatDateTime(run.created_at)} · {run.records_written} records</p></div><StatusBadge status={run.status} /></div>)}</TabsContent>
        </Tabs>
        {isAdmin && <DialogFooter><Button variant="destructive" onClick={() => void act(`accounts/${account.id}/archive`, {}, apiAccountSchema, "Account archived")}><Archive /> Archive account</Button></DialogFooter>}
      </DialogContent>
    </Dialog>
  );
}

function CredentialForm({ accountId, onCreate }: { accountId: string; onCreate: (path: string, payload: unknown, schema: z.ZodType, message: string) => Promise<void> }) {
  return <form className="grid gap-2 rounded-md border border-dashed p-3 sm:grid-cols-[1fr_1fr_auto]" onSubmit={(event) => { event.preventDefault(); const data = new FormData(event.currentTarget); void onCreate(`accounts/${accountId}/credentials`, { name: data.get("name"), value: data.get("value") }, apiCredentialSchema, "Credential added").then(() => event.currentTarget.reset()); }}><Input name="name" placeholder="Credential name" required /><Input name="value" type="password" placeholder="API key or token" required /><Button type="submit"><Plus /> Add</Button></form>;
}

function UsageForms({ account, onCreate }: { account: ApiAccount; onCreate: (path: string, payload: unknown, schema: z.ZodType, message: string) => Promise<void> }) {
  return <div className="grid gap-3 sm:grid-cols-2"><form className="space-y-2 rounded-md border border-dashed p-3" onSubmit={(event) => { event.preventDefault(); const data = new FormData(event.currentTarget); const end = new Date(); const start = new Date(end.getTime() - 86_400_000); void onCreate(`accounts/${account.id}/usage/manual`, { period_start: start.toISOString(), period_end: end.toISOString(), request_count: Number(data.get("requests") || 0), total_tokens: Number(data.get("tokens") || 0), cost_amount: Number(data.get("cost") || 0), currency: account.billing_currency }, apiUsageSchema, "Usage snapshot added").then(() => event.currentTarget.reset()); }}><p className="text-sm font-medium">Add usage snapshot</p><Input name="requests" type="number" min="0" placeholder="Requests" /><Input name="tokens" type="number" min="0" placeholder="Total tokens" /><Input name="cost" type="number" min="0" step="0.000001" placeholder="Cost" /><Button type="submit" size="sm">Save usage</Button></form><form className="space-y-2 rounded-md border border-dashed p-3" onSubmit={(event) => { event.preventDefault(); const data = new FormData(event.currentTarget); void onCreate(`accounts/${account.id}/balance/manual`, { balance_amount: Number(data.get("balance")), currency: account.billing_currency }, apiBalanceSchema, "Balance snapshot added").then(() => event.currentTarget.reset()); }}><p className="text-sm font-medium">Add balance snapshot</p><Input name="balance" type="number" step="0.000001" placeholder="Current balance" required /><Button type="submit" size="sm">Save balance</Button></form></div>;
}

function DataList({ title, rows }: { title: string; rows: Array<{ id: string; primary: string; secondary: string }> }) {
  return <div className="rounded-md border p-3"><h3 className="mb-2 font-medium">{title}</h3>{rows.length === 0 ? <p className="text-xs text-muted-foreground">No data recorded.</p> : rows.map((row) => <div key={row.id} className="border-t py-2 first:border-t-0"><p className="text-sm font-medium">{row.primary}</p><p className="text-xs text-muted-foreground">{row.secondary}</p></div>)}</div>;
}
