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

export function formatBytes(value: number | null) {
  if (value === null) return "--";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let amount = value;
  let unit = 0;
  while (amount >= 1024 && unit < units.length - 1) {
    amount /= 1024;
    unit += 1;
  }
  return `${formatNumber(amount, amount >= 10 ? 1 : 2)} ${units[unit]}`;
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
