import type { Metadata } from "next";

import { ApiResourcesPage } from "@/features/api-resources/api-resources-page";

export const metadata: Metadata = { title: "API Resources" };

export default function Page() {
  return <ApiResourcesPage />;
}
