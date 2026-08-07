"use client";

import { useMemo, useState } from "react";
import { Search } from "lucide-react";

import { models } from "@/mocks/data";
import { ModelCard } from "@/components/model/model-card";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Library } from "lucide-react";

export function ModelLibraryPage() {
  const [query, setQuery] = useState("");
  const [provider, setProvider] = useState("all");
  const [type, setType] = useState("all");
  const filtered = useMemo(
    () =>
      models.filter((model) => {
        const matchesQuery = `${model.name} ${model.displayName} ${model.tags.join(" ")}`
          .toLowerCase()
          .includes(query.toLowerCase());
        return (
          matchesQuery &&
          (provider === "all" || model.provider === provider) &&
          (type === "all" || model.type === type)
        );
      }),
    [provider, query, type],
  );

  return (
    <PageContainer>
      <PageHeader
        title="Model library"
        description="Discover curated model definitions from Hugging Face and ModelScope, then choose a target server."
      />
      <div className="mb-4 flex flex-col gap-2 rounded-md border bg-card p-3 sm:flex-row sm:items-center">
        <div className="relative w-full sm:max-w-md">
          <Search className="absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search models, organizations, or capabilities..."
            className="h-8 pl-8"
          />
        </div>
        <Select value={provider} onValueChange={(value) => value && setProvider(value)}>
          <SelectTrigger size="sm" className="w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All providers</SelectItem>
            <SelectItem value="Hugging Face">Hugging Face</SelectItem>
            <SelectItem value="ModelScope">ModelScope</SelectItem>
          </SelectContent>
        </Select>
        <Select value={type} onValueChange={(value) => value && setType(value)}>
          <SelectTrigger size="sm" className="w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All model types</SelectItem>
            <SelectItem value="LLM">LLM</SelectItem>
            <SelectItem value="Embedding">Embedding</SelectItem>
          </SelectContent>
        </Select>
        <span className="ml-auto text-xs text-muted-foreground">
          {filtered.length} definitions
        </span>
      </div>
      {filtered.length ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
          {filtered.map((model) => (
            <ModelCard key={model.id} model={model} />
          ))}
        </div>
      ) : (
        <div className="rounded-md border bg-card">
          <EmptyState
            icon={Library}
            title="No model definitions found"
            message="Change the query, provider, or model type to broaden the library search."
          />
        </div>
      )}
    </PageContainer>
  );
}
