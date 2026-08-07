import type { Metadata } from "next";
import { ModelLibraryPage } from "@/features/models/model-library-page";

export const metadata: Metadata = { title: "Model Library" };
export default function Page() { return <ModelLibraryPage />; }
