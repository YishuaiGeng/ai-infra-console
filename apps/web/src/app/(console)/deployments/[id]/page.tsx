import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { deployments } from "@/mocks/data";
import { DeploymentDetailPage } from "@/features/deployments/deployment-detail-page";

export function generateStaticParams() {
  return deployments.map((deployment) => ({ id: deployment.id }));
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  return { title: deployments.find((item) => item.id === id)?.name ?? "Deployment" };
}

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const deployment = deployments.find((item) => item.id === id);
  if (!deployment) notFound();
  return <DeploymentDetailPage deployment={deployment} />;
}
