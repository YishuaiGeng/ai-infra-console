import { proxyCentral } from "@/lib/server/central-api";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  return proxyCentral(
    `/api/v1/deployments/${encodeURIComponent(id)}/test-api`,
    {
      method: "POST",
      body: await request.text(),
    },
  );
}
