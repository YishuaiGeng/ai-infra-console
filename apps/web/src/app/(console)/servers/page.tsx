import type { Metadata } from "next";
import { ServersPage } from "@/features/servers/servers-page";

export const metadata: Metadata = { title: "Servers" };

export default function Page() {
  return <ServersPage />;
}
