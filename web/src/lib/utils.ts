import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const DEPTH_LABELS: Record<number, string> = {
  0: "L0",
  1: "L1",
  2: "L2",
  3: "L3",
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

/** Extract body preview — content after the title line, or remainder of a long first line. */
export function extractBody(content: string, maxLen = 120): string {
  const lines = content.split("\n").map((l) => l.trim());
  const firstIdx = lines.findIndex((l) => l.length > 0);
  if (firstIdx < 0) return "";
  const rest = lines
    .slice(firstIdx + 1)
    .filter((l) => l.length > 0)
    .join(" ")
    .trim();
  if (rest) return truncate(stripMarkdown(rest), maxLen);
  // Single-line content: show the part after the title truncation point
  const fullFirst = stripMarkdown(lines[firstIdx]);
  if (fullFirst.length > 60) return truncate(fullFirst.slice(60).trim(), maxLen);
  return "";
}
