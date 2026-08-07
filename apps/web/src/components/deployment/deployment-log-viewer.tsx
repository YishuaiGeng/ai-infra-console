"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowDownToLine, Search } from "lucide-react";

import { deploymentLogs } from "@/mocks/data";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";

export function DeploymentLogViewer() {
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState("100");
  const [follow, setFollow] = useState(true);
  const endRef = useRef<HTMLDivElement>(null);
  const filtered = useMemo(
    () =>
      deploymentLogs.filter((line) =>
        line.toLowerCase().includes(query.toLowerCase()),
      ),
    [query],
  );

  useEffect(() => {
    if (follow) endRef.current?.scrollIntoView({ block: "nearest" });
  }, [follow, filtered]);

  return (
    <div className="overflow-hidden rounded-md border bg-[#090c10] text-slate-200">
      <div className="flex flex-col gap-2 border-b border-white/10 bg-[#11161d] p-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full sm:max-w-xs">
          <Search className="absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-slate-500" />
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search logs..."
            className="h-8 border-white/10 bg-white/5 pl-8 text-slate-100 placeholder:text-slate-500"
          />
        </div>
        <div className="flex items-center gap-3">
          <Select
            value={limit}
            onValueChange={(value) => value && setLimit(value)}
          >
            <SelectTrigger className="h-8 border-white/10 bg-white/5 text-slate-200">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="100">Last 100</SelectItem>
              <SelectItem value="500">Last 500</SelectItem>
              <SelectItem value="1000">Last 1000</SelectItem>
            </SelectContent>
          </Select>
          <label className="flex items-center gap-2 whitespace-nowrap text-xs text-slate-400">
            <Switch checked={follow} onCheckedChange={setFollow} />
            <ArrowDownToLine className="size-3.5" /> Follow
          </label>
        </div>
      </div>
      <div className="max-h-[430px] min-h-72 overflow-auto p-3 font-mono text-xs leading-6">
        {filtered.length ? (
          filtered.map((line, index) => {
            const isWarning = line.includes("WARN");
            const isError = line.includes("ERROR");
            return (
              <div
                key={`${index}-${line}`}
                className={
                  isError
                    ? "text-red-300"
                    : isWarning
                      ? "text-amber-300"
                      : line.includes("INFO")
                        ? "text-slate-300"
                        : "text-slate-400"
                }
              >
                <span className="mr-3 select-none text-slate-700">
                  {String(index + 1).padStart(3, "0")}
                </span>
                {line}
              </div>
            );
          })
        ) : (
          <div className="py-12 text-center text-slate-500">
            No log lines match the query.
          </div>
        )}
        <div ref={endRef} />
      </div>
      <div className="flex items-center justify-between border-t border-white/10 bg-[#11161d] px-3 py-1.5 font-mono text-[10px] text-slate-500">
        <span>{filtered.length} visible lines</span>
        <span>runtime stream / follow={String(follow)}</span>
      </div>
    </div>
  );
}
