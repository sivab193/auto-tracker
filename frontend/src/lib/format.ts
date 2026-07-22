import type { DocumentType } from "../api/types";

export function money(n: number | null | undefined, currency = "USD"): string {
  if (n === null || n === undefined) return "—";
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency,
      maximumFractionDigits: 2,
    }).format(n);
  } catch {
    return `${n.toFixed(2)} ${currency}`;
  }
}

export function titleize(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function docTypeLabel(t: DocumentType): string {
  return titleize(t);
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

export function daysUntil(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  const ms = d.getTime() - Date.now();
  return Math.ceil(ms / 86400000);
}

/** Badge tone for an expiry date: red (past), amber (<30d), green otherwise. */
export function expiryTone(iso: string | null | undefined): "red" | "amber" | "green" | "" {
  const d = daysUntil(iso);
  if (d === null) return "";
  if (d < 0) return "red";
  if (d <= 30) return "amber";
  return "green";
}

export function today(): string {
  return new Date().toISOString().slice(0, 10);
}
