import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
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

/** Strip common markdown syntax for plain-text display. */
export function stripMarkdown(text: string): string {
  return text
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/\*(.+?)\*/g, "$1")
    .replace(/`(.+?)`/g, "$1")
    .replace(/\[(.+?)\]\(.+?\)/g, "$1")
    .replace(/^[-*+]\s+/gm, "")
    .replace(/^\d+\.\s+/gm, "")
    .trim();
}

/** Extract title from memory content — first non-empty line, markdown stripped. */
export function extractTitle(content: string, maxLen = 60): string {
  const lines = content.split("\n").map((l) => l.trim());
  const firstLine = lines.find((l) => l.length > 0) ?? "";
  return truncate(stripMarkdown(firstLine), maxLen);
}

/** Classify a date string into a human-readable group label. */
export function getDateGroup(dateString: string): string {
  const dt = new Date(dateString);
  const now = new Date();

  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfYesterday = new Date(startOfToday.getTime() - 86_400_000);
  const startOfWeek = new Date(startOfToday.getTime() - startOfToday.getDay() * 86_400_000);
  const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);

  if (dt >= startOfToday) return "Today";
  if (dt >= startOfYesterday) return "Yesterday";
  if (dt >= startOfWeek) return "This week";
  if (dt >= startOfMonth) return "This month";
  return "Older";
}

/** Extract body preview — full content flattened, markdown stripped. */
export function extractBody(content: string, maxLen = 140): string {
  const flat = content
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l.length > 0)
    .join(" ");
  return truncate(stripMarkdown(flat), maxLen);
}
