"use client";

import { memo } from "react";
import { Handle, Position } from "@xyflow/react";
import type { NodeProps } from "@xyflow/react";
import type { Memory } from "@/lib/types";
import { depthLabel, extractTitle, extractBody } from "@/lib/utils";
import { CATEGORY_COLORS, CATEGORY_LABELS } from "@/lib/constants";

/* -------------------------------------------------------------------------- */
/*  Constants                                                                  */
/* -------------------------------------------------------------------------- */

const DEPTH_DOT_COLORS: Record<number, string> = {
  0: "#ef4444",
  1: "#f59e0b",
  2: "#3b82f6",
  3: "#6b7280",
};

const GENERIC_TAGS = new Set([
  "status",
  "context",
  "code",
  "reference",
  "update",
  "manual",
]);

function primaryTag(tags: string[]): string | null {
  if (tags.length === 0) return null;
  return tags.find((t) => !GENERIC_TAGS.has(t)) ?? tags[0];
}

/* -------------------------------------------------------------------------- */
/*  MemoryGraphNode — renders a single memory in the tree                      */
/* -------------------------------------------------------------------------- */

interface MemoryNodeData {
  memory: Memory;
  isGroup: false;
  [key: string]: unknown;
}

function MemoryGraphNodeInner({ data }: NodeProps) {
  const { memory } = data as unknown as MemoryNodeData;
  const dotColor = DEPTH_DOT_COLORS[memory.depth] ?? "#6b7280";
  const catColor = CATEGORY_COLORS[memory.category] ?? "#888";
  const tag = primaryTag(memory.tags);

  return (
    <div
      className={`rounded-lg border bg-[var(--card)] px-3 py-2 shadow-sm ${memory.resolved ? "opacity-60" : ""}`}
      style={{
        width: 280,
        borderColor: catColor,
        borderWidth: 1.5,
      }}
    >
      <Handle type="target" position={Position.Top} className="!bg-muted" />

      {/* Header: depth badge + primary tag */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ backgroundColor: dotColor }}
          />
          <span className="font-mono text-[10px] text-[var(--muted)]">
            {depthLabel(memory.depth)}
          </span>
        </div>
        {tag && (
          <span className="rounded bg-[var(--card-hover)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--muted)]">
            {tag}
          </span>
        )}
      </div>

      {/* Title (first line, bold) */}
      <div className={`mt-1.5 text-xs font-medium leading-snug text-[var(--foreground)] line-clamp-1 ${memory.resolved ? "line-through" : ""}`}>
        {memory.title || extractTitle(memory.content)}
      </div>

      {/* Body preview (muted, 2 lines) */}
      <div className="mt-0.5 text-xs leading-snug text-[var(--muted)] line-clamp-2">
        {extractBody(memory.content)}
      </div>

      {/* Short ID */}
      <div className="mt-1.5 text-right">
        <span className="font-mono text-[10px] text-[var(--muted)]">
          {memory.short_id}
        </span>
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-muted" />
    </div>
  );
}

export const MemoryGraphNode = memo(MemoryGraphNodeInner);

/* -------------------------------------------------------------------------- */
/*  CategoryGroupNode — virtual node for category clusters                     */
/* -------------------------------------------------------------------------- */

interface CategoryGroupData {
  id: string;
  label: string;
  category: string;
  isGroup: true;
  count: number;
  color: string;
  collapsed?: boolean;
  [key: string]: unknown;
}

function CategoryGroupNodeInner({ data }: NodeProps) {
  const { label, category, count, color, collapsed } =
    data as unknown as CategoryGroupData;
  const displayLabel = CATEGORY_LABELS[category] ?? label;

  return (
    <div
      className="flex cursor-pointer items-center justify-center rounded-lg border-2 transition-all duration-200"
      style={{
        width: 200,
        height: collapsed ? 44 : 60,
        borderColor: `${color}40`,
        backgroundColor: collapsed ? `${color}05` : `${color}15`,
        opacity: collapsed ? 0.6 : 1,
      }}
    >
      <Handle type="target" position={Position.Top} className="!bg-muted" />

      <div className="text-center">
        <div
          className="flex items-center justify-center gap-1.5 text-sm font-medium"
          style={{ color }}
        >
          <span className="text-[10px]">{collapsed ? "▸" : "▾"}</span>
          {displayLabel}
        </div>
        {!collapsed && (
          <div className="text-[10px] text-[var(--muted)]">
            {count} {count === 1 ? "memory" : "memories"}
          </div>
        )}
        {collapsed && (
          <div className="text-[9px] text-[var(--muted)]">
            {count} hidden
          </div>
        )}
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-muted" />
    </div>
  );
}

export const CategoryGroupNode = memo(CategoryGroupNodeInner);
