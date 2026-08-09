import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppProviders } from "@/components/app-providers";

import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://github.com/YishuaiGeng/ai-infra-console"),
  title: {
    default: "AI Infra Console",
    template: "%s | AI Infra Console",
  },
  description:
    "A lightweight control plane for AI servers, GPUs, models, and inference runtimes.",
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/favicon-32x32.png", type: "image/png", sizes: "32x32" },
      { url: "/icon-192.png", type: "image/png", sizes: "192x192" },
      { url: "/icon-512.png", type: "image/png", sizes: "512x512" },
    ],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180" }],
  },
  openGraph: {
    title: "AI Infra Console",
    description:
      "A lightweight control plane for AI servers, GPUs, models, and inference runtimes.",
    type: "website",
    images: [{ url: "/brand/logo.png", width: 1536, height: 1024 }],
  },
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-background font-sans text-foreground antialiased">
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
