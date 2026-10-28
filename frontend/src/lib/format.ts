import type { Money } from "./types";

export const TIME_ZONE = "Asia/Dhaka";

export function toNumber(value: Money | null | undefined): number {
  if (value === null || value === undefined || value === "") return 0;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : 0;
}

/** ৳1,250 or ৳1,250.50 — BDT with South Asian digit grouping. */
export function formatBDT(value: Money | null | undefined): string {
  const n = toNumber(value);
  const hasFraction = Math.round(n * 100) % 100 !== 0;
  return `৳${n.toLocaleString("en-IN", {
    minimumFractionDigits: hasFraction ? 2 : 0,
    maximumFractionDigits: 2,
  })}`;
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: TIME_ZONE,
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  }).format(new Date(value));
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  // Plain dates (YYYY-MM-DD) are already business-local; parse them without shifting time zones.
  const date = /^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(`${value}T00:00:00+06:00`) : new Date(value);
  return new Intl.DateTimeFormat("en-GB", { timeZone: TIME_ZONE, day: "2-digit", month: "short", year: "numeric" }).format(date);
}

export function formatTime(value: string | null | undefined): string {
  if (!value) return "";
  return new Intl.DateTimeFormat("en-GB", { timeZone: TIME_ZONE, hour: "2-digit", minute: "2-digit", hour12: true }).format(
    new Date(value),
  );
}

/** Today's date in Asia/Dhaka as YYYY-MM-DD. */
export function dhakaToday(offsetDays = 0): string {
  const d = new Date(Date.now() + offsetDays * 86_400_000);
  return new Intl.DateTimeFormat("en-CA", { timeZone: TIME_ZONE }).format(d);
}

export function formatPhone(e164: string): string {
  if (e164.startsWith("+880") && e164.length === 14) return `+880 ${e164.slice(4, 8)}-${e164.slice(8)}`;
  return e164;
}
