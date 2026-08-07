import type { ReactNode } from "react";

import { AppShell } from "@/components/layout/app-shell";

export default function ConsoleLayout({ children }: Readonly<{ children: ReactNode }>) {
  return <AppShell>{children}</AppShell>;
}
