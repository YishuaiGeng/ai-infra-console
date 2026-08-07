"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Library, Search } from "lucide-react";

import { useCatalogModels } from "@/hooks/use-downloads";
import { useSession } from "@/hooks/use-infrastructure";
import { ModelCard } from "@/components/model/model-card";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export function ModelLibraryPage() {
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [provider, setProvider] = useState<"all" | "huggingface" | "modelscope">("all");
  const [type, setType] = useState("all");
  const catalogQuery = useCatalogModels(debouncedQuery, provider);
  const sessionQuery = useSession();

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebouncedQuery(query.trim()), 350);
    return () => window.clearTimeout(timeout);
  }, [query]);

  const filtered = useMemo(() => {
    const models = catalogQuery.data?.items ?? [];
    return type === "all"
      ? models
      : models.filter((model) => model.modelType.toLowerCase().includes(type));
  }, [catalogQuery.data?.items, type]);
  const providerErrors = Object.entries(catalogQuery.data?.providerErrors ?? {});

  return (
    <PageContainer>
      <PageHeader
        title="Model library"
        description="Search Hugging Face and ModelScope, then queue an allowlisted Agent download."
      />
      <div className="mb-4 flex flex-col gap-2 rounded-md border bg-card p-3 sm:flex-row sm:items-center">
        <div className="relative w-full sm:max-w-md">
          <Search className="absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search models or organizations..."
            className="h-8 pl-8"
          />
        </div>
        <Select
          value={provider}
          onValueChange={(value) =>
            value && setProvider(value as "all" | "huggingface" | "modelscope")
          }
        >
          <SelectTrigger size="sm" className="w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All providers</SelectItem>
            <SelectItem value="huggingface">Hugging Face</SelectItem>
            <SelectItem value="modelscope">ModelScope</SelectItem>
          </SelectContent>
        </Select>
        <Select value={type} onValueChange={(value) => value && setType(value)}>
          <SelectTrigger size="sm" className="w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All model types</SelectItem>
            <SelectItem value="generation">Generation</SelectItem>
            <SelectItem value="embedding">Embedding</SelectItem>
          </SelectContent>
        </Select>
        <span className="ml-auto whitespace-nowrap text-xs text-muted-foreground">
          {catalogQuery.isFetching ? "Searching..." : `${filtered.length} results`}
        </span>
      </div>
      {providerErrors.length > 0 && (
        <div className="mb-4 flex items-start gap-2 border-y border-warning/30 bg-warning/5 px-3 py-2 text-xs text-muted-foreground">
          <AlertTriangle className="mt-0.5 size-3.5 shrink-0 text-warning" />
          <span>
            {providerErrors.map(([name, code]) => `${name}: ${code}`).join(" / ")}
          </span>
        </div>
      )}
      {catalogQuery.isPending ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
          {Array.from({ length: 6 }, (_, index) => (
            <div key={index} className="h-64 animate-pulse rounded-md border bg-muted/30" />
          ))}
        </div>
      ) : catalogQuery.isError ? (
        <ErrorState
          title="Model catalog unavailable"
          message={catalogQuery.error.message}
          onRetry={() => void catalogQuery.refetch()}
        />
      ) : filtered.length ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
          {filtered.map((model) => (
            <ModelCard
              key={model.id}
              model={model}
              isAdmin={sessionQuery.data?.role === "admin"}
            />
          ))}
        </div>
      ) : (
        <div className="border-y bg-card">
          <EmptyState
            icon={Library}
            title="No model definitions found"
            message="Change the query, provider, or model type to broaden the search."
          />
        </div>
      )}
    </PageContainer>
  );
}
