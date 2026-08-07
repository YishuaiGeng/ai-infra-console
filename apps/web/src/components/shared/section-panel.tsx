import { cn } from "@/lib/utils";

export function SectionPanel({
  title,
  description,
  action,
  children,
  className,
  contentClassName,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  contentClassName?: string;
}) {
  return (
    <section className={cn("overflow-hidden rounded-md border bg-card", className)}>
      <div className="flex min-h-12 items-center justify-between gap-4 border-b px-4 py-2.5">
        <div>
          <h2 className="text-sm font-semibold">{title}</h2>
          {description && (
            <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>
          )}
        </div>
        {action}
      </div>
      <div className={contentClassName}>{children}</div>
    </section>
  );
}
