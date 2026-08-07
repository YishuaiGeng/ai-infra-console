import Link from "next/link";
import { ArrowLeft, SearchX } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-muted/20 p-6">
      <div className="max-w-md text-center">
        <SearchX className="mx-auto mb-4 size-10 text-muted-foreground" />
        <h1 className="text-xl font-semibold">Resource not found</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          The server, deployment, or page you requested does not exist in this
          console.
        </p>
        <Link
          href="/dashboard"
          className={buttonVariants({ className: "mt-5" })}
        >
          <ArrowLeft /> Back to dashboard
        </Link>
      </div>
    </main>
  );
}
