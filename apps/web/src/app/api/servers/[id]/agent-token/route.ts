import { proxyCentral } from "@/lib/server/central-api";

export async function POST(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  return proxyCentral(`/api/v1/servers/${encodeURIComponent(id)}/agent-token`, {
    method: "POST",
  });
}
