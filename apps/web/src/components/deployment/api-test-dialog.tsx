"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Play } from "lucide-react";
import { z } from "zod";

import type { ApiEndpoint } from "@/types";
import { getModel } from "@/mocks/data";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

const testSchema = z.object({
  prompt: z.string().min(1, "Enter a prompt."),
  maxTokens: z.number().int().min(1).max(4096),
  temperature: z.number().min(0).max(2),
});
type TestValues = z.infer<typeof testSchema>;

export function ApiTestDialog({ endpoint }: { endpoint: ApiEndpoint }) {
  const [response, setResponse] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<{ latency: number; input: number; output: number } | null>(null);
  const { register, handleSubmit, formState: { errors } } = useForm<TestValues>({
    resolver: zodResolver(testSchema),
    defaultValues: { prompt: "Hello", maxTokens: 128, temperature: 0.7 },
  });

  const submit = (values: TestValues) => {
    setResponse(
      `Hello! The ${getModel(endpoint.modelId)?.displayName} endpoint is responding normally. Your prompt was: "${values.prompt}"`,
    );
    setMetrics({ latency: endpoint.latencyMs ?? 84, input: 8, output: 24 });
  };

  return (
    <Dialog>
      <DialogTrigger render={<Button variant="outline" size="sm" />}>
        <Play /> Test API
      </DialogTrigger>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Test API endpoint</DialogTitle>
          <DialogDescription className="font-mono">{endpoint.endpoint}/chat/completions</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(submit)} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor={`prompt-${endpoint.id}`}>Prompt</Label>
            <Textarea id={`prompt-${endpoint.id}`} rows={4} {...register("prompt")} />
            {errors.prompt && <p className="text-xs text-destructive">{errors.prompt.message}</p>}
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor={`tokens-${endpoint.id}`}>Max tokens</Label>
              <Input id={`tokens-${endpoint.id}`} type="number" {...register("maxTokens", { valueAsNumber: true })} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor={`temperature-${endpoint.id}`}>Temperature</Label>
              <Input id={`temperature-${endpoint.id}`} type="number" min="0" max="2" step="0.1" {...register("temperature", { valueAsNumber: true })} />
            </div>
          </div>
          {response && (
            <div className="rounded-md border bg-muted/25 p-3">
              <div className="text-xs font-semibold">Response</div>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">{response}</p>
              {metrics && (
                <div className="mt-3 flex flex-wrap gap-4 border-t pt-2 font-mono text-[11px] text-muted-foreground">
                  <span>{metrics.latency} ms</span>
                  <span>{metrics.input} input tokens</span>
                  <span>{metrics.output} output tokens</span>
                  <span>{metrics.input + metrics.output} total tokens</span>
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            <Button type="submit"><Play /> Send request</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
