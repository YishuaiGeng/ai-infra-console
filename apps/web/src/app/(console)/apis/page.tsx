import type { Metadata } from "next";
import { ApiEndpointsPage } from "@/features/api-endpoints/api-endpoints-page";

export const metadata: Metadata = { title: "API Endpoints" };
export default function Page() { return <ApiEndpointsPage />; }
