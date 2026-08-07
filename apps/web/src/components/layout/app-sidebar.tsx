"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Braces, ChevronLeft, ChevronRight, Cpu, X } from "lucide-react";

import { navigation } from "@/config/navigation";
import { cn } from "@/lib/utils";
import { useUiStore } from "@/stores/ui-store";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

function NavContent({
  collapsed,
  onNavigate,
}: {
  collapsed: boolean;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();

  return (
    <>
      <div className="flex h-14 shrink-0 items-center border-b px-3">
        <Link
          href="/dashboard"
          className={cn(
            "flex min-w-0 items-center gap-2.5 overflow-hidden",
            collapsed && "justify-center",
          )}
          onClick={onNavigate}
        >
          <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-foreground text-background">
            <Cpu className="size-4" />
          </span>
          {!collapsed && (
            <span className="min-w-0">
              <span className="block truncate text-sm font-semibold">
                AI Infra Console
              </span>
              <span className="block truncate font-mono text-[10px] text-muted-foreground">
                CONTROL PLANE
              </span>
            </span>
          )}
        </Link>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 py-3">
        {navigation.map((group) => (
          <div key={group.label} className="mb-4 last:mb-0">
            {!collapsed && (
              <div className="mb-1 px-2 text-[10px] font-semibold uppercase text-muted-foreground">
                {group.label}
              </div>
            )}
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const active = item.match
                  ? item.match.some((path) => pathname.startsWith(path))
                  : pathname === item.href;
                const Icon = item.icon;
                const link = (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={onNavigate}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "flex h-8 items-center gap-2 rounded-md px-2 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
                      active &&
                        "bg-muted font-medium text-foreground shadow-[inset_2px_0_0_var(--foreground)]",
                      collapsed && "justify-center px-0",
                    )}
                  >
                    <Icon className="size-4 shrink-0" />
                    {!collapsed && <span className="truncate">{item.label}</span>}
                  </Link>
                );

                return collapsed ? (
                  <Tooltip key={item.href}>
                    <TooltipTrigger render={link} />
                    <TooltipContent side="right">{item.label}</TooltipContent>
                  </Tooltip>
                ) : (
                  link
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="border-t p-2">
        <div
          className={cn(
            "flex items-center gap-2 rounded-md border bg-background p-2",
            collapsed && "justify-center border-0 bg-transparent p-1",
          )}
        >
          <Braces className="size-4 shrink-0 text-muted-foreground" />
          {!collapsed && (
            <div className="min-w-0 flex-1">
              <div className="text-xs font-medium">Preview environment</div>
              <div className="font-mono text-[10px] text-muted-foreground">
                local / v0.1.0
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

export function AppSidebar() {
  const collapsed = useUiStore((state) => state.sidebarCollapsed);
  const toggleSidebar = useUiStore((state) => state.toggleSidebar);

  return (
    <aside
      className={cn(
        "fixed inset-y-0 left-0 z-40 hidden flex-col border-r bg-sidebar text-sidebar-foreground transition-[width] duration-200 lg:flex",
        collapsed ? "w-[68px]" : "w-60",
      )}
    >
      <NavContent collapsed={collapsed} />
      <Tooltip>
        <TooltipTrigger
          render={
            <Button
              variant="outline"
              size="icon-xs"
              className="absolute -right-3 top-[70px] rounded-full bg-background"
              onClick={toggleSidebar}
              aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            />
          }
        >
          {collapsed ? <ChevronRight /> : <ChevronLeft />}
        </TooltipTrigger>
        <TooltipContent side="right">
          {collapsed ? "Expand sidebar" : "Collapse sidebar"}
        </TooltipContent>
      </Tooltip>
    </aside>
  );
}

export function MobileSidebar({ onClose }: { onClose: () => void }) {
  return (
    <div className="flex h-full flex-col bg-sidebar text-sidebar-foreground">
      <Button
        variant="ghost"
        size="icon-sm"
        className="absolute right-3 top-3 z-10"
        onClick={onClose}
        aria-label="Close navigation"
      >
        <X />
      </Button>
      <NavContent collapsed={false} onNavigate={onClose} />
    </div>
  );
}
