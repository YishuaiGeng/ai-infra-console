"use client";

import { AppHeader } from "@/components/layout/app-header";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { useUiStore } from "@/stores/ui-store";

export function AppShell({ children }: { children: React.ReactNode }) {
  const collapsed = useUiStore((state) => state.sidebarCollapsed);

  return (
    <div className="min-h-screen bg-muted/20">
      <AppSidebar />
      <div
        className={
          collapsed
            ? "min-h-screen transition-[padding] duration-200 lg:pl-[68px]"
            : "min-h-screen transition-[padding] duration-200 lg:pl-60"
        }
      >
        <AppHeader />
        <main>{children}</main>
      </div>
    </div>
  );
}
