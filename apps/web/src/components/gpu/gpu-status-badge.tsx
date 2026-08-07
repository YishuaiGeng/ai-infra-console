import type { GPUStatus } from "@/types";
import { StatusBadge } from "@/components/shared/status-badge";

export function GPUStatusBadge({ status }: { status: GPUStatus }) {
  return <StatusBadge status={status} />;
}
