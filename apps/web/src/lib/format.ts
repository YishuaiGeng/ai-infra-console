export function formatPercent(value: number | null) {
  return value === null ? "--" : `${Math.round(value)}%`;
}

export function formatMemory(used: number | null, total: number) {
  return used === null ? `-- / ${total} GB` : `${formatNumber(used)} / ${total} GB`;
}

export function formatNumber(value: number, maximumFractionDigits = 1) {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits }).format(
    value,
  );
}

export function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(value));
}

export function titleCase(value: string) {
  return value
    .split("-")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
