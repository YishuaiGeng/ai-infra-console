"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const metrics = [
  { time: "14:00", throughput: 28, latency: 164 },
  { time: "14:10", throughput: 31, latency: 151 },
  { time: "14:20", throughput: 29, latency: 172 },
  { time: "14:30", throughput: 38, latency: 138 },
  { time: "14:40", throughput: 42, latency: 126 },
  { time: "14:50", throughput: 36, latency: 142 },
  { time: "15:00", throughput: 44, latency: 121 },
];

export function DeploymentMetrics() {
  return (
    <div className="h-72 w-full p-3">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={metrics} margin={{ top: 8, right: 12, bottom: 0, left: -18 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey="time" fontSize={11} tickLine={false} axisLine={false} />
          <YAxis fontSize={11} tickLine={false} axisLine={false} />
          <Tooltip
            contentStyle={{
              background: "var(--popover)",
              border: "1px solid var(--border)",
              borderRadius: 6,
              color: "var(--popover-foreground)",
              fontSize: 12,
            }}
          />
          <Line
            type="monotone"
            dataKey="throughput"
            name="Throughput (tok/s)"
            stroke="var(--chart-2)"
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="latency"
            name="Latency (ms)"
            stroke="var(--chart-1)"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
