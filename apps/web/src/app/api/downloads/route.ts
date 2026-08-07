import { proxyCentral } from "@/lib/server/central-api";

export async function GET(request: Request) {
  return proxyCentral(`/api/v1/downloads${new URL(request.url).search}`);
}

export async function POST(request: Request) {
  return proxyCentral("/api/v1/downloads", {
    method: "POST",
    body: await request.text(),
  });
}
