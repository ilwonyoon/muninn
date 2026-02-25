import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const DEPTH_LABELS: Record<number, string> = {
  0: "summary",
  1: "context",
  2: "detailed",
  3: "full",
};

export function depthLabel(depth: number): string {
  return DEPTH_LABELS[depth] ?? String(depth);
}

export function relativeTime(isoTimestamp: string): string {
  const dt = new Date(isoTimestamp);
  const now = new Date();
  const days = Math.floor((now.getTime() - dt.getTime()) / (1000 * 60 * 60 * 24));

  if (days < 0) return "just now";
  if (days === 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 7) return `${days}d ago`;
  if (days < 14) return "1w ago";
  if (days < 30) return `${Math.floor(days / 7)}w ago`;
  if (days < 60) return "1mo ago";
  if (days < 365) return `${Math.floor(days / 30)}mo ago`;
  return `${Math.floor(days / 365)}y ago`;
}

export function truncate(str: string, maxLen: number): string {
  if (str.length <= maxLen) return str;
  return str.slice(0, maxLen - 1) + "…";
}
