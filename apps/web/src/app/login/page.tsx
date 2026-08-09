import type { Metadata } from "next";
import Image from "next/image";
import { LockKeyhole } from "lucide-react";

import { LoginForm } from "@/features/auth/login-form";

export const metadata: Metadata = { title: "Sign in" };

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string }>;
}) {
  const { next } = await searchParams;
  return (
    <main className="grid min-h-screen place-items-center bg-muted/25 px-4 py-10">
      <section className="w-full max-w-sm" aria-labelledby="login-title">
        <div className="mb-8 flex items-center gap-3">
          <div className="grid size-10 place-items-center overflow-hidden rounded-md border bg-black">
            <Image
              src="/brand/logo-mark.png"
              alt=""
              width={40}
              height={40}
              className="size-10 object-cover"
              priority
            />
          </div>
          <div>
            <div className="text-base font-semibold">AI Infra Console</div>
            <div className="font-mono text-xs text-muted-foreground">
              Central control plane
            </div>
          </div>
        </div>

        <div className="rounded-md border bg-card p-6 shadow-sm">
          <LockKeyhole className="size-5 text-muted-foreground" />
          <h1 id="login-title" className="mt-4 text-xl font-semibold">
            Sign in
          </h1>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            Use an active Central API account to access infrastructure data.
          </p>
          <LoginForm nextPath={next} />
        </div>
      </section>
    </main>
  );
}
