"use client";

import { memo } from "react";
import { Handle, Position } from "@xyflow/react";
import type { NodeProps } from "@xyflow/react";
import type { Memory } from "@/lib/types";
import { cn, extractTitle, extractBody } from "@/lib/utils";
import { DepthBadge } from "@/components/muninn/depth-badge";
import { CATEGORY_COLORS, CATEGORY_LABELS } from "@/lib/constants";

// Neutral border for all memory nodes — category group provides the color signal
const NEUTRAL_BORDER = "border-[var(--border-default)]";

const GENERIC_TAGS = new Set(["status", "context", "code", "reference", "update", "manual"]);

function primaryTag(tags: string[]): string | null {
  if (tags.length === 0) return null;
  return tags.find((t) => !GENERIC_TAGS.has(t)) ?? tags[0];
}

type MemoryNodeData = Memory;

function MemoryGraphNodeInner({ data }: NodeProps) {
  const mem = data as unknown as MemoryNodeData;
  const tag = primaryTag(mem.tags);

  return (
    <div
      className={cn(
        "w-[280px] cursor-pointer rounded-lg border bg-card p-3 shadow-sm transition-shadow hover:shadow-md",
        NEUTRAL_BORDER
      )}
    >
      <Handle type="target" position={Position.Top} className="!bg-border-hover !w-2 !h-2" />
      <div className="flex items-center justify-between">
        <DepthBadge depth={mem.depth} />
        {tag && (
          <span className="rounded bg-card-hover px-1.5 py-0.5 font-mono text-[10px] text-muted">
            {tag}
          </span>
        )}
      </div>
      <div className="mt-1.5 text-xs font-medium leading-snug text-foreground line-clamp-1">
        {extractTitle(mem.content)}
      </div>
      <div className="mt-0.5 text-xs leading-snug text-muted line-clamp-2">
        {extractBody(mem.content)}
      </div>
      <div className="mt-1.5 text-right">
        <span className="font-mono text-[10px] text-muted">{mem.short_id}</span>
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-border-hover !w-2 !h-2" />
    </div>
  );
}

export const MemoryGraphNode = memo(MemoryGraphNodeInner);

interface CategoryGroupData {
  label: string;
  category: string;
  isGroup: boolean;
  count: number;
  collapsed?: boolean;
}

function CategoryGroupNodeInner({ data }: NodeProps) {
  const group = data as unknown as CategoryGroupData;
  const color = CATEGORY_COLORS[group.category] ?? "#666666";
  const label = CATEGORY_LABELS[group.category] ?? group.label;

  return (
    <div
      className="flex w-[200px] cursor-pointer flex-col items-center justify-center rounded-lg border px-4 py-2.5"
      style={{
        borderColor: `${color}40`,
        backgroundColor: `${color}18`,
      }}
    >
      <Handle type="target" position={Position.Top} className="!bg-border-hover !w-2 !h-2" />
      <span className="text-sm font-medium" style={{ color }}>
        {label}
      </span>
      <span className="text-[10px] text-muted">
        {group.count} memories {group.collapsed ? "▸" : "▾"}
      </span>
      <Handle type="source" position={Position.Bottom} className="!bg-border-hover !w-2 !h-2" />
    </div>
  );
}

export const CategoryGroupNode = memo(CategoryGroupNodeInner);
