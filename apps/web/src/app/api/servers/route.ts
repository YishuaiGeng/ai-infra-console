import { proxyCentral } from "@/lib/server/central-api";

export async function GET() {
  return proxyCentral("/api/v1/servers");
}

export async function POST(request: Request) {
  return proxyCentral("/api/v1/servers/registrations", {
    method: "POST",
    body: await request.text(),
  });
}
