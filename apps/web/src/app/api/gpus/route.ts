import { proxyCentral } from "@/lib/server/central-api";

export async function GET() {
  return proxyCentral("/api/v1/gpus");
}
