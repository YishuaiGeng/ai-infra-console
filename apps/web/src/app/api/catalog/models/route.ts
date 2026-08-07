import { proxyCentral } from "@/lib/server/central-api";

export async function GET(request: Request) {
  return proxyCentral(`/api/v1/catalog/models${new URL(request.url).search}`);
}
