import { proxyCentral, webError } from "@/lib/server/central-api";

const actions = new Set(["start", "stop", "restart", "retry"]);

export async function POST(
  _request: Request,
  { params }: { params: Promise<{ id: string; action: string }> },
) {
  const { id, action } = await params;
  if (!actions.has(action)) {
    return webError(404, "deployment_action_not_found", "The deployment action does not exist.");
  }
  return proxyCentral(
    `/api/v1/deployments/${encodeURIComponent(id)}/${encodeURIComponent(action)}`,
    { method: "POST" },
  );
}
