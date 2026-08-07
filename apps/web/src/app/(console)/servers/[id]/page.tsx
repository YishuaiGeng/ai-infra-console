import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { servers } from "@/mocks/data";
import { ServerDetailPage } from "@/features/servers/server-detail-page";

export function generateStaticParams() {
  return servers.map((server) => ({ id: server.id }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const server = servers.find((item) => item.id === id);
  return { title: server?.name ?? "Server" };
}

export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const server = servers.find((item) => item.id === id);
  if (!server) notFound();
  return <ServerDetailPage server={server} />;
}
