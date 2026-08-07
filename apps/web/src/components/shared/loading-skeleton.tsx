import { PageContainer } from "@/components/layout/page-container";
import { Skeleton } from "@/components/ui/skeleton";

export function PageLoadingSkeleton() {
  return (
    <PageContainer>
      <div className="mb-5 space-y-2">
        <Skeleton className="h-7 w-48" />
        <Skeleton className="h-4 w-[min(30rem,80%)]" />
      </div>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        {Array.from({ length: 5 }).map((_, index) => (
          <Skeleton key={index} className="h-28 rounded-md" />
        ))}
      </div>
      <Skeleton className="mt-4 h-[420px] rounded-md" />
    </PageContainer>
  );
}

export function TableLoadingSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div className="space-y-2 p-4">
      {Array.from({ length: rows }).map((_, index) => (
        <Skeleton key={index} className="h-10 w-full rounded-sm" />
      ))}
    </div>
  );
}
