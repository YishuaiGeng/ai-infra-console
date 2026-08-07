"use client";

import { PageContainer } from "@/components/layout/page-container";
import { ErrorState } from "@/components/shared/error-state";

export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <PageContainer>
      <ErrorState
        title="Failed to load console data"
        message="The page could not be rendered. Retry the request or return to the dashboard."
        onRetry={reset}
      />
    </PageContainer>
  );
}
