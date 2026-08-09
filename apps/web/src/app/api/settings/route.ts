import { proxyCentral } from "@/lib/server/central-api";

export async function GET() {
  return proxyCentral("/api/v1/settings");
}

export async function PUT(request: Request) {
  return proxyCentral("/api/v1/settings", {
    method: "PUT",
    body: await request.text(),
  });
}
