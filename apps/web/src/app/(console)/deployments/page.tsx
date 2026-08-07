import type { Metadata } from "next";
import { DeploymentsPage } from "@/features/deployments/deployments-page";

export const metadata: Metadata = { title: "Deployments" };
export default function Page() { return <DeploymentsPage />; }
