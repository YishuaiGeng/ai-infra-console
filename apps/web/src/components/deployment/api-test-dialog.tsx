"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Play } from "lucide-react";
import { z } from "zod";

import type { Deployment } from "@/types";
import { useTestApiEndpoint } from "@/hooks/use-deployments";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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

export function ApiTestDialog({ deployment }: { deployment: Deployment }) {
  const testApi = useTestApiEndpoint();
  const [open, setOpen] = useState(false);
  const { register, handleSubmit, formState: { errors } } = useForm<TestValues>({
    resolver: zodResolver(testSchema),
    defaultValues: { prompt: "Hello", maxTokens: 128, temperature: 0.7 },
  });

  const submit = async (values: TestValues) => {
    await testApi.mutateAsync({ id: deployment.id, input: values }).catch(() => undefined);
  };

  const result = testApi.data;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button variant="outline" size="sm" />}>
        <Play /> Test API
      </DialogTrigger>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Test API endpoint</DialogTitle>
          <DialogDescription className="font-mono">
            {deployment.endpoint.replace(/\/$/, "")}/chat/completions
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(submit)} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor={`prompt-${deployment.id}`}>Prompt</Label>
            <Textarea id={`prompt-${deployment.id}`} rows={4} {...register("prompt")} />
            {errors.prompt && <p className="text-xs text-destructive">{errors.prompt.message}</p>}
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor={`tokens-${deployment.id}`}>Max tokens</Label>
              <Input id={`tokens-${deployment.id}`} type="number" {...register("maxTokens", { valueAsNumber: true })} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor={`temperature-${deployment.id}`}>Temperature</Label>
              <Input id={`temperature-${deployment.id}`} type="number" min="0" max="2" step="0.1" {...register("temperature", { valueAsNumber: true })} />
            </div>
          </div>
          {testApi.isError && (
            <Alert variant="destructive">
              <AlertTitle>API test failed</AlertTitle>
              <AlertDescription>{testApi.error.message}</AlertDescription>
            </Alert>
          )}
          {result && (
            <div className="rounded-md border bg-muted/25 p-3">
              <div className="text-xs font-semibold">Response</div>
              <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-muted-foreground">
                {result.response}
              </p>
              <div className="mt-3 flex flex-wrap gap-4 border-t pt-2 font-mono text-[11px] text-muted-foreground">
                <span>{Math.round(result.latencyMs)} ms</span>
                <span>{result.inputTokens ?? "--"} input tokens</span>
                <span>{result.outputTokens ?? "--"} output tokens</span>
                <span>{result.totalTokens ?? "--"} total tokens</span>
                <span>{result.model ?? deployment.model.sourceId}</span>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button type="submit" disabled={testApi.isPending}>
              <Play /> {testApi.isPending ? "Sending..." : "Send request"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
