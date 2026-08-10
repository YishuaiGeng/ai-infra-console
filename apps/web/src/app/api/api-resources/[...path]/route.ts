import { proxyCentral } from "@/lib/server/central-api";

type Context = { params: Promise<{ path: string[] }> };

async function forward(request: Request, context: Context) {
  const { path } = await context.params;
  const url = new URL(request.url);
  const suffix = path.map(encodeURIComponent).join("/");
  const body = request.method === "GET" || request.method === "DELETE"
    ? undefined
    : await request.text();
  return proxyCentral(`/api/v1/api-resources/${suffix}${url.search}`, {
    method: request.method,
    body: body || undefined,
  });
}

export const GET = forward;
export const POST = forward;
export const PATCH = forward;
export const DELETE = forward;
