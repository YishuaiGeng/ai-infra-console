import type { Metadata } from "next";
import { DownloadsPage } from "@/features/downloads/downloads-page";

export const metadata: Metadata = { title: "Downloads" };
export default function Page() { return <DownloadsPage />; }
