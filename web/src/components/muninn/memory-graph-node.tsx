"use client";

import { memo } from "react";
import { Handle, Position } from "@xyflow/react";
import type { NodeProps } from "@xyflow/react";
import type { Memory } from "@/lib/types";
import { truncate, cn } from "@/lib/utils";
import { DepthBadge } from "@/components/muninn/depth-badge";
import { TagPill } from "@/components/muninn/tag-pill";

// Border color per depth using CSS variables
const DEPTH_BORDER: Record<number, string> = {
  0: "border-depth-0",
  1: "border-depth-1",
  2: "border-depth-2",
  3: "border-depth-3",
};

// Node data type — just Memory
type MemoryNodeData = Memory;

function MemoryGraphNodeInner({ data }: NodeProps) {
  const mem = data as unknown as MemoryNodeData;
  return (
    <div
      className={cn(
        "w-[280px] cursor-pointer rounded-lg border-2 bg-card p-3 shadow-md transition-shadow hover:shadow-lg",
        DEPTH_BORDER[mem.depth] ?? "border-border"
      )}
    >
      <Handle type="target" position={Position.Top} className="!bg-border-hover !w-2 !h-2" />
      <div className="flex items-center justify-between">
        <DepthBadge depth={mem.depth} />
        <span className="font-mono text-[10px] text-muted">{mem.short_id}</span>
      </div>
      <div className="mt-1.5 text-sm leading-snug text-foreground line-clamp-3">
        {truncate(mem.content, 100)}
      </div>
      {mem.tags.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1">
          {mem.tags.slice(0, 3).map((tag) => (
            <TagPill key={tag} tag={tag} />
          ))}
          {mem.tags.length > 3 && (
            <span className="text-[10px] text-muted">+{mem.tags.length - 3}</span>
          )}
        </div>
      )}
      <Handle type="source" position={Position.Bottom} className="!bg-border-hover !w-2 !h-2" />
    </div>
  );
}

export const MemoryGraphNode = memo(MemoryGraphNodeInner);
