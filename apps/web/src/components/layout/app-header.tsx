"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRouter } from "next/navigation";
import { useState } from "react";
import {
  Bell,
  CheckCircle2,
  ChevronRight,
  Menu,
  Monitor,
  Moon,
  Sun,
  User,
} from "lucide-react";
import { useTheme } from "next-themes";

import { breadcrumbLabels } from "@/config/navigation";
import { useDeployment } from "@/hooks/use-deployments";
import {
  useInfrastructureSummary,
  useServers,
  useSession,
} from "@/hooks/use-infrastructure";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { MobileSidebar } from "@/components/layout/app-sidebar";

function ThemeToggle() {
  const { setTheme } = useTheme();

  return (
    <DropdownMenu>
      <Tooltip>
        <TooltipTrigger
          render={
            <DropdownMenuTrigger
              render={
                <Button variant="ghost" size="icon-sm" aria-label="Theme" />
              }
            />
          }
        >
          <Sun className="dark:hidden" />
          <Moon className="hidden dark:block" />
        </TooltipTrigger>
        <TooltipContent>Theme</TooltipContent>
      </Tooltip>
      <DropdownMenuContent align="end">
        <DropdownMenuGroup>
          <DropdownMenuLabel>Appearance</DropdownMenuLabel>
          <DropdownMenuItem onClick={() => setTheme("light")}>
            <Sun /> Light
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => setTheme("dark")}>
            <Moon /> Dark
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => setTheme("system")}>
            <Monitor /> System
          </DropdownMenuItem>
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function Breadcrumbs() {
  const pathname = usePathname();
  const serversQuery = useServers();
  const segments = pathname.split("/").filter(Boolean);
  const deploymentId = segments[0] === "deployments" ? segments[1] ?? "" : "";
  const deploymentQuery = useDeployment(deploymentId, deploymentId.length > 0);

  const getLabel = (segment: string, index: number) => {
    if (breadcrumbLabels[segment]) return breadcrumbLabels[segment];
    const previous = segments[index - 1];
    if (previous === "servers") {
      return serversQuery.data?.find((server) => server.id === segment)?.name ?? segment;
    }
    if (previous === "deployments") return deploymentQuery.data?.name ?? segment;
    return segment;
  };

  return (
    <nav aria-label="Breadcrumb" className="min-w-0">
      <ol className="flex min-w-0 items-center gap-1 text-sm">
        {segments.map((segment, index) => {
          const href = `/${segments.slice(0, index + 1).join("/")}`;
          const current = index === segments.length - 1;
          return (
            <li key={href} className="flex min-w-0 items-center gap-1">
              {index > 0 && (
                <ChevronRight className="size-3.5 shrink-0 text-muted-foreground" />
              )}
              {current ? (
                <span className="truncate font-medium">
                  {getLabel(segment, index)}
                </span>
              ) : (
                <Link
                  href={href}
                  className="truncate text-muted-foreground hover:text-foreground"
                >
                  {getLabel(segment, index)}
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

export function AppHeader() {
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);
  const summaryQuery = useInfrastructureSummary();
  const sessionQuery = useSession();
  const summary = summaryQuery.data;

  const signOut = async () => {
    await fetch("/api/session", { method: "DELETE" });
    router.replace("/login");
    router.refresh();
  };

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between gap-3 border-b bg-background/95 px-4 backdrop-blur-sm sm:px-6">
      <div className="flex min-w-0 items-center gap-2">
        <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
          <SheetTrigger
            render={
              <Button
                variant="ghost"
                size="icon-sm"
                className="lg:hidden"
                aria-label="Open navigation"
              />
            }
          >
            <Menu />
          </SheetTrigger>
          <SheetContent side="left" className="w-64 p-0" showCloseButton={false}>
            <MobileSidebar onClose={() => setMobileOpen(false)} />
          </SheetContent>
        </Sheet>
        <Breadcrumbs />
      </div>

      <div className="flex shrink-0 items-center gap-0.5">
        <div className="mr-2 hidden items-center gap-1.5 border-r pr-3 text-xs text-muted-foreground sm:flex">
          <span className="relative flex size-2">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400 opacity-40" />
            <span className="relative inline-flex size-2 rounded-full bg-emerald-500" />
          </span>
          {summary?.online_server_count ?? 0} servers online
        </div>
        <ThemeToggle />
        <DropdownMenu>
          <Tooltip>
            <TooltipTrigger
              render={
                <DropdownMenuTrigger
                  render={
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      className="relative"
                      aria-label="Notifications"
                    />
                  }
                />
              }
            >
              <Bell />
              <span className="absolute right-1 top-1 size-1.5 rounded-full bg-red-500" />
            </TooltipTrigger>
            <TooltipContent>Notifications</TooltipContent>
          </Tooltip>
          <DropdownMenuContent align="end" className="w-80">
            <DropdownMenuGroup>
              <DropdownMenuLabel>Notifications</DropdownMenuLabel>
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            <div className="p-2 text-sm">
              <div className="mb-1 flex items-center gap-2 font-medium">
                <CheckCircle2 className="size-4 text-emerald-500" />
                Infrastructure summary
              </div>
              <p className="pl-6 text-xs leading-5 text-muted-foreground">
                {summary?.online_server_count ?? 0} servers online and{" "}
                {summary?.available_gpu_count ?? 0} GPUs available.
              </p>
            </div>
          </DropdownMenuContent>
        </DropdownMenu>
        <DropdownMenu>
          <DropdownMenuTrigger
            render={
              <Button variant="ghost" size="icon-sm" aria-label="User menu" />
            }
          >
            <User />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuGroup>
              <DropdownMenuLabel>
                <span className="block">
                  {sessionQuery.data?.username ?? "Account"}
                </span>
                <span className="block text-xs font-normal text-muted-foreground">
                  {sessionQuery.data?.role ?? "Authenticated session"}
                </span>
              </DropdownMenuLabel>
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => void signOut()}>
              Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
