import type { Metadata } from "next";
import { InstalledModelsPage } from "@/features/models/installed-models-page";

export const metadata: Metadata = { title: "Installed Models" };
export default function Page() { return <InstalledModelsPage />; }
