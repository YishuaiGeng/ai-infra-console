import { proxyCentral } from "@/lib/server/central-api";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  return proxyCentral(`/api/v1/models/${encodeURIComponent(id)}`);
}
