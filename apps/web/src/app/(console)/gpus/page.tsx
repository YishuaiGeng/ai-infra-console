import type { Metadata } from "next";
import { GpusPage } from "@/features/gpus/gpus-page";

export const metadata: Metadata = { title: "GPUs" };

export default function Page() {
  return <GpusPage />;
}
