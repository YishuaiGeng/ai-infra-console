"use client";

import { RotateCcw, TriangleAlert } from "lucide-react";

import { Button } from "@/components/ui/button";

export function ErrorState({
  title,
  message,
  onRetry,
}: {
  title: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex min-h-72 flex-col items-center justify-center rounded-md border border-red-200 bg-red-50/40 px-6 py-12 text-center dark:border-red-950 dark:bg-red-950/10">
      <TriangleAlert className="mb-3 size-9 text-red-500" />
      <h2 className="text-base font-semibold">{title}</h2>
      <p className="mt-1 max-w-md text-sm text-muted-foreground">{message}</p>
      {onRetry && (
        <Button variant="outline" className="mt-4" onClick={onRetry}>
          <RotateCcw /> Retry
        </Button>
      )}
    </div>
  );
}
