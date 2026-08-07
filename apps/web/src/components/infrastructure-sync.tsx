"use client";

import { usePathname } from "next/navigation";

import { useInfrastructureEvents } from "@/hooks/use-infrastructure";

export function InfrastructureSync() {
  const pathname = usePathname();
  useInfrastructureEvents(pathname !== "/login");
  return null;
}
