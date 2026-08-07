import { AppShell } from "@/components/layout/app-shell";

export default function ConsoleLayout({ children }: LayoutProps<"/">) {
  return <AppShell>{children}</AppShell>;
}
