import { proxyCentral } from "@/lib/server/central-api";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  return proxyCentral(
    `/api/v1/deployments/${encodeURIComponent(id)}/logs${new URL(request.url).search}`,
  );
}
