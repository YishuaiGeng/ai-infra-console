import type { Deployment } from "@/types";
import { formatDateTime } from "@/lib/format";
import { StatusBadge } from "@/components/shared/status-badge";

export function DeploymentMetrics({ deployment }: { deployment: Deployment }) {
  const values = [
    ["Health", <StatusBadge key="health" status={deployment.healthStatus} />],
    [
      "Probe latency",
      <span key="latency" className="font-mono text-sm font-medium">
        {deployment.healthLatencyMs === null
          ? "--"
          : `${Math.round(deployment.healthLatencyMs)} ms`}
      </span>,
    ],
    [
      "Last health probe",
      <span key="health-time" className="font-mono text-xs">
        {deployment.lastHealthCheckedAt
          ? formatDateTime(deployment.lastHealthCheckedAt)
          : "Not reported"}
      </span>,
    ],
    [
      "Last reconciliation",
      <span key="reconciled" className="font-mono text-xs">
        {deployment.lastReconciledAt
          ? formatDateTime(deployment.lastReconciledAt)
          : "Not reported"}
      </span>,
    ],
  ];

  return (
    <div className="grid sm:grid-cols-2 xl:grid-cols-4">
      {values.map(([label, value]) => (
        <div key={String(label)} className="border-b p-4 sm:border-r xl:border-b-0">
          <div className="text-xs font-medium text-muted-foreground">{label}</div>
          <div className="mt-2">{value}</div>
        </div>
      ))}
    </div>
  );
}
