import { proxyCentral } from "@/lib/server/central-api";

export async function GET(request: Request) {
  return proxyCentral(`/api/v1/deployments${new URL(request.url).search}`);
}

export async function POST(request: Request) {
  return proxyCentral("/api/v1/deployments", {
    method: "POST",
    body: await request.text(),
  });
}
