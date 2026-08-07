import type { Metadata } from "next";

import { ServerDetailPage } from "@/features/servers/server-detail-page";

export const metadata: Metadata = { title: "Server" };

export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ServerDetailPage serverId={id} />;
}
