import type { GPUProcess } from "@/types";
import { formatDateTime, formatNumber } from "@/lib/format";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export function GPUProcessTable({ processes }: { processes: GPUProcess[] }) {
  if (!processes.length) {
    return (
      <div className="px-4 py-10 text-center text-sm text-muted-foreground">
        No active GPU processes on this server.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>GPU</TableHead>
            <TableHead>PID</TableHead>
            <TableHead>User</TableHead>
            <TableHead>Command</TableHead>
            <TableHead>VRAM</TableHead>
            <TableHead>Collected</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {processes.map((process) => (
            <TableRow key={process.id}>
              <TableCell className="font-mono text-xs">
                GPU {process.gpuIndex ?? "--"}
              </TableCell>
              <TableCell className="numeric font-mono text-xs">
                {process.pid}
              </TableCell>
              <TableCell>{process.user}</TableCell>
              <TableCell className="max-w-sm truncate font-mono text-xs">
                {process.command}
              </TableCell>
              <TableCell className="numeric font-mono text-xs">
                {formatNumber(process.memoryGb)} GB
              </TableCell>
              <TableCell className="whitespace-nowrap text-xs text-muted-foreground">
                {formatDateTime(process.startedAt)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
