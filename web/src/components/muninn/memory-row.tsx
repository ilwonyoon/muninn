"use client";

import { Pencil, Trash2 } from "lucide-react";
import type { Memory } from "@/lib/types";
import { relativeTime, truncate, cn } from "@/lib/utils";
import { DepthBadge } from "@/components/muninn/depth-badge";
import { TagPill } from "@/components/muninn/tag-pill";

interface MemoryRowProps {
  memory: Memory;
  selected: boolean;
  active: boolean;
  onSelect: () => void;
  onEdit: () => void;
  onDelete: () => void;
}

export function MemoryRow({
  memory,
  selected,
  active,
  onSelect,
  onEdit,
  onDelete,
}: MemoryRowProps) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect();
        }
      }}
      className={cn(
        "group flex cursor-pointer items-start gap-3 px-4 py-2.5 transition-colors",
        selected && !active && "bg-card-hover",
        active && "border-l-2 border-accent bg-card-hover/50"
      )}
    >
      <DepthBadge depth={memory.depth} />
      <div className="min-w-0 flex-1">
        <div className="text-sm leading-snug text-foreground">
          {truncate(memory.content, 200)}
        </div>
        {memory.tags.length > 0 && (
          <div className="mt-1 flex gap-1">
            {memory.tags.map((tag) => (
              <TagPill key={tag} tag={tag} />
            ))}
          </div>
        )}
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <div className="flex flex-col items-end gap-0.5">
          <span className="font-mono text-[10px] text-muted">
            {memory.short_id}
          </span>
          <span className="text-[10px] text-muted">
            {relativeTime(memory.updated_at)}
          </span>
        </div>
        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onEdit();
            }}
            className="rounded p-1 text-muted hover:bg-card-hover hover:text-foreground"
            title="Edit"
          >
            <Pencil className="h-3 w-3" />
          </button>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="rounded p-1 text-muted hover:bg-card-hover hover:text-red-400"
            title="Delete"
          >
            <Trash2 className="h-3 w-3" />
          </button>
        </div>
      </div>
    </div>
  );
}
